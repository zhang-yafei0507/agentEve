"""
聊天路由 - 处理用户对话请求
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
from datetime import datetime

from ..utils.db_init import get_db
from ..utils.database import Session as DBSession, Message
from ..agents.supervisor import SupervisorAgent
from ..core.orchestrator import AgentOrchestrator
from ..llm.providers.base import create_llm_provider
from ..utils.config import get_settings
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
        
        # 使用 SupervisorAgent 进行意图分析和任务拆解
        supervisor = SupervisorAgent()
        
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
            
            # 意图分析
            intent = await supervisor.analyze_intent(query, llm_client=llm_provider)
            
            # 简单任务处理
            if not intent.get("requires_multi_agent", False):
                # 主智能体开始思考
                thought_event = json.dumps({
                    'type': 'supervisor_thought',
                    'action': 'analyzing_query',
                    'message': '正在理解用户查询...'
                })
                yield f"event: supervisor_thought\ndata: {thought_event}\n\n"
                await asyncio.sleep(0.3)
                
                # 主智能体决策
                decision_event = json.dumps({
                    'type': 'supervisor_decision',
                    'decision': 'simple_task',
                    'message': '这是一个简单任务，直接回答...'
                })
                yield f"event: supervisor_decision\ndata: {decision_event}\n\n"
                await asyncio.sleep(0.3)
                
                yield f"event: agent_update\ndata: {json.dumps({'type': 'agent_update', 'agent': 'supervisor', 'status': 'thinking', 'message': '正在思考...'})}\n\n"
                await asyncio.sleep(0.5)
                
                # 使用 LLM 流式生成答案
                messages = [
                    {"role": "system", "content": "你是一个智能助手。请用中文详细、专业地回答用户的问题。"},
                    {"role": "user", "content": query}
                ]
                
                stream_response = llm_provider.chat_completion_stream(messages)
                content = ""
                
                async for chunk in stream_response:
                    chunk_content = chunk.get("content", "")
                    if chunk_content:
                        content += chunk_content
                        chunk_data = json.dumps({
                            'type': 'final_answer_chunk',
                            'chunk': chunk_content
                        })
                        yield f"event: final_answer_chunk\ndata: {chunk_data}\n\n"
                        await asyncio.sleep(0.02)
                
                # 更新 AI 消息
                ai_message.content = content
                ai_message.thinking_process = [{
                    "agent": "Supervisor",
                    "action": "直接回答",
                    "timestamp": datetime.utcnow().isoformat()
                }]
            
            else:
                # 复杂任务：使用 Orchestrator 进行流式编排
                print(f"[Chat] 开始多智能体编排，意图：{intent}")
                
                # 任务拆解
                sub_tasks = await supervisor.decompose_task(query, intent, llm_client=llm_provider)
                sub_agents = await supervisor.create_sub_agents(sub_tasks)
                
                # 转换为字典格式供 Orchestrator 使用
                sub_agents_dict = [
                    {
                        "id": agent.id,
                        "role": agent.role,
                        "task": agent.task,
                        "tools": agent.available_tools,
                        "output": None,  # 将由 Orchestrator 填充
                        "duration": 0
                    }
                    for agent in sub_agents
                ]
                
                # 使用 Orchestrator 执行流式流程
                orchestrator = AgentOrchestrator(llm_provider)
                
                thinking_process = []
                sub_agent_results = []
                tool_call_count = 0
                final_content = ""
                
                async for event in orchestrator.execute_flow(query, sub_agents_dict):
                    event_type = event['type']
                    event_data = event['data']
                    
                    # 直接推送事件到前端
                    yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
                    
                    # 累积结构化数据
                    if event_type == 'agent_update' and event_data.get('status') == 'completed':
                        thinking_process.append({
                            "agent": event_data.get('agent'),
                            "action": event_data.get('task'),
                            "tool_calls": event_data.get('tool_calls', 0),
                            "duration": event_data.get('duration', 1.0),
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                        sub_agent_results.append({
                            "agent_id": event_data.get('agent_id'),
                            "role": event_data.get('agent'),
                            "task": event_data.get('task'),
                            "output": event_data.get('output'),
                            "tool_calls": event_data.get('tool_calls', 0),
                            "duration": event_data.get('duration', 1.0)
                        })
                        
                        if event_data.get('tool_calls', 0) > 0:
                            tool_call_count += event_data.get('tool_calls', 0)
                    
                    elif event_type == 'final_answer_chunk':
                        final_content += event_data.get('chunk', '')
                    
                    elif event_type == 'done':
                        # 更新最终统计数据
                        event_data['thinking_process'] = thinking_process
                        event_data['sub_agent_results'] = sub_agent_results
                
                # 更新 AI 消息
                ai_message.content = final_content or ''.join([r['output'] for r in sub_agent_results if r.get('output')])
                ai_message.thinking_process = thinking_process
                ai_message.sub_agent_results = sub_agent_results
                ai_message.msg_metadata = {
                    "total_duration": sum(r["duration"] for r in sub_agent_results),
                    "total_tool_calls": tool_call_count,
                    "agents_used": list(set(r["role"] for r in sub_agent_results)),
                    "sub_agent_count": len(sub_agent_results)
                }
                
                # 关键修复：使用 LLM 流式生成最终答案
                if not final_content and len(sub_agent_results) > 0:
                    print(f"[Chat] 使用 LLM 实时生成最终答案...")
                    
                    # 构建上下文信息
                    context_info = "各智能体执行结果：\n\n"
                    for i, sa in enumerate(sub_agent_results):
                        context_info += f"步骤{i+1} - {sa['role']}: {sa['task']}\n"
                        context_info += f"输出：{sa['output']}\n\n"
                    
                    # 调用 LLM 生成综合性答案（流式）
                    system_prompt = """你是一个专业的总结助手。请根据提供的多智能体协作结果，生成一份结构清晰、内容完整的综合性报告。

