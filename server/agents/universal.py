"""
通用智能体 - 基于 ReAct 循环的单一智能体
核心理念：理解目标 → 规划步骤 → 调用工具 → 整合结果
"""
from typing import Dict, Any, AsyncGenerator, List, Optional
from datetime import datetime
import asyncio
import uuid
import json


class Thought:
    """思考数据结构"""
    
    def __init__(self, 
                 action: str,
                 reasoning: str,
                 tool: Optional[str] = None,
                 tool_args: Optional[Dict] = None,
                 step: int = 0):
        self.action = action  # "call_tool" or "finish"
        self.reasoning = reasoning  # 思考过程
        self.tool = tool  # 工具名称
        self.tool_args = tool_args  # 工具参数
        self.step = step  # 当前步骤
    
    def to_dict(self) -> Dict:
        return {
            "action": self.action,
            "reasoning": self.reasoning,
            "tool": self.tool,
            "tool_args": self.tool_args,
            "step": self.step
        }


class Observation:
    """观察数据结构"""
    
    def __init__(self,
                 result: Any,
                 success: bool,
                 error: Optional[str] = None,
                 metadata: Optional[Dict] = None):
        self.result = result
        self.success = success
        self.error = error
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        return {
            "result": self.result,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata
        }


class Reflection:
    """反思数据结构"""
    
    def __init__(self,
                 quality_score: float,
                 observation_summary: str,
                 adjustment: str,
                 should_continue: bool,
                 should_finish: bool = False):
        self.quality_score = quality_score  # 0-1 质量评分
        self.observation_summary = observation_summary  # 结果摘要
        self.adjustment = adjustment  # 策略调整
        self.should_continue = should_continue  # 是否继续执行
        self.should_finish = should_finish  # 是否结束任务
    
    def to_dict(self) -> Dict:
        return {
            "quality_score": self.quality_score,
            "observation_summary": self.observation_summary,
            "adjustment": self.adjustment,
            "should_continue": self.should_continue,
            "should_finish": self.should_finish
        }


class ExecutionState:
    """执行状态管理器"""
    
    def __init__(self, goal: str):
        self.id = str(uuid.uuid4())
        self.goal = goal
        self.created_at = datetime.utcnow()
        self.history: List[Dict] = []  # [(thought, observation), ...]
        self.current_step = 0
        self.is_completed = False
        self.total_tokens = 0
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.final_answer = ""
        
    def add_step(self, thought: Thought, observation: Observation, reflection: Reflection):
        """添加执行步骤到历史"""
        self.history.append({
            "step": self.current_step,
            "thought": thought.to_dict(),
            "observation": observation.to_dict(),
            "reflection": reflection.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        })
        self.current_step += 1
    
    def get_observation_summary(self) -> str:
        """获取所有观察的摘要"""
        if not self.history:
            return "尚未执行任何步骤"
        
        summaries = []
        for step_data in self.history[-3:]:  # 只看最近 3 步
            obs = step_data["observation"]
            if obs["success"]:
                summaries.append(f"步骤{step_data['step']}: {obs['metadata'].get('summary', '成功')}")
            else:
                summaries.append(f"步骤{step_data['step']}: 失败 - {obs['error']}")
        
        return "\n".join(summaries)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "current_step": self.current_step,
            "is_completed": self.is_completed,
            "history": self.history,
            "final_answer": self.final_answer,
            "duration": (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
            "total_tokens": self.total_tokens
        }


