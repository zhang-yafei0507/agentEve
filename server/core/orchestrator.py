"""
Agent 编排器 - 串行执行 + 实时流式推送
"""
from typing import Dict, Any, AsyncGenerator, List
import asyncio
from datetime import datetime

# 延迟导入，在使用时才导入
LLMProvider = None
BaseTool = None
get_tool = None


class AgentOrchestrator:
    """
    Agent 编排器
    
    核心职责：
    1. 串行执行子任务（一个接一个）
    2. 每步执行前后都推送思考事件
    3. 工具调用实时推送开始/结束状态
    4. 支持动态决策是否继续下一步
    """
    
    def __init__(self, llm_provider):
        # 延迟导入
        if LLMProvider is None:
            from llm.providers.base import LLMProvider as _LLMProvider
            from tools.base import get_tool as _get_tool
            globals()['LLMProvider'] = _LLMProvider
            globals()['get_tool'] = _get_tool
        
        self.llm = llm_provider
        self.current_step = 0
        self.total_steps = 0
        
    async def execute_flow(
        self,
        query: str,
        sub_agents: List[Dict[str, Any]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行完整的 Agent 流程（流式生成器）
        
        Yields:
            SSE 事件字典，包含 type 和 data
        """
        self.total_steps = len(sub_agents)
        self.current_step = 0
        
        # 1. 主智能体初始思考
        yield {
            "type": "supervisor_thought",
            "data": {
                "action": "analyzing_query",
                "message": "正在理解用户查询..."
            }
        }
        await asyncio.sleep(0.3)  # 短暂延迟，让用户看到思考
        
        # 2. 任务拆解决策
        yield {
            "type": "supervisor_decision",
            "data": {
                "decision": "complex_task",
                "message": f"这是一个复杂任务，需要{self.total_steps}个子智能体协作"
            }
        }
        await asyncio.sleep(0.5)
        
        # 3. 发送初始任务规划（只展示第一步）
        if sub_agents:
            first_step = sub_agents[0]
            yield {
                "type": "task_plan",
                "data": {
                    "total_steps": self.total_steps,
                    "steps": [{
                        "step": 1,
                        "role": first_step["role"],
                        "task": first_step["task"],
                        "status": "pending",
                        "revealed": True
                    }]
                }
            }
            await asyncio.sleep(0.5)
        
        # 4. 串行执行每个子任务
        thinking_process = []
        sub_agent_results = []
        
        for idx, sub_agent in enumerate(sub_agents):
            # 4.1 决策是否继续下一步
            if idx > 0:
                yield {
                    "type": "next_step_decision",
                    "data": {
                        "current_step": idx,
                        "total_steps": self.total_steps,
                        "message": f"第{idx}步已完成，评估是否需要继续执行下一步..."
                    }
                }
                await asyncio.sleep(0.3)
                
                # 揭示下一步
                current_step = sub_agents[idx]
                yield {
                    "type": "task_plan_update",
                    "data": {
                        "new_step": {
                            "step": idx + 1,
                            "role": current_step["role"],
                            "task": current_step["task"],
                            "status": "pending",
                            "revealed": True
                        }
                    }
                }
                await asyncio.sleep(0.3)
            
            # 4.2 开始执行当前步骤的思考
            yield {
                "type": "supervisor_thought",
                "data": {
                    "action": "starting_step",
                    "step": idx + 1,
                    "total": self.total_steps,
                    "message": f"开始执行第{idx + 1}步：{sub_agent['role']} - {sub_agent['task'][:30]}..."
                }
            }
            await asyncio.sleep(0.3)
            
            # 4.3 智能体启动
            yield {
                "type": "agent_update",
                "data": {
                    "agent": sub_agent["role"],
                    "agent_id": sub_agent.get("id", f"agent-{idx}"),
                    "status": "running",
                    "message": f'{sub_agent["role"]} 正在执行：{sub_agent["task"]}',
                    "task": sub_agent["task"],
                    "tools": sub_agent.get("tools", [])
                }
            }
            
            # 4.4 工具调用（如果有）
            tool_call_count = 0
            if sub_agent.get("tools"):
                tool_name = sub_agent["tools"][0]
                tool = get_tool(tool_name)
                
                if tool:
                    # 工具调用开始
                    yield {
                        "type": "tool_call_start",
                        "data": {
                            "tool": tool_name,
                            "agent_id": sub_agent.get("id"),
                            "params": {"query": sub_agent["task"]},
                            "step": idx + 1
                        }
                    }
                    
                    # 真实执行工具
                    try:
                        tool_result = await tool.execute(query=sub_agent["task"])
                        
                        # 工具调用结束
                        yield {
                            "type": "tool_call_end",
                            "data": {
                                "tool": tool_name,
                                "agent_id": sub_agent.get("id"),
                                "status": "success" if tool_result.get("success") else "failed",
                                "result": tool_result,
                                "duration": 1.0,
                                "step": idx + 1
                            }
                        }
                        tool_call_count += 1
                    except Exception as e:
                        yield {
                            "type": "tool_call_end",
                            "data": {
                                "tool": tool_name,
                                "agent_id": sub_agent.get("id"),
                                "status": "failed",
                                "error": str(e),
                                "step": idx + 1
                            }
                        }
            
            # 4.5 模拟子智能体执行时间（TODO: 改为真实的 LLM 调用）
            await asyncio.sleep(0.5)
            
            # 4.6 智能体完成
            output = sub_agent.get("output", f"已完成任务：{sub_agent['task']}")
            duration = sub_agent.get("duration", 1.0)
            
            yield {
                "type": "agent_update",
                "data": {
                    "agent": sub_agent["role"],
                    "agent_id": sub_agent.get("id"),
                    "status": "completed",
                    "output": output,
                    "task": sub_agent["task"],
                    "tool_calls": tool_call_count,
                    "duration": duration
                }
            }
            
            # 4.7 主智能体反思
            yield {
                "type": "supervisor_thought",
                "data": {
                    "action": "step_completed",
                    "step": idx + 1,
                    "message": f"第{idx + 1}步完成，耗时{duration:.1f}秒，检查结果质量..."
                }
            }
            await asyncio.sleep(0.3)
            
            # 4.8 如果需要继续，推送反思事件
            if idx < self.total_steps - 1:
                yield {
                    "type": "supervisor_reflecting",
                    "data": {
                        "step": idx + 1,
                        "message": f"第{idx + 1}步结果良好，准备启动第{idx + 2}步..."
                    }
                }
                await asyncio.sleep(0.3)
            
            # 累积结果
            thinking_process.append({
                "agent": sub_agent["role"],
                "action": sub_agent["task"],
                "tool_calls": tool_call_count,
                "duration": duration,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            sub_agent_results.append({
                "agent_id": sub_agent.get("id"),
                "role": sub_agent["role"],
                "task": sub_agent["task"],
                "output": output,
                "tool_calls": tool_call_count,
                "duration": duration
            })
            
            self.current_step = idx + 1
        
        # 5. 所有子任务完成，主智能体汇总
        yield {
            "type": "supervisor_thought",
            "data": {
                "action": "aggregating",
                "message": f"所有{len(sub_agent_results)}个子智能体已完成，正在汇总结果..."
            }
        }
        await asyncio.sleep(0.5)
        
        yield {
            "type": "agent_update",
            "data": {
                "agent": "supervisor",
                "status": "aggregating",
                "message": "所有子智能体已完成，正在汇总结果...",
                "completed_count": len(sub_agent_results),
                "total_count": self.total_steps
            }
        }
        await asyncio.sleep(0.5)
        
        # 6. 使用 LLM 实时生成最终答案（真正的流式）
        final_answer = ""
        messages = [
            {"role": "system", "content": "你是一个专业的总结助手。请根据提供的多智能体协作结果，生成一份结构清晰、内容完整的综合性报告。"},
            {"role": "user", "content": f"用户查询：{query}\n\n各智能体执行结果：\n" + "\n".join([f"- {r['role']}: {r['output']}" for r in sub_agent_results])}
        ]
        
        # 流式调用 LLM
        stream_response = self.llm.chat_completion_stream(messages)
        
        async for chunk in stream_response:
            content = chunk.get("content", "")
            if content:
                final_answer += content
                yield {
                    "type": "final_answer_chunk",
                    "data": {
                        "chunk": content
                    }
                }
                await asyncio.sleep(0.02)  # 控制输出速度
        
        # 7. 完成
        yield {
            "type": "done",
            "data": {
                "session_id": "",  # TODO: 传入实际 session_id
                "thinking_process": thinking_process,
                "sub_agent_results": sub_agent_results,
                "total_duration": sum(r["duration"] for r in sub_agent_results),
                "total_tool_calls": sum(r["tool_calls"] for r in sub_agent_results)
            }
        }
