"""
LangGraph 状态机：主从智能体编排、共享状态板、工具调用、SSE 事件流。
"""

import asyncio
import json
import logging
import time
from typing import Any, Annotated, Optional, Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings
from app.mcp.mcp_manager import MCPToolManager
from app.agents.prompts import (
    SUPERVISOR_PLAN_PROMPT,
    RESEARCHER_PROMPT,
    CODER_PROMPT,
    ANALYZER_PROMPT,
    REVIEWER_PROMPT,
    SYNTHESIZE_PROMPT,
)
from app.utils.trace import generate_trace_id

logger = logging.getLogger("agent_engine")


# ═══════════════════════════════════════════════════
#  State 定义
# ═══════════════════════════════════════════════════

def _merge_dicts(a: dict, b: dict) -> dict:
    merged = a.copy()
    merged.update(b)
    return merged


def _concat_lists(a: list, b: list) -> list:
    return a + b


class AgentState(dict):
    """LangGraph 全局状态"""
    query: str
    trace_id: str
    plan: dict
    shared_board: dict                          # 共享状态板
    pending_tasks: list[str]
    completed_tasks: list[str]
    agent_outputs: dict[str, str]
    tool_calls_log: list[dict]
    final_answer: str
    iteration_count: int


# 使用 TypedDict + Annotated 让 LangGraph 自动合并
from typing import TypedDict


class GraphState(TypedDict):
    query: str
    trace_id: str
    plan: dict
    shared_board: Annotated[dict, _merge_dicts]
    pending_tasks: list[str]                    # 每次替换
    completed_tasks: Annotated[list[str], _concat_lists]
    agent_outputs: Annotated[dict[str, str], _merge_dicts]
    tool_calls_log: Annotated[list[dict], _concat_lists]
    final_answer: str
    iteration_count: int


# ═══════════════════════════════════════════════════
#  Agent 名 → Prompt 映射
# ═══════════════════════════════════════════════════

AGENT_PROMPTS = {
    "researcher": RESEARCHER_PROMPT,
    "coder": CODER_PROMPT,
    "analyzer": ANALYZER_PROMPT,
    "reviewer": REVIEWER_PROMPT,
}


# ═══════════════════════════════════════════════════
#  工具调用 ReAct 循环 (供所有 Worker 共用)
# ═══════════════════════════════════════════════════

async def _react_loop(
    agent_name: str,
    system_prompt: str,
    user_content: str,
    mcp_manager: MCPToolManager,
    event_queue: asyncio.Queue,
    trace_id: str,
    max_iters: int = None,
) -> tuple[str, list[dict]]:
    """
    在一个 Worker 内执行 ReAct 循环：
    1. 调 LLM (带 tools)
    2. 若返回 tool_calls → 执行 → 结果回传 → 回到 1
    3. 若返回文本 → 结束
    返回 (最终文本，tool_call_logs)
    """
    if max_iters is None:
        max_iters = settings.MAX_TOOL_ITERATIONS

    model = ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=0.2,
        timeout=settings.AGENT_TIMEOUT,
    )

    tool_schemas = mcp_manager.get_enabled_tool_schemas()
    if tool_schemas:
        model = model.bind_tools(tool_schemas)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    tool_logs: list[dict] = []

    for iteration in range(max_iters):
        response: AIMessage = await model.ainvoke(messages)

        if not response.tool_calls:
            return response.content or "", tool_logs

        # 处理每个 tool call
        messages.append(response)

        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_call_id = tc["id"]

            # 发送 SSE 事件
            await event_queue.put({
                "type": "tool_call",
                "agent": agent_name,
                "tool": tool_name,
                "args": tool_args,
                "trace_id": trace_id,
            })

            try:
                result = await asyncio.wait_for(
                    mcp_manager.call_tool(tool_name, tool_args, agent_name, trace_id),
                    timeout=30,
                )
            except asyncio.TimeoutError:
                result = f"Error: Tool '{tool_name}' timed out after 30s"
            except Exception as e:
                result = f"Error calling tool '{tool_name}': {e}"

            tool_logs.append({
                "agent": agent_name,
                "tool": tool_name,
                "args": tool_args,
                "result": result[:500],
                "trace_id": trace_id,
            })

            await event_queue.put({
                "type": "tool_result",
                "agent": agent_name,
                "tool": tool_name,
                "result": result[:300],
                "trace_id": trace_id,
            })

            messages.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))

    # 超过循环上限，最后一次无 tool call 的 invoke
    final = await model.ainvoke(messages)
    return final.content or "", tool_logs


# ═══════════════════════════════════════════════════
#  Graph 节点函数
# ═══════════════════════════════════════════════════