class UniversalAgent:
    """
    通用智能体 - 基于 ReAct 循环
    
    核心流程：
    1. Think: 基于当前状态决定下一步行动
    2. Act: 执行动作（调用工具或结束）
    3. Reflect: 评估执行质量，决定是否继续
    """
    
    def __init__(self, llm_provider, tool_manager=None):
        self.llm = llm_provider
        self.tool_manager = tool_manager
        self.max_steps = 15  # 最大执行步数
        self.step_timeout = 60  # 单步超时（秒）
        self.available_tools: List[Dict] = []
        
    async def discover_tools(self):
        """发现并注册可用工具"""
        if self.tool_manager:
            self.available_tools = await self.tool_manager.list_tools()
            print(f"[UniversalAgent] 🔧 发现 {len(self.available_tools)} 个可用工具")
        else:
            self.available_tools = []
            print("[UniversalAgent] ⚠️ 未配置工具管理器")
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        tools_info = ""
        if self.available_tools:
            tools_info = "\n\n可用工具列表：\n"
            for tool in self.available_tools:
                tools_info += f"- {tool.get('name', 'unknown')}: {tool.get('description', '')}\n"
                if tool.get('inputSchema'):
                    tools_info += f"  参数：{json.dumps(tool['inputSchema'], ensure_ascii=False)}\n"
        
        return f"""你是一个通用的 AI 智能体，擅长使用工具完成复杂任务。

你的工作流程遵循 ReAct 模式：
1. **思考 (Think)**: 分析当前情况，决定下一步行动
2. **行动 (Act)**: 调用工具执行具体任务，或宣布任务完成
3. **观察 (Observe)**: 查看工具执行结果
4. **反思 (Reflect)**: 评估结果质量，决定是否需要调整策略

重要规则：
- 每次只执行一个动作
- 如果信息不足，先调用工具收集信息
- 如果已掌握足够信息，立即结束任务并给出答案
- 工具调用失败时，尝试其他方法或请求更多信息
- 始终使用中文回复{tools_info}

请严格按照以下 JSON 格式返回你的决策：
{{
    "action": "call_tool" 或 "finish",
    "reasoning": "你的思考过程，为什么要这么做",
    "tool": "工具名称（仅当 action=call_tool 时需要）",
    "tool_args": {{工具参数字典（仅当 action=call_tool 时需要）}}
}}"""

    async def think(self, state: ExecutionState) -> Thought:
        """
        思考阶段：基于当前状态决定下一步
        
        Args:
            state: 当前执行状态
            
        Returns:
            Thought: 思考结果
        """
        # 构建提示词
        observation_summary = state.get_observation_summary()
        
        user_message = f"""当前任务目标：{state.goal}

已执行的步骤和结果：
{observation_summary}

当前是第 {state.current_step + 1} 步（最多 {self.max_steps} 步）。

请决定下一步行动。如果需要调用工具，请指定工具名称和参数。
如果认为已经可以完成任务，请选择"finish"行动。"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": user_message}
        ]
        
        try:
            # 调用 LLM
            result = await self.llm.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                stream=False
            )
            
            # 解析 JSON 响应
            content = result["content"]
            thought_data = json.loads(content)
            
            thought = Thought(
                action=thought_data.get("action", "finish"),
                reasoning=thought_data.get("reasoning", ""),
                tool=thought_data.get("tool"),
                tool_args=thought_data.get("tool_args", {}),
                step=state.current_step
            )
            
            # 更新 token 计数
            state.total_tokens += result.get("usage", {}).get("total_tokens", 0)
            
            print(f"[UniversalAgent] 💭 思考完成：{thought.action}")
            return thought
            
        except Exception as e:
            print(f"[UniversalAgent] ❌ 思考失败：{e}")
            # 降级方案：直接结束
            return Thought(
                action="finish",
                reasoning=f"思考过程出错：{str(e)}",
                step=state.current_step
            )
    
    async def act(self, thought: Thought, state: ExecutionState) -> Observation:
        """
        行动阶段：执行动作
        
        Args:
            thought: 思考结果
            state: 执行状态
            
        Returns:
            Observation: 执行结果观察
        """
        if thought.action == "finish":
            # 结束任务，生成最终答案
            return await self._synthesize_answer(state)
        
        elif thought.action == "call_tool":
            # 调用工具
            if not thought.tool:
                return Observation(
                    result=None,
                    success=False,
                    error="未指定工具名称"
                )
            
            try:
                print(f"[UniversalAgent] 🔧 调用工具：{thought.tool}")
                
                # 通过工具管理器调用
                if self.tool_manager:
                    result = await self.tool_manager.call_tool(
                        thought.tool,
                        thought.tool_args or {}
                    )
                else:
                    raise ValueError("未配置工具管理器")
                
                return Observation(
                    result=result,
                    success=result.get("success", False),
                    error=result.get("error"),
                    metadata={
                        "tool": thought.tool,
                        "args": thought.tool_args,
                        "summary": f"工具{thought.tool}执行成功"
                    }
                )
                
            except Exception as e:
                print(f"[UniversalAgent] ❌ 工具调用失败：{e}")
                return Observation(
                    result=None,
                    success=False,
                    error=str(e),
                    metadata={
                        "tool": thought.tool,
                        "args": thought.tool_args
                    }
                )
        
        else:
            return Observation(
                result=None,
                success=False,
                error=f"未知行动类型：{thought.action}"
            )
    
    async def _synthesize_answer(self, state: ExecutionState) -> Observation:
        """合成最终答案"""
        try:
            # 如果有执行历史，使用 LLM 整合结果
            if state.history:
                history_text = "\n".join([
                    f"步骤{i}: {step['observation']['metadata'].get('summary', '')}"
                    for i, step in enumerate(state.history)
                ])
                
                user_message = f"""任务目标：{state.goal}

已完成的执行步骤：
{history_text}

