"""
智能体系统 - 主智能体和子智能体
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import uuid


class AgentRole:
    """智能体角色定义"""
    
    SUPERVISOR = "supervisor"
    RESEARCHER = "researcher"
    CODER = "coder"
    ANALYZER = "analyzer"
    WRITER = "writer"
    REVIEWER = "reviewer"


# 预定义的智能体 System Prompt 模板
AGENT_PROMPTS = {
    AgentRole.RESEARCHER: """你是专业研究员，擅长从多来源检索信息并验证准确性。
你的职责：
1. 使用联网搜索、网页读取等工具获取信息
2. 验证信息来源的可靠性
3. 提取关键数据和事实
4. 将发现写入共享状态板

请确保信息准确、来源可靠、数据完整。""",

    AgentRole.CODER: """你是资深程序员，擅长编写高质量、可维护的代码。
你的职责：
1. 根据需求编写功能完整的代码
2. 添加适当的错误处理和日志
3. 遵循最佳实践和设计模式
4. 提供代码说明和使用示例

请确保代码简洁、高效、易读、安全。""",

    AgentRole.ANALYZER: """你是数据分析师，擅长从数据中提取洞察。
你的职责：
1. 读取共享状态板中的数据
2. 进行同比、环比、趋势分析
3. 计算关键指标和比率
4. 识别模式和异常

请确保分析深入、结论有据、可视化清晰。""",

    AgentRole.WRITER: """你是专业作家，擅长撰写结构化、有说服力的内容。
你的职责：
1. 整合所有子智能体的输出
2. 生成逻辑清晰、结构完整的报告
3. 标注引用来源
4. 确保语言流畅、专业

请确保内容完整、准确、易懂、有深度。""",

    AgentRole.REVIEWER: """你是质量审核专家，负责检查输出质量。
你的职责：
1. 验证数据的准确性和一致性
2. 检查逻辑是否严密
3. 发现潜在错误或遗漏
4. 提出改进建议

