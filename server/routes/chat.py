"""
聊天路由 - 处理用户对话请求
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import sys  # 新增：用于获取 Python 解释器路径
from datetime import datetime

from ..utils.db_init import get_db
from ..utils.database import Session as DBSession, Message
from ..agents.universal import UniversalAgent
from ..mcp.tool_manager import MCPToolManager
from ..llm.providers.base import create_llm_provider
from ..utils.config import get_settings
from ..mcp.servers_config import get_enabled_servers
import asyncio

router = APIRouter()


@router.post("/send")
async def send_message(
    request: Request,
    query: str = None,
    session_id: str = None,
    selected_tools: list = None,
    db: AsyncSession = Depends(get_db)
):
    """
    发送消息并获取流式响应
    使用 SSE (Server-Sent Events) 实时推送智能体状态
    """
    
    # 尝试从 query string 或 JSON body 获取参数
    if not query:
        # 尝试从 JSON body 获取
        try:
            body = await request.json()
            query = body.get('query')
            session_id = body.get('session_id', session_id)
            selected_tools = body.get('selected_tools', selected_tools)
        except:
            pass
    
    if not query:
        raise HTTPException(status_code=400, detail="缺少 query 参数")
    
    # 1. 获取或创建会话
    if not session_id:
        db_session = DBSession(title=query[:50] + "..." if len(query) > 50 else query)
        db.add(db_session)
        await db.commit()
        await db.refresh(db_session)
        session_id = db_session.id
    else:
        result = await db.execute(select(DBSession).where(DBSession.id == session_id))
        db_session = result.scalar_one_or_none()
        if not db_session:
            raise HTTPException(status_code=404, detail="会话不存在")
    
    # 2. 保存用户消息
    user_message = Message(
        session_id=session_id,
        role="user",
        content=query,
        metadata={"selected_tools": selected_tools or []}
    )
    db.add(user_message)
    await db.commit()
    
    # 3. 创建 AI 消息占位符
    ai_message = Message(
        session_id=session_id,
        role="assistant",
        content="",
        thinking_process=[],
        sub_agent_results=[],
        citations=[]
    )
    db.add(ai_message)
    await db.commit()
    await db.refresh(ai_message)  # 关键：刷新以获取生成的 ID
    
    print(f"[Chat] AI 消息已创建，ID: {ai_message.id}")
    
    # 4. 定义 SSE 生成器
    async def event_generator():
        # 创建 LLM Provider
        settings = get_settings()
        llm_provider = create_llm_provider(
            provider_type=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL
        )
        
        # 创建工具管理器并注册 MCP 服务器（从配置文件加载）
        tool_manager = MCPToolManager()
        
        # 加载所有启用的 MCP 服务器
        enabled_servers = await get_enabled_servers()
        print(f"[Chat] 📋 发现 {len(enabled_servers)} 个启用的 MCP 服务器")
        
        for server_config in enabled_servers:
            try:
                server_name = server_config.get("name")
                print(f"[Chat] 🔌 正在注册 MCP 服务器：{server_name}...")
                
                # 替换 Python 命令为当前解释器路径
                if server_config.get("command") == "python":
                    server_config["command"] = sys.executable
                
                await tool_manager.register_server(
                    name=server_name,
                    config=server_config
                )
                print(f"[Chat] ✅ {server_name} MCP 服务器注册成功")
                
            except Exception as e:
                print(f"[Chat] ❌ {server_name} MCP 服务器注册失败：{e}")
                # 继续注册其他服务器，不因单个失败而中断
        
        # 使用 UniversalAgent 进行 ReAct 循环执行
        agent = UniversalAgent(llm_provider, tool_manager)
        
        try:
            # 发送会话信息（第一个事件，必须包含 message_id）
            session_info_data = json.dumps({
                'session_id': session_id, 
                'message_id': str(ai_message.id),
                'type': 'session_info'
            })
            print(f"[SSE] 发送 session_info: {session_info_data}")
            print(f"[SSE] ⚠️ 关键：ai_message.id = {ai_message.id}")
            yield f"event: session_info\ndata: {session_info_data}\n\n"
            
            # 使用 UniversalAgent 执行 ReAct 循环
            thinking_process = []  # 保留兼容性，但不再使用
            tool_calls = []
            reflections = []  # 新增：反思历史
            supervisor_thoughts = []  # 新增：主智能体思考
            final_content = ""
            
            async for event in agent.execute(query):
                event_type = event['type']
                event_data = event['data']
                
                # 直接推送事件到前端
                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
                
                # 累积结构化数据（新架构）
                if event_type == 'supervisor_thought':
                    supervisor_thoughts.append({
                        "step": event_data.get("step", 0),
                        "action": event_data.get("action", event_data.get("reasoning", "")),
                        "reasoning": event_data.get("reasoning", ""),
                        "tool": event_data.get("tool"),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif event_type == 'tool_call_start':
                    tool_calls.append({
                        "step": event_data.get("step", 0),
                        "tool": event_data.get("tool"),
                        "params": event_data.get("params"),
                        "status": "running",
                        "start_time": datetime.utcnow().isoformat()
                    })
                
                elif event_type == 'tool_call_end':
                    # 更新最后一个工具调用
                    if tool_calls:
                        tool_calls[-1]["status"] = event_data.get("status")
                        tool_calls[-1]["result"] = event_data.get("result")
                        tool_calls[-1]["end_time"] = datetime.utcnow().isoformat()
                
                elif event_type == 'reflection':
                    reflections.append({
                        "step": event_data.get("step", 0),
                        "quality_score": event_data.get("quality_score", 0),
                        "observation_summary": event_data.get("observation_summary", ""),
                        "adjustment": event_data.get("adjustment", ""),
                        "should_continue": event_data.get("should_continue", False),
                        "should_finish": event_data.get("should_finish", False),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif event_type == 'final_answer_chunk':
                    final_content += event_data.get('chunk', '')
                
                elif event_type == 'done':
                    # 更新最终统计数据
                    pass
            
            # 更新 AI 消息（新架构数据结构）
            ai_message.content = final_content
            ai_message.thinking_process = supervisor_thoughts  # 兼容旧字段名，实际存储 supervisor_thoughts
            ai_message.sub_agent_results = []  # 已废弃，不再使用
            ai_message.msg_metadata = {
                "total_steps": len(supervisor_thoughts),
                "total_tool_calls": len([t for t in tool_calls if t.get("status") == "success"]),
                "reflections_count": len(reflections),
                "execution_id": getattr(agent, 'id', None),
                "supervisor_thoughts": supervisor_thoughts,  # 新增：完整思考历史
                "reflections": reflections,  # 新增：完整反思历史
                "tool_calls": tool_calls  # 新增：完整工具调用历史
            }
            
            # 最终提交
            await db.commit()
            print(f"[Chat] ✅ 消息处理完成，ID: {ai_message.id}")
            
        except Exception as e:
            print(f"[Chat] ❌ SSE 生成器错误：{e}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理工具管理器资源
            try:
                await tool_manager.cleanup()
            except Exception as cleanup_error:
                print(f"[Chat] 清理资源时出错：{cleanup_error}")
            
            # 确保数据库连接关闭
            await db.close()


@router.get("/quick-questions")
async def get_quick_questions(category: str = None):
    """获取快捷提问列表"""
    questions = [
        {"text": "帮我分析一下特斯拉 2025 年 Q1 财报", "category": "analysis"},
        {"text": "最近 AI 领域有什么重要新闻？", "category": "research"},
        {"text": "用 Python 写一个快速排序算法", "category": "coding"},
        {"text": "对比比亚迪和蔚来汽车的商业模式", "category": "analysis"},
        {"text": "帮我写一篇关于气候变化的科普文章", "category": "writing"},
        {"text": "查询英伟达最新股价和市值", "category": "research"},
        {"text": "解释什么是 Transformer 架构", "category": "analysis"},
        {"text": "创建一个简单的待办事项管理网页", "category": "coding"},
        {"text": "总结《人类简史》这本书的核心观点", "category": "writing"}
    ]

    if category:
        questions = [q for q in questions if q["category"] == category]

    return {"questions": questions[:9]}  # 最多返回 9 个


@router.get("/history/{session_id}")
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """获取会话历史消息"""
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.timestamp)
    )
    messages = result.scalars().all()
    
    return {
        "session_id": session_id,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "thinking_process": msg.thinking_process if msg.role == "assistant" else None,
                "sub_agent_results": msg.sub_agent_results if msg.role == "assistant" else None,
                "citations": msg.citations if msg.role == "assistant" else None
            }
            for msg in messages
        ]
    }