async def supervisor_plan_node(state: GraphState, config: dict) -> dict:
    """主智能体：分析 query，生成执行计划或直接作答"""
    eq: asyncio.Queue = config["configurable"]["event_queue"]
    trace_id = state["trace_id"]

    await eq.put({"type": "thinking", "agent": "supervisor", "content": "Analyzing query complexity…", "trace_id": trace_id})

    model = ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=0,
        timeout=settings.AGENT_TIMEOUT,
    )

    messages = [
        SystemMessage(content=SUPERVISOR_PLAN_PROMPT),
        HumanMessage(content=state["query"]),
    ]
    resp = await model.ainvoke(messages)
    raw = resp.content.strip()

    # 解析 JSON
    try:
        # 兼容 markdown 代码块包裹
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        plan = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"[{trace_id}] Supervisor returned invalid JSON, treating as simple")
        plan = {"complexity": "simple", "direct_answer": raw}

    await eq.put({"type": "plan", "plan": plan, "trace_id": trace_id})

    if plan.get("complexity") == "simple":
        return {
            "plan": plan,
            "final_answer": plan.get("direct_answer", raw),
        }

    # 复杂任务：提取 pending_tasks
    tasks = plan.get("tasks", [])
    agents_needed = [t["agent"] for t in tasks if t["agent"] in AGENT_PROMPTS]
    if not agents_needed:
        return {"plan": plan, "final_answer": plan.get("direct_answer", raw)}

    return {
        "plan": plan,
        "pending_tasks": agents_needed,
    }


async def worker_dispatch_node(state: GraphState, config: dict) -> dict:
    """路由节点：递增迭代计数，防死循环"""
    count = state.get("iteration_count", 0) + 1
    if count > settings.MAX_GRAPH_ITERATIONS:
        return {"pending_tasks": [], "iteration_count": count,
                "final_answer": "Error: max graph iterations exceeded"}
    return {"iteration_count": count}


def _build_worker_node(agent_name: str):
    """工厂函数：为每种 worker 生成节点处理函数"""

    async def _node(state: GraphState, config: dict) -> dict:
        eq: asyncio.Queue = config["configurable"]["event_queue"]
        mcp_mgr: MCPToolManager = config["configurable"]["mcp_manager"]
        trace_id = state["trace_id"]

        # 从 plan 找到当前 agent 的任务描述
        task_desc = ""
        for t in state.get("plan", {}).get("tasks", []):
            if t["agent"] == agent_name:
                task_desc = t.get("description", "")
                break

        # 构建上下文：共享状态板
        board_lines = []
        for k, v in state.get("shared_board", {}).items():
            board_lines.append(f"### {k}\n{v}")
        shared_context = "\n\n".join(board_lines) if board_lines else "(empty)"

        user_content = (
            f"## Your Task\n{task_desc}\n\n"
            f"## Original User Query\n{state['query']}\n\n"
            f"## Shared Board (results from other agents)\n{shared_context}"
        )

        await eq.put({
            "type": "agent_start",
            "agent": agent_name,
            "task": task_desc,
            "trace_id": trace_id,
        })

        try:
            output, tool_logs = await asyncio.wait_for(
                _react_loop(
                    agent_name=agent_name,
                    system_prompt=AGENT_PROMPTS[agent_name],
                    user_content=user_content,
                    mcp_manager=mcp_mgr,
                    event_queue=eq,
                    trace_id=trace_id,
                ),
                timeout=settings.AGENT_TIMEOUT,
            )
        except asyncio.TimeoutError:
            output = f"Agent '{agent_name}' timed out after {settings.AGENT_TIMEOUT}s"
            tool_logs = []
            logger.error(f"[{trace_id}] {output}")
        except Exception as e:
            output = f"Agent '{agent_name}' error: {e}"
            tool_logs = []
            logger.error(f"[{trace_id}] {output}")

        # 写入共享状态板
        board_key = f"{agent_name}_output"

        await eq.put({
            "type": "shared_state_update",
            "key": board_key,
            "value": output[:500],
            "by": agent_name,
            "trace_id": trace_id,
        })
        await eq.put({
            "type": "agent_complete",
            "agent": agent_name,
            "output": output[:800],
            "trace_id": trace_id,
        })

        new_pending = [t for t in state.get("pending_tasks", []) if t != agent_name]

        return {
            "shared_board": {board_key: output},
            "agent_outputs": {agent_name: output},
            "completed_tasks": [agent_name],
            "pending_tasks": new_pending,
            "tool_calls_log": tool_logs,
        }

    _node.__name__ = f"{agent_name}_node"
    return _node


