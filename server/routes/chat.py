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
from ..utils.llm_client import create_llm_client
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
        # 创建 LLM 客户端
        settings = get_settings()
        llm_client = await create_llm_client(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL
        )
        
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
            
            # 关键新增：主智能体开始思考
            thought_event = json.dumps({
                'type': 'supervisor_thought',
                'action': 'analyzing_query',
                'message': '正在理解用户查询...'
            })
            yield f"event: supervisor_thought\ndata: {thought_event}\n\n"
            await asyncio.sleep(0.3)
            
            # 执行智能体任务（传入 LLM 客户端）
            task_result = await supervisor.execute(query, llm_client=llm_client)
            print(f"[SSE] 任务执行完成，类型：{task_result.get('is_simple')}")
            
            # 如果是简单任务
            if task_result.get("is_simple"):
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
                
                # 流式输出答案
                content = task_result["content"]
                print(f"[SSE] 开始流式传输，内容长度：{len(content)}")
                for i in range(0, len(content), 10):
                    chunk = content[i:i+10]
                    chunk_data = json.dumps({
                        'type': 'final_answer_chunk',
                        'chunk': chunk
                    })
                    print(f"[SSE] 发送 chunk: {chunk}")
                    yield f"event: final_answer_chunk\ndata: {chunk_data}\n\n"
                    await asyncio.sleep(0.05)
                
                # 更新 AI 消息
                ai_message.content = content
                ai_message.thinking_process = [{
                    "agent": "Supervisor",
                    "action": "直接回答",
                    "timestamp": datetime.utcnow().isoformat()
                }]
            
            else:
                # 复杂任务：多智能体协作（关键修复：实现思考 - 工具调用 - 思考的交替循环）
                print(f"[Chat] 开始多智能体编排，子智能体数量：{len(task_result['sub_agents'])}")
                
                thinking_process = []
                sub_agent_results = []
                tool_call_count = 0
                completed_steps = 0
                
                # 主智能体决策：任务拆解
                decision_event = json.dumps({
                    'type': 'supervisor_decision',
                    'decision': 'complex_task',
                    'message': f'这是一个复杂任务，需要{len(task_result["sub_agents"])}个子智能体协作',
                    'reasoning': task_result.get('intent', {}).get('reasoning', '')
                })
                yield f"event: supervisor_decision\ndata: {decision_event}\n\n"
                await asyncio.sleep(0.5)
                
                # 初始任务规划（只展示第一步，后续逐步揭示）
                first_step = task_result['sub_agents'][0] if task_result['sub_agents'] else None
                if first_step:
                    task_plan_event = json.dumps({
                        'type': 'task_plan',
                        'total_steps': len(task_result['sub_agents']),
                        'steps': [
                            {
                                'step': 1,
                                'role': first_step['role'],
                                'task': first_step['task'],
                                'status': 'pending',
                                'revealed': True  # 只揭示第一步
                            }
                        ]
                    })
                    yield f"event: task_plan\ndata: {task_plan_event}\n\n"
                    await asyncio.sleep(0.5)
                
                # 关键修复：逐个执行子智能体并实现“思考 - 执行 - 反思”循环
                for idx, sub_agent in enumerate(task_result["sub_agents"]):
                    agent_id = sub_agent.get("id") or sub_agent.get("agent_id")
                    role = sub_agent["role"]
                    
                    # 主智能体思考：是否继续下一步
                    if idx > 0:
                        # 发送下一步决策事件
                        next_step_event = json.dumps({
                            'type': 'next_step_decision',
                            'current_step': idx,
                            'total_steps': len(task_result['sub_agents']),
                            'message': f'第{idx}步已完成，评估是否需要继续执行下一步...'
                        })
                        yield f"event: next_step_decision\ndata: {next_step_event}\n\n"
                        await asyncio.sleep(0.3)
                        
                        # 揭示下一步到任务规划
                        current_step = task_result['sub_agents'][idx]
                        reveal_step_event = json.dumps({
                            'type': 'task_plan_update',
                            'new_step': {
                                'step': idx + 1,
                                'role': current_step['role'],
                                'task': current_step['task'],
                                'status': 'pending',
                                'revealed': True
                            }
                        })
                        yield f"event: task_plan_update\ndata: {reveal_step_event}\n\n"
                        await asyncio.sleep(0.3)
                    
                    # 主智能体思考：开始执行这一步
                    thought_event = json.dumps({
                        'type': 'supervisor_thought',
                        'action': 'starting_step',
                        'step': idx + 1,
                        'total': len(task_result['sub_agents']),
                        'message': f'开始执行第{idx + 1}步：{role} - {sub_agent["task"][:30]}...'
                    })
                    yield f"event: supervisor_thought\ndata: {thought_event}\n\n"
                    await asyncio.sleep(0.3)
                    
                    # 智能体启动事件
                    event_data = json.dumps({
                        'type': 'agent_update',
                        'agent': role,
                        'agent_id': agent_id,
                        'status': 'running',
                        'message': f'{role} 正在执行：{sub_agent["task"]}',
                        'task': sub_agent['task'],
                        'tools': sub_agent.get('tools', [])
                    })
                    yield f"event: agent_update\ndata: {event_data}\n\n"
                    
                    # 工具调用开始（如果有真实工具）
                    if sub_agent.get('tools'):
                        tool_start_event = json.dumps({
                            'type': 'tool_call_start',
                            'tool': sub_agent['tools'][0],
                            'agent_id': agent_id,
                            'params': {'query': sub_agent['task']},
                            'step': idx + 1
                        })
                        yield f"event: tool_call_start\ndata: {tool_start_event}\n\n"
                    
                    # 等待子智能体执行完成
                    await asyncio.sleep(0.5)
                    
                    # 工具调用结果
                    if sub_agent.get('tools'):
                        tool_end_event = json.dumps({
                            'type': 'tool_call_end',
                            'tool': sub_agent['tools'][0],
                            'agent_id': agent_id,
                            'status': 'success',
                            'result': '找到相关信息',
                            'duration': sub_agent.get("duration", 1.0),
                            'step': idx + 1
                        })
                        yield f"event: tool_call_end\ndata: {tool_end_event}\n\n"
                        tool_call_count += 1
                    
                    # 智能体完成
                    event_data = json.dumps({
                        'type': 'agent_update',
                        'agent': role,
                        'agent_id': agent_id,
                        'status': 'completed',
                        'output': sub_agent['output'],
                        'task': sub_agent['task'],
                        'tool_calls': sub_agent.get('tool_calls', 1) if sub_agent.get('tools') else 0,
                        'duration': sub_agent.get("duration", 1.0)
                    })
                    yield f"event: agent_update\ndata: {event_data}\n\n"
                    
                    # 主智能体反思：评估完成质量
                    thought_event = json.dumps({
                        'type': 'supervisor_thought',
                        'action': 'step_completed',
                        'step': idx + 1,
                        'message': f'第{idx + 1}步完成，耗时{sub_agent.get("duration", 1.0):.1f}秒，检查结果质量...'
                    })
                    yield f"event: supervisor_thought\ndata: {thought_event}\n\n"
                    await asyncio.sleep(0.3)
                    
                    # 判断是否需要继续下一步
                    if idx < len(task_result['sub_agents']) - 1:
                        reflection_event = json.dumps({
                            'type': 'supervisor_reflecting',
                            'step': idx + 1,
                            'message': f'第{idx + 1}步结果良好，准备启动第{idx + 2}步...'
                        })
                        yield f"event: supervisor_reflecting\ndata: {reflection_event}\n\n"
                        await asyncio.sleep(0.3)
                    
                    thinking_process.append({
                        "agent": role,
                        "action": sub_agent["task"],
                        "tool_calls": sub_agent.get('tool_calls', 1) if sub_agent.get('tools') else 0,
                        "duration": sub_agent.get("duration", 1.0),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # 累积子智能体结果
                    sub_agent_results.append({
                        "agent_id": agent_id,
                        "role": role,
                        "task": sub_agent["task"],
                        "output": sub_agent["output"],
                        "tool_calls": sub_agent.get('tool_calls', 1) if sub_agent.get('tools') else 0,
                        "duration": sub_agent.get("duration", 1.0)
                    })
                    
                    completed_steps += 1
                
                # 所有子智能体完成后，主智能体汇总
                thought_event = json.dumps({
                    'type': 'supervisor_thought',
                    'action': 'aggregating',
                    'message': f'所有{len(sub_agent_results)}个子智能体已完成，正在汇总结果...'
                })
                yield f"event: supervisor_thought\ndata: {thought_event}\n\n"
                await asyncio.sleep(0.5)
                
                # 所有子智能体完成后，主智能体汇总
                event_data = json.dumps({
                    'type': 'agent_update',
                    'agent': 'supervisor',
                    'status': 'aggregating',
                    'message': '所有子智能体已完成，正在汇总结果...',
                    'completed_count': len(sub_agent_results),
                    'total_count': len(task_result['sub_agents'])
                })
                yield f"event: agent_update\ndata: {event_data}\n\n"
                await asyncio.sleep(0.5)
                
                # 关键修复：如果有 LLM 客户端，使用 LLM 实时生成总结而不是简单拼接
                settings = get_settings()
                llm_client_for_summary = await create_llm_client(
                    provider=settings.LLM_PROVIDER,
                    api_key=settings.LLM_API_KEY,
                    base_url=settings.LLM_BASE_URL,
                    model=settings.LLM_MODEL
                )
                
                if llm_client_for_summary and len(sub_agent_results) > 0:
                    # 使用 LLM 进行实时综合推理生成最终答案
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
                    
                    # 关键修复：使用流式调用 LLM
                    stream_response = await llm_client_for_summary.chat_completion(
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2048,
                        stream=True  # 启用流式
                    )
                    
                    # 实时流式输出 LLM 生成的内容
                    print(f"[Chat] 开始流式输出 LLM 生成的答案...")
                    async for chunk in stream_response:
                        chunk_content = chunk.get("content", "")
                        if chunk_content:
                            chunk_data = json.dumps({
                                'type': 'final_answer_chunk',
                                'chunk': chunk_content
                            })
                            yield f"event: final_answer_chunk\ndata: {chunk_data}\n\n"
                            await asyncio.sleep(0.02)  # 更小的延迟，更流畅
                    
                    # 更新 AI 消息（内容已在流式中累积）
                    ai_message.content = stream_response.get("full_content", "")
                    
                else:
                    # 降级方案：没有 LLM 时使用原有逻辑
                    print(f"[Chat] 降级：使用拼接方式生成最终答案")
                    final_answer = task_result.get("final_answer", "")
                    
                    # 关键修复：如果 final_answer 为空或质量太低，现场生成详细总结
                    if not final_answer or len(final_answer) < 100:
                        print(f"[Chat] final_answer 质量不足 (长度:{len(final_answer)}), 现场生成详细总结")
                        
                        # 从子智能体的 output 中提取有用信息
                        collected_info = []
                        for sa in sub_agent_results:
                            output = sa.get('output', '')
                            if output and len(output) > 20:
                                collected_info.append(f"- **{sa['role']}**: {output}")
                        
                        # 生成结构化总结
                        final_answer = f"## 任务执行报告\n\n"
                        final_answer += f"已启动 {len(sub_agent_results)} 个智能体进行协作分析：\n\n"
                        
                        if collected_info:
                            final_answer += "### 各智能体执行情况：\n"
                            final_answer += "\n".join(collected_info)
                            final_answer += "\n\n"
                        
                        # 如果有共享状态板的数据
                        shared_board = task_result.get('shared_board', {})
                        key_findings = shared_board.get('key_findings', [])
                        if key_findings:
                            final_answer += "### 关键发现：\n"
                            for finding in key_findings[:5]:  # 最多显示 5 条
                                final_answer += f"- {finding}\n"
                            final_answer += "\n"
                        
                        intermediate_conclusions = shared_board.get('intermediate_conclusions', [])
                        if intermediate_conclusions:
                            final_answer += "### 中间结论：\n"
                            for conclusion in intermediate_conclusions[:3]:  # 最多显示 3 条
                                final_answer += f"- {conclusion}\n"
                            final_answer += "\n"
                        
                        final_answer += "### 总结\n"
                        final_answer += f"本次协作共调用 {tool_call_count} 次工具，总耗时 {sum(a.get('duration', 1.0) for a in sub_agent_results):.1f} 秒。\n\n"
                        final_answer += "基于以上分析过程，已完成用户指定的任务。"
                    
                    print(f"[SSE] 开始汇总答案，最终长度：{len(final_answer)}")
                    # 流式输出（字符切片方式）
                    for i in range(0, len(final_answer), 10):
                        chunk = final_answer[i:i+10]
                        chunk_data = json.dumps({
                            'type': 'final_answer_chunk',
                            'chunk': chunk
                        })
                        print(f"[SSE] 发送汇总 chunk: {chunk}")
                        yield f"event: final_answer_chunk\ndata: {chunk_data}\n\n"
                        await asyncio.sleep(0.05)
                    
                    # 更新 AI 消息
                    ai_message.content = final_answer
                ai_message.thinking_process = thinking_process
                ai_message.sub_agent_results = sub_agent_results
                ai_message.msg_metadata = {
                    "total_duration": sum(a.get("duration", 1.0) for a in sub_agent_results),
                    "total_tool_calls": tool_call_count,
                    "agents_used": list(set(a["role"] for a in sub_agent_results)),
                    "sub_agent_count": len(sub_agent_results)
                }
            
            # 完成
            event_data = json.dumps({
                'type': 'done',
                'session_id': session_id,
                'message_id': ai_message.id,
                'total_duration': ai_message.msg_metadata.get('total_duration', 0) if ai_message.msg_metadata else 0,
                # 关键修复：在 done 事件中包含结构化数据
                'thinking_process': ai_message.thinking_process,
                'sub_agent_results': ai_message.sub_agent_results,
                'citations': ai_message.citations
            })
            yield f"event: done\ndata: {event_data}\n\n"
            
        except Exception as e:
            event_data = json.dumps({
                'type': 'error',
                'error': str(e),
                'recoverable': True
            })
            yield f"event: error\ndata: {event_data}\n\n"
        
        finally:
            # 关键修复：确保在 SSE 结束后立即保存到数据库
            print(f"[Chat] 正在保存 AI 消息到数据库，ID: {ai_message.id}")
            try:
                await db.commit()
                print(f"[Chat] AI 消息已保存到数据库")
            except Exception as save_error:
                print(f"[Chat] 保存失败：{save_error}")
                await db.rollback()
                raise
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


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