请基于以上执行结果，生成一份完整、专业的最终答案。要求：
1. 直接回答用户问题
2. 引用关键数据和发现
3. 结构清晰，逻辑连贯
4. 如有不确定之处，明确说明"""

                messages = [
                    {"role": "system", "content": "你是一个专业的 AI 助手，擅长整合多来源信息生成综合性报告。"},
                    {"role": "user", "content": user_message}
                ]
                
                result = await self.llm.chat_completion(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2048,
                    stream=False
                )
                
                state.total_tokens += result.get("usage", {}).get("total_tokens", 0)
                state.final_answer = result["content"]
                
            else:
                # 没有执行历史，直接回答
                state.final_answer = "基于已有知识，我无法提供更多信息。建议尝试其他查询方式。"
            
            return Observation(
                result=state.final_answer,
                success=True,
                metadata={"summary": "已生成最终答案"}
            )
            
        except Exception as e:
            print(f"[UniversalAgent] ❌ 合成答案失败：{e}")
            return Observation(
                result="答案生成失败",
                success=False,
                error=str(e)
            )
    
    async def reflect(self, observation: Observation, state: ExecutionState) -> Reflection:
        """
        反思阶段：评估执行质量
        
        Args:
            observation: 执行结果观察
            state: 执行状态
            
        Returns:
            Reflection: 反思结果
        """
        # 简单规则-based 反思
        quality_score = 0.5
        
        if observation.success:
            quality_score = 0.8
            observation_summary = "执行成功"
            adjustment = "保持当前策略"
            should_continue = True
        else:
            quality_score = 0.3
            observation_summary = f"执行失败：{observation.error}"
            adjustment = "尝试其他方法或工具"
            should_continue = state.current_step < self.max_steps - 1
        
        # 检查是否应该结束
        should_finish = (
            observation.metadata.get("tool") is None or  # 已经是 finish 行动
            state.current_step >= self.max_steps - 1 or  # 达到最大步数
            (observation.success and len(state.history) >= 3)  # 成功且至少有 3 步有效执行
        )
        
        reflection = Reflection(
            quality_score=quality_score,
            observation_summary=observation_summary,
            adjustment=adjustment,
            should_continue=should_continue and not should_finish,
            should_finish=should_finish
        )
        
        print(f"[UniversalAgent] 🤔 反思完成：质量={quality_score:.1f}, 应结束={should_finish}")
        return reflection
    
    async def execute(self, goal: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行 ReAct 循环（流式生成器）
        
        Args:
            goal: 任务目标
            
        Yields:
            SSE 事件字典
        """
        print(f"[UniversalAgent] 🚀 开始执行任务：{goal}")
        
        # 初始化状态
        state = ExecutionState(goal=goal)
        
        # 发现工具
        await self.discover_tools()
        
        # 发送初始事件
        yield {
            "type": "session_info",
            "data": {
                "execution_id": state.id,
                "goal": goal,
                "start_time": state.start_time.isoformat()
            }
        }
        
        # ReAct 循环
        while not state.is_completed and state.current_step < self.max_steps:
            try:
                # 1. Think
                print(f"\n[Step {state.current_step + 1}] 💭 思考中...")
                yield {
                    "type": "supervisor_thought",
                    "data": {
                        "step": state.current_step,
                        "action": "thinking",
                        "message": f"正在思考第{state.current_step + 1}步..."
                    }
                }
                
                thought = await self.think(state)
                yield {
                    "type": "supervisor_thought",
                    "data": thought.to_dict()
                }
                
                # 2. Act
                print(f"[Step {state.current_step + 1}] 🔧 行动中...")
                
                if thought.action == "call_tool":
                    yield {
                        "type": "tool_call_start",
                        "data": {
                            "step": state.current_step,
                            "tool": thought.tool,
                            "params": thought.tool_args
                        }
                    }
                
                observation = await self.act(thought, state)
                
                if thought.action == "call_tool":
                    yield {
                        "type": "tool_call_end",
                        "data": {
                            "step": state.current_step,
                            "tool": thought.tool,
                            "status": "success" if observation.success else "failed",
                            "result": observation.result,
                            "duration": 1.0
                        }
                    }
                
                # 3. Reflect
                print(f"[Step {state.current_step + 1}] 🤔 反思中...")
                reflection = await self.reflect(observation, state)
                yield {
                    "type": "reflection",
                    "data": reflection.to_dict()
                }
                
                # 4. 更新状态
                state.add_step(thought, observation, reflection)
                
                # 5. 检查是否完成
                if reflection.should_finish or thought.action == "finish":
                    state.is_completed = True
                    state.end_time = datetime.utcnow()
                    
                    # 发送最终答案
                    if state.final_answer:
                        yield {
                            "type": "final_answer_chunk",
                            "data": {
                                "chunk": state.final_answer
                            }
                        }
                    
                    # 发送完成事件
                    yield {
                        "type": "done",
                        "data": state.to_dict()
                    }
                    break
                
            except Exception as e:
                print(f"[UniversalAgent] ❌ 执行错误：{e}")
                import traceback
                traceback.print_exc()
                
                yield {
                    "type": "error",
                    "data": {
                        "error_type": "execution_error",
                        "message": str(e),
                        "recoverable": False
                    }
                }
                state.is_completed = True
                state.end_time = datetime.utcnow()
                break
        
        print(f"[UniversalAgent] ✅ 任务执行完成，共{state.current_step}步")