要求：
1. 先概述任务整体执行情况
2. 详细说明每个智能体的贡献
3. 提炼关键发现和结论
4. 使用 Markdown 格式，确保层次分明
5. 语言专业、流畅、易懂"""
                    
                    user_message = f"""用户原始查询：{query}

{context_info}

请基于以上信息生成综合性报告。"""
                    
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ]
                    
                    # 使用 LLM Provider 的流式接口
                    stream_response = llm_provider.chat_completion_stream(messages)
                    
                    final_content = ""
                    async for chunk in stream_response:
                        chunk_content = chunk.get("content", "")
                        if chunk_content:
                            final_content += chunk_content
                            chunk_data = json.dumps({
                                'type': 'final_answer_chunk',
                                'chunk': chunk_content
                            })
                            yield f"event: final_answer_chunk\ndata: {chunk_data}\n\n"
                            await asyncio.sleep(0.02)
                    
                    # 更新 AI 消息内容
                    ai_message.content = final_content or ''.join([r['output'] for r in sub_agent_results if r.get('output')])
                    ai_message.thinking_process = thinking_process
                    ai_message.sub_agent_results = sub_agent_results
                    ai_message.msg_metadata = {
                        "total_duration": sum(r["duration"] for r in sub_agent_results),
                        "total_tool_calls": tool_call_count,
                        "agents_used": list(set(r["role"] for r in sub_agent_results)),
                        "sub_agent_count": len(sub_agent_results)
                    }
                    
                    # 等待 AI 消息写入完成
                    await asyncio.sleep(0.1)
            
            # 最终提交
            await db.commit()
            print(f"[Chat] ✅ 消息处理完成，ID: {ai_message.id}")
            
        except Exception as e:
            print(f"[Chat] ❌ SSE 生成器错误：{e}")
            import traceback
            traceback.print_exc()
        finally:
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