请确保最终输出高质量、无错误、可信赖。""",
}


class SharedBoard:
    """共享状态板"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.created_at = datetime.utcnow()
        self.key_findings: List[Dict] = []
        self.intermediate_conclusions: List[Dict] = []
        self.open_questions: List[Dict] = []
        self.help_requests: List[Dict] = []
        self.final_output: Optional[Dict] = None
    
    def add_finding(self, key: str, value: str, source_agent: str, 
                    confidence: float = 0.9, references: List[str] = None):
        """添加关键发现"""
        finding = {
            "key": key,
            "value": value,
            "source_agent": source_agent,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "references": references or []
        }
        self.key_findings.append(finding)
        return finding
    
    def add_conclusion(self, agent: str, conclusion: str, based_on: List[str]):
        """添加中间结论"""
        conclusion_obj = {
            "agent": agent,
            "conclusion": conclusion,
            "based_on": based_on,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.intermediate_conclusions.append(conclusion_obj)
        return conclusion_obj
    
    def ask_question(self, question: str, asked_by: str) -> Dict:
        """提出问题"""
        q = {
            "question": question,
            "asked_by": asked_by,
            "answered_by": None,
            "answer": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.open_questions.append(q)
        return q
    
    def answer_question(self, question: str, answered_by: str, answer: str):
        """回答问题"""
        for q in self.open_questions:
            if q["question"] == question:
                q["answered_by"] = answered_by
                q["answer"] = answer
                break
    
    def request_help(self, request: str, from_agent: str, assigned_to: str = None) -> Dict:
        """请求帮助"""
        help_req = {
            "request": request,
            "from_agent": from_agent,
            "assigned_to": assigned_to,
            "status": "pending",
            "response": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.help_requests.append(help_req)
        return help_req
    
    def respond_help(self, help_request: Dict, response: str):
        """响应帮助请求"""
        help_request["response"] = response
        help_request["status"] = "completed"
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat(),
            "key_findings": self.key_findings,
            "intermediate_conclusions": self.intermediate_conclusions,
            "open_questions": self.open_questions,
            "help_requests": self.help_requests,
            "final_output": self.final_output
        }


class SubAgent:
    """子智能体"""
    
    def __init__(self, role: str, task: str, tools: List[str], 
                 shared_board: SharedBoard):
        self.id = str(uuid.uuid4())
        self.role = role
        self.task = task
        self.available_tools = tools
        self.shared_board = shared_board
        self.status = "pending"  # pending/running/completed/failed
        self.output = None
        self.tool_calls = []
        self.duration = 0.0
        self.started_at = None
        self.completed_at = None
    
    async def execute(self, llm_client=None) -> Dict:
        """执行任务（真实 LLM 调用版）"""
        self.status = "running"
        self.started_at = datetime.utcnow()
        
        try:
            # 如果有 LLM 客户端，真实调用
            if llm_client:
                print(f"[SubAgent] 🚀 开始调用 LLM: {self.role}")
                
                # 构建提示词
                system_prompt = f"""你是一个{self.role}智能体。
你的任务是：{self.task}

请认真分析并完成任务，提供详细、专业、有深度的回答。使用中文回复。"""
                
                user_message = f"请完成以下任务：{self.task}\n\n用户原始查询：请根据任务描述完成相关工作。"
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
                
                # 调用 LLM
                result = await llm_client.chat_completion(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2048,
                    stream=False
                )
                
                self.output = result["content"]
                self.status = "completed"
                
                # 记录工具调用
                self.tool_calls = [
                    {"tool": "llm_inference", "model": llm_client.model, "tokens": result.get("usage", {}).get("total_tokens", 0)}
                ]
                
                print(f"[SubAgent] ✅ {self.role} 完成，输出长度：{len(self.output)}")
            else:
                # 降级方案：没有 LLM 时返回提示
                self.output = f"""【系统提示】

未配置 LLM 客户端，无法执行真实的智能推理。

任务角色：{self.role}
任务描述：{self.task}

建议：请在 .env 文件中配置有效的 LLM API 信息。"""
                self.status = "completed"
                self.tool_calls = []
                
        except Exception as e:
            print(f"[SubAgent] ❌ 执行失败：{e}")
            self.output = f"执行出错：{str(e)}"
            self.status = "failed"
            self.tool_calls = []
        
        self.completed_at = datetime.utcnow()
        self.duration = (self.completed_at - self.started_at).total_seconds()
        
        return {
            "agent_id": self.id,
            "role": self.role,
            "output": self.output,
            "task": self.task,
            "tool_calls": len(self.tool_calls),
            "duration": self.duration
        }



class SupervisorAgent:
    """主智能体（Supervisor）"""
    
    def __init__(self):
        self.id = "supervisor"
        self.current_task = None
        self.sub_agents: List[SubAgent] = []
        self.shared_board: Optional[SharedBoard] = None
    
    async def analyze_intent(self, query: str, llm_client=None) -> Dict:
        """分析用户意图（LLM 增强版）"""
        # 如果有 LLM 客户端，使用 LLM 进行深度语义分析
        if llm_client:
            return await self.analyze_intent_with_llm(query, llm_client)
        
        # 降级方案：规则 + 关键词匹配
        complexity = "simple"
        required_domains = []
        entities = []
        
        # 强制触发复杂任务的关键词（出现任意一个即判定为 complex）
        force_complex_keywords = [
            "网络", "搜索", "查找", "检索", "抓取", "查一下", "查询",  # 检索类
            "分析", "对比", "评估", "比较", "优缺点", "区别", "差异",  # 分析类
            "报告", "论文", "文章", "总结", "综述", "资料", "信息",  # 创作类
            "代码", "编程", "架构", "系统", "API", "实现",  # 技术类
            "调查", "研究", "调研", "探索", "排名", "榜单",  # 研究类
            "最新", "当前", "现在", "今天", "近期",  # 时效性
        ]
        
        # 加分关键词（每个 +0.1 分）
        bonus_keywords = [
            "帮我", "请问", "如何",  # 礼貌用语
            "为什么", "是什么", "怎么做",  # 疑问词
            "多个", "各种", "所有",  # 复数概念
        ]
        
        # 领域关键词
        domain_keywords = {
            "analysis": ["分析", "对比", "评估", "比较"],
            "finance": ["财报", "数据", "股价", "财务", "市值", "营收"],
            "coding": ["代码", "编程", "脚本", "程序", "函数"],
            "research": ["网络", "搜索", "查找", "检索", "报告"],
        }
        
        # 检测强制触发词
        for keyword in force_complex_keywords:
            if keyword in query:
                complexity = "complex"
                print(f"[Intent] 检测到强制触发词：'{keyword}'，判定为复杂任务")
                break
        
        # 如果还不是 complex，计算加分
        if complexity == "simple":
            score = 0.0
            for keyword in bonus_keywords:
                if keyword in query:
                    score += 0.1
            
            # 检测领域关键词
            for domain, keywords in domain_keywords.items():
                if any(kw in query for kw in keywords):
                    required_domains.append(domain)
                    score += 0.2
            
            # 如果包含多个实体名称（如"特斯拉"、"比亚迪"）
            if query.count("和") >= 1 or query.count("vs") >= 1 or query.count("对比") >= 1:
                score += 0.3
                print(f"[Intent] 检测到多实体对比")
            
            # 阈值判断
            if score >= 0.4:
                complexity = "complex"
                print(f"[Intent] 综合得分：{score} >= 0.4，判定为复杂任务")
            else:
                print(f"[Intent] 综合得分：{score} < 0.4，判定为简单任务")
        
        return {
            "complexity": complexity,
            "domains": required_domains,
            "entities": entities,
            "requires_multi_agent": complexity == "complex"
        }
    
    async def analyze_intent_with_llm(self, query: str, llm_client) -> Dict:
        """使用 LLM 进行深度意图分析"""
        try:
            system_prompt = """你是一个专业的任务分析专家。请分析用户查询并返回 JSON 格式的分析结果。

请严格按照以下 JSON Schema 返回：
{
    "complexity": "simple/medium/complex",
    "required_domains": ["research", "analysis", "coding", "writing"...],
    "entities": [{"name": "实体名", "type": "公司/人物/事件..."}],
    "implicit_needs": ["需要最新数据", "需要对比分析"...],
    "suggested_agents": ["Researcher", "Analyzer", "Coder", "Writer"...],
    "reasoning": "简要说明分析理由"
}

判断标准：
- simple: 单一事实查询、简单计算、常识性问题
- medium: 需要多步骤处理、基础数据分析、简单创作
- complex: 需要多智能体协作、网络搜索、复杂分析、长篇创作

领域定义：
- research: 需要检索信息、查找资料
- analysis: 需要数据分析、对比评估
- coding: 需要编写代码、技术方案
- writing: 需要创作文案、报告、文章"""
            
            user_message = f"请分析以下用户查询：\n\n{query}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            result = await llm_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
                stream=False
            )
            
            # 解析 JSON 响应
            import json
            content = result["content"]
            
            # 尝试提取 JSON（如果 LLM 返回了额外的文本）
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
            else:
                json_str = content
            
            analysis = json.loads(json_str)
            
            print(f"[Intent] LLM 分析结果：{analysis}")
            
            return {
                "complexity": analysis.get("complexity", "medium"),
                "domains": analysis.get("required_domains", []),
                "entities": analysis.get("entities", []),
                "implicit_needs": analysis.get("implicit_needs", []),
                "suggested_agents": analysis.get("suggested_agents", []),
                "reasoning": analysis.get("reasoning", ""),
                "requires_multi_agent": analysis.get("complexity") in ["complex", "medium"]
            }
            
        except Exception as e:
            print(f"[Intent] LLM 分析失败，降级到规则匹配：{e}")
            # 降级到规则匹配
            return await self.analyze_intent(query)
    
    async def decompose_task(self, query: str, intent: Dict, llm_client=None) -> List[Dict]:
        """拆解任务（LLM 增强版）"""
        # 如果有 LLM 客户端，使用 LLM 进行智能拆解
        if llm_client:
            return await self.decompose_task_with_llm(query, intent, llm_client)
        
        # 降级方案：基于规则的拆解
        sub_tasks = []
        
        # 检测是否包含网络搜索需求
        has_search_intent = any(kw in query for kw in ["网络", "搜索", "查找", "检索", "报告", "调查"])
        
        if "分析" in query and "对比" in query:
            # 财报分析类任务
            sub_tasks = [
                {"role": AgentRole.RESEARCHER, "task": "检索相关财报数据"},
                {"role": AgentRole.ANALYZER, "task": "对比分析关键指标"},
                {"role": AgentRole.WRITER, "task": "生成分析报告"},
            ]
        elif has_search_intent:
            # 网络搜索类任务
            print(f"[Decompose] 检测到网络搜索意图，创建 Researcher 智能体")
            sub_tasks = [
                {"role": AgentRole.RESEARCHER, "task": f"从网络检索相关信息：{query[:50]}"},
                {"role": AgentRole.WRITER, "task": "整理和总结检索到的信息"},
            ]
        elif "代码" in query or "编程" in query:
            # 编程类任务
            sub_tasks = [
                {"role": AgentRole.CODER, "task": "编写代码"},
                {"role": AgentRole.REVIEWER, "task": "代码审查"},
            ]
        else:
            # 通用任务
            sub_tasks = [
                {"role": AgentRole.RESEARCHER, "task": "信息检索"},
                {"role": AgentRole.WRITER, "task": "整理答案"},
            ]
        
        return sub_tasks[:4]  # 最多 4 个子智能体
    
    async def decompose_task_with_llm(self, query: str, intent: Dict, llm_client) -> List[Dict]:
        """使用 LLM 进行智能任务拆解"""
        try:
            system_prompt = """你是一个专业的任务规划师。请将复杂任务拆解为可执行的子任务。

请严格按照以下 JSON Schema 返回子任务列表：
[
    {
        "role": "Researcher/Analyzer/Coder/Writer/Reviewer",
        "task": "具体任务描述",
        "depends_on": [],  // 依赖的子任务索引，如 [0] 表示依赖第一个任务
        "tools": ["工具名 1", "工具名 2"]  // 建议使用的工具
    }
]

角色定义：
- Researcher: 负责信息检索、网络搜索、资料收集
- Analyzer: 负责数据分析、对比评估、洞察提取
- Coder: 负责编写代码、技术方案实现
- Writer: 负责文案创作、报告撰写、内容整合
- Reviewer: 负责质量审核、事实核查、一致性验证

拆解原则：
1. 每个子任务应该是独立可执行的
2. 明确任务间的依赖关系（串行/并行）
3. 合理分配工具使用
4. 最多创建 4 个子任务
5. 确保任务顺序符合逻辑"""
            
            user_message = f"""请基于以下意图分析结果，将任务拆解为子任务：

用户查询：{query}

意图分析：
- 复杂度：{intent.get('complexity', 'medium')}
- 领域：{intent.get('domains', [])}
- 实体：{intent.get('entities', [])}
- 隐含需求：{intent.get('implicit_needs', [])}
- 推荐智能体：{intent.get('suggested_agents', [])}

请输出 JSON 数组格式的子任务列表。"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            result = await llm_client.chat_completion(
                messages=messages,
                temperature=0.5,
                max_tokens=2048,
                stream=False
            )
            
            # 解析 JSON 响应
            import json
            content = result["content"]
            
            # 尝试提取 JSON 数组
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
            else:
                json_str = content
            
            sub_tasks = json.loads(json_str)
            
            print(f"[Decompose] LLM 拆解结果：{sub_tasks}")
            
            # 验证和规范化
            validated_tasks = []
            for i, task in enumerate(sub_tasks[:4]):  # 最多 4 个
                role = task.get("role", "Researcher")
                # 标准化角色名称
                role_mapping = {
                    "researcher": AgentRole.RESEARCHER,
                    "analyzer": AgentRole.ANALYZER,
                    "coder": AgentRole.CODER,
                    "writer": AgentRole.WRITER,
                    "reviewer": AgentRole.REVIEWER
                }
                normalized_role = role_mapping.get(role.lower(), AgentRole.RESEARCHER)
                
                validated_tasks.append({
                    "role": normalized_role,
                    "task": task.get("task", ""),
                    "depends_on": task.get("depends_on", []),
                    "tools": task.get("tools", [])
                })
            
            return validated_tasks
            
        except Exception as e:
            print(f"[Decompose] LLM 拆解失败，降级到规则匹配：{e}")
            # 降级到规则匹配
            return await self.decompose_task(query, intent)
    
    async def create_sub_agents(self, sub_tasks: List[Dict]) -> List[SubAgent]:
        """创建子智能体"""
        agents = []
        for task_info in sub_tasks:
            # 为每个子智能体分配工具
            tools = self._assign_tools(task_info["role"])
            agent = SubAgent(
                role=task_info["role"],
                task=task_info["task"],
                tools=tools,
                shared_board=self.shared_board
            )
            agents.append(agent)
        return agents
    
    def _assign_tools(self, role: str) -> List[str]:
        """为智能体分配工具（最小权限原则）"""
        tool_mapping = {
            AgentRole.RESEARCHER: ["web_search", "news_search", "web_reader"],
            AgentRole.CODER: ["code_interpreter", "file_read", "file_write"],
            AgentRole.ANALYZER: ["data_analysis", "calculator", "chart_generator"],
            AgentRole.WRITER: ["text_summarizer", "markdown_formatter"],
            AgentRole.REVIEWER: ["fact_checker", "consistency_validator"],
        }
        return tool_mapping.get(role, [])
    
    async def execute(self, query: str, llm_client=None) -> Dict:
        """执行完整任务流程
        
        Args:
            query: 用户查询
            llm_client: LLM 客户端（可选）
        """
        # 1. 意图分析（传入 LLM 客户端）
        intent = await self.analyze_intent(query, llm_client=llm_client)
        
        # 2. 判断是否需要多智能体
        if not intent["requires_multi_agent"]:
            # 简单任务，直接回答（如果有 LLM 就调用，否则用预设答案）
            if llm_client:
                # 使用 LLM 生成答案
                system_prompt = "你是一个智能助手。请用中文详细、专业地回答用户的问题。"
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ]
                
                result = await llm_client.chat_completion(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2048,
                    stream=False
                )
                
                return {
                    "content": result["content"],
                    "is_simple": True,
                    "usage": result.get("usage", {})
                }
            else:
                # 降级方案：使用预设答案
                return await self._simple_answer(query)
        
        # 3. 复杂任务：创建共享状态板
        self.shared_board = SharedBoard(str(uuid.uuid4()))
        
        # 4. 任务拆解（传入 LLM 客户端）
        sub_tasks = await self.decompose_task(query, intent, llm_client=llm_client)
        
        # 5. 创建子智能体
        self.sub_agents = await self.create_sub_agents(sub_tasks)
        
        # 6. 并行执行子任务（传入 LLM 客户端）
        results = await asyncio.gather(
            *[agent.execute(llm_client=llm_client) for agent in self.sub_agents],
            return_exceptions=True
        )
        
        # 7. 汇总结果
        final_answer = await self._aggregate_results(results)
        
        return {
            "task_id": self.shared_board.task_id,
            "intent": intent,
            "sub_agents": [
                {
                    "id": a.id,
                    "role": a.role,
                    "task": a.task,
                    "status": a.status,
                    "output": a.output,
                    "duration": a.duration
                }
                for a in self.sub_agents
            ],
            "shared_board": self.shared_board.to_dict(),
            "final_answer": final_answer
        }
    
    async def _simple_answer(self, query: str) -> Dict:
        """简单任务直接回答（增强版：生成有意义的答案）"""
        # MVP: 根据问题类型生成模拟答案
        
        # 检测问题类型并生成对应答案
        if "lmarena" in query.lower() or "排名" in query or "模型" in query:
            # lmarena 排名查询
            content = f"""【LM Arena 模型排名信息】

根据您的查询："{query}"

由于我暂时无法实时访问 lmarena 官网，以下是基于我的知识的参考信息：

## LM Arena (Language Model Arena) 简介

LM Arena 是一个由 LMSYS 组织创建的开放式大模型评测平台，采用众包投票机制对模型进行排名。

## 当前主流模型排名（参考数据）

### 第 1 梯队（顶级模型）
1. **GPT-4 Turbo / GPT-4o** (OpenAI)
   - 优势：综合能力强，推理、编码、多模态表现优异
   - 典型应用：复杂任务处理、创意写作

2. **Claude 3 Opus** (Anthropic)
   - 优势：长上下文理解、逻辑推理、安全性高
   - 典型应用：文档分析、法律医疗等专业领域

3. **Gemini Ultra / Pro** (Google)
   - 优势：多模态能力、跨语言性能
   - 典型应用：图像文本联合任务

### 第 2 梯队（优秀模型）
4. **Qwen 2.5 72B** (阿里巴巴)
   - 开源模型中的佼佼者
   - 在数学和编码任务上表现出色

5. **Llama 3 70B** (Meta)
   - 开源生态最完善的模型
   - 社区支持强大，应用广泛

6. **Mistral Large** (Mistral AI)
   - 欧洲最强模型
   - 多语言能力和代码能力均衡

### 其他值得关注的模型
- **Command R+** (Cohere): 企业级应用，RAG 能力强
- **DBRX** (Databricks): 开源混合专家模型 (MoE)
- **Yi Large** (零一万物): 中文能力强

## 获取最新排名的方式

如需查看实时排名，建议访问：
- 🌐 官方网站：https://lmarena.ai/
- 📊 排行榜链接：https://lmarena.ai/?leaderboard
- 📱 也可通过 Hugging Face Open LLM Leaderboard 查看

*注：以上信息仅供参考，具体排名请以官网最新数据为准。*
"""
        elif "天气" in query or "气温" in query:
            content = f"""【天气信息】

根据您的查询："{query}"

由于我暂时无法实时获取天气数据，建议您：
1. 访问中国天气网：http://www.nmc.cn/
2. 使用天气 API 服务（如和风天气、心知天气）
3. 在手机或电脑上安装天气应用

如果您告诉我具体城市，我可以提供该城市的一般气候特征。"""
        
        elif "时间" in query or "日期" in query:
            from datetime import datetime
            now = datetime.now()
            content = f"""【当前时间信息】

现在是：{now.strftime('%Y年%m月%d日 %H:%M:%S')}
时区：东八区（北京时间）

今天是：{now.strftime('%A')}
今年的第 {now.timetuple().tm_yday} 天"""
        
        else:
            # 通用问题：基于知识回答
            content = f"""【问题解答】

根据您的查询："{query}"

这是一个很好的问题。基于我的知识库，我可以提供以下信息：

## 相关背景

这个问题涉及到多个方面，让我为您详细解释：

1. **概念说明**
   - 这是指...
   - 主要特点是...
   - 应用场景包括...

2. **关键要点**
   - 要点一：...
   - 要点二：...
   - 要点三：...

3. **实用建议**
   - 如果您需要深入了解，建议...
   - 可以参考的资料有...
   - 常见的解决方案包括...

## 进一步帮助

如果您有更具体的需求，比如：
- 需要实时数据（如股价、天气、新闻）
- 需要专业领域的深度分析
- 需要代码实现或技术方案

请随时告诉我，我会调用相应的工具或服务来帮助您。
"""
        
        return {
            "content": content,
            "is_simple": True
        }
    
    async def _aggregate_results(self, results: List) -> str:
        """汇总子智能体结果（增强版）"""
        # 关键修复：直接使用子智能体的实际输出作为最终答案
        outputs = []
        
        for result in results:
            if isinstance(result, Exception):
                outputs.append(f"执行出错：{str(result)}")
            else:
                output = result.get("output", "")
                role = result.get("role", "")
                task = result.get("task", "")
                
                # 如果有实际输出，直接使用
                if output and len(output) > 50:
                    outputs.append(output)
        
        # 如果所有子智能体都有实质性输出，返回拼接结果
        if outputs:
            return "\n\n---\n\n".join(outputs)
        
        # 兜底方案：如果没有有效输出，生成简单报告
        return f"已完成任务处理。共执行 {len(results)} 个子任务。"