async def synthesize_node(state: GraphState, config: dict) -> dict:
    """主智能体：汇总所有 worker 输出，生成最终回答"""
    eq: asyncio.Queue = config["configurable"]["event_queue"]
    trace_id = state["trace_id"]

    await eq.put({"type": "thinking", "agent": "supervisor", "content": "Synthesizing final answer…", "trace_id": trace_id})

    if not state.get("agent_outputs"):
        return {"final_answer": state.get("final_answer", "No results")}

    results_text = "\n\n".join(
        f"## {agent} Output\n{output}"
        for agent, output in state["agent_outputs"].items()
    )

    model = ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=0.3,
        timeout=settings.AGENT_TIMEOUT,
    )
    messages = [
        SystemMessage(content=SYNTHESIZE_PROMPT),
        HumanMessage(content=f"## User Query\n{state['query']}\n\n## Agent Results\n{results_text}"),
    ]
    resp = await model.ainvoke(messages)

    final = resp.content or ""
    await eq.put({"type": "response", "content": final, "trace_id": trace_id})

    return {"final_answer": final}


# ═══════════════════════════════════════════════════
#  条件路由函数
# ═══════════════════════════════════════════════════

def route_after_plan(state: GraphState) -> str:
    if state.get("final_answer"):
        return "done"
    return "worker_dispatch"


def route_to_worker(state: GraphState) -> str:
    pending = state.get("pending_tasks", [])
    if not pending:
        return "synthesize"

    completed = set(state.get("completed_tasks", []))
    tasks = state.get("plan", {}).get("tasks", [])

    # 按依赖顺序找第一个可执行的
    for t in tasks:
        agent = t["agent"]
        if agent in pending:
            deps = set(t.get("dependencies", []))
            if deps.issubset(completed):
                return agent

    # 保底：取 pending 第一个
    return pending[0]


# ═══════════════════════════════════════════════════
#  构建 Graph
# ═══════════════════════════════════════════════════

def build_graph():
    graph = StateGraph(GraphState)

    # 添加节点
    graph.add_node("supervisor_plan", supervisor_plan_node)
    graph.add_node("worker_dispatch", worker_dispatch_node)
    graph.add_node("researcher", _build_worker_node("researcher"))
    graph.add_node("coder", _build_worker_node("coder"))
    graph.add_node("analyzer", _build_worker_node("analyzer"))
    graph.add_node("reviewer", _build_worker_node("reviewer"))
    graph.add_node("synthesize", synthesize_node)

    # 边
    graph.add_edge(START, "supervisor_plan")

    graph.add_conditional_edges("supervisor_plan", route_after_plan, {
        "done": END,
        "worker_dispatch": "worker_dispatch",
    })

    graph.add_conditional_edges("worker_dispatch", route_to_worker, {
        "researcher": "researcher",
        "coder": "coder",
        "analyzer": "analyzer",
        "reviewer": "reviewer",
        "synthesize": "synthesize",
    })

    graph.add_edge("researcher", "worker_dispatch")
    graph.add_edge("coder", "worker_dispatch")
    graph.add_edge("analyzer", "worker_dispatch")
    graph.add_edge("reviewer", "worker_dispatch")
    graph.add_edge("synthesize", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# ═══════════════════════════════════════════════════
#  编排器 (外层封装，供 API 调用)
# ═══════════════════════════════════════════════════

class AgentOrchestrator:
    def __init__(self, mcp_manager: MCPToolManager):
        self.mcp_manager = mcp_manager
        self.compiled_graph = build_graph()

    async def stream_run(self, query: str, session_id: str):
        """
        异步生成器：运行 Graph 并通过 event_queue 产出 SSE 事件。
        """
        trace_id = generate_trace_id()
        event_queue: asyncio.Queue = asyncio.Queue()

        initial_state: GraphState = {
            "query": query,
            "trace_id": trace_id,
            "plan": {},
            "shared_board": {},
            "pending_tasks": [],
            "completed_tasks": [],
            "agent_outputs": {},
            "tool_calls_log": [],
            "final_answer": "",
            "iteration_count": 0,
        }

        config = {
            "configurable": {
                "thread_id": session_id,
                "event_queue": event_queue,
                "mcp_manager": self.mcp_manager,
            }
        }

        # 后台运行 graph
        async def _run_graph():
            try:
                final_state = await self.compiled_graph.ainvoke(initial_state, config)
                await event_queue.put({
                    "type": "done",
                    "content": final_state.get("final_answer", ""),
                    "trace_id": trace_id,
                    "tool_calls_log": final_state.get("tool_calls_log", []),
                    "agent_outputs": final_state.get("agent_outputs", {}),
                })
            except Exception as e:
                logger.error(f"[{trace_id}] Graph execution error: {e}", exc_info=True)
                await event_queue.put({
                    "type": "error",
                    "content": str(e),
                    "trace_id": trace_id,
                })

        task = asyncio.create_task(_run_graph())

        # 持续从 queue 中读取事件并 yield
        while True:
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.2)
                yield event
                if event.get("type") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                if task.done():
                    # drain 剩余
                    while not event_queue.empty():
                        yield await event_queue.get()
                    break
                continue

        if not task.done():
            await task
