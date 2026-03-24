"""
MCPToolManager: 统一管理 MCP Server 连接、工具注册、权限校验与路由调用。
"""

import asyncio
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any, Optional

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from app.agents.tools import LOCAL_TOOLS_REGISTRY

logger = logging.getLogger("mcp_manager")


# ─── 数据类 ────────────────────────────────────────

@dataclass
class ToolInfo:
    name: str
    description: str
    parameters: dict
    server_name: str
    source: str = "mcp"          # mcp | local
    enabled: bool = True


@dataclass
class MCPConnection:
    name: str
    config: dict
    session: Optional[ClientSession] = None
    _exit_stack: AsyncExitStack = field(default_factory=AsyncExitStack)
    connected: bool = False

    async def connect(self):
        try:
            transport = self.config.get("transport", "stdio")
            if transport == "stdio":
                params = StdioServerParameters(
                    command=self.config["command"],
                    args=self.config.get("args", []),
                    env=self.config.get("env_vars") or None,
                )
                read_stream, write_stream = await self._exit_stack.enter_async_context(
                    stdio_client(params)
                )
            else:
                # SSE transport
                from mcp.client.sse import sse_client
                read_stream, write_stream = await self._exit_stack.enter_async_context(
                    sse_client(self.config["url"])
                )

            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self.session.initialize()
            self.connected = True
            logger.info(f"MCP server '{self.name}' connected")
        except Exception as e:
            logger.error(f"Failed to connect MCP server '{self.name}': {e}")
            raise

    async def disconnect(self):
        try:
            await self._exit_stack.aclose()
        except Exception:
            pass
        self.connected = False

    async def list_tools(self) -> list:
        if not self.session:
            return []
        result = await self.session.list_tools()
        return result.tools

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        if not self.session:
            raise RuntimeError(f"Server '{self.name}' not connected")
        result = await self.session.call_tool(tool_name, arguments=arguments)
        # 将 content 列表拼接为字符串
        texts = []
        for item in result.content:
            if hasattr(item, "text"):
                texts.append(item.text)
            else:
                texts.append(str(item))
        return "\n".join(texts)


# ─── 管理器单例 ─────────────────────────────────────

class MCPToolManager:
    def __init__(self):
        self.connections: dict[str, MCPConnection] = {}
        self.tool_registry: dict[str, ToolInfo] = {}
        self._disabled_tools: set[str] = set()
        self._lock = asyncio.Lock()

    # ── 初始化 / 关闭 ────────────────────────────

    async def initialize(self):
        """启动时加载本地工具"""
        for name, meta in LOCAL_TOOLS_REGISTRY.items():
            self.tool_registry[name] = ToolInfo(
                name=name,
                description=meta["description"],
                parameters=meta["parameters"],
                server_name="__local__",
                source="local",
                enabled=True,
            )
        logger.info(f"Loaded {len(LOCAL_TOOLS_REGISTRY)} local tools")

    async def shutdown(self):
        for conn in self.connections.values():
            await conn.disconnect()
        self.connections.clear()
        logger.info("MCPToolManager shutdown complete")

    # ── MCP Server 管理 ──────────────────────────

    async def add_server(self, name: str, config: dict) -> list[ToolInfo]:
        async with self._lock:
            if name in self.connections:
                await self.connections[name].disconnect()

            conn = MCPConnection(name=name, config=config)
            await conn.connect()
            self.connections[name] = conn

            # 注册工具
            remote_tools = await conn.list_tools()
            registered = []
            for t in remote_tools:
                info = ToolInfo(
                    name=t.name,
                    description=t.description or "",
                    parameters=t.inputSchema if t.inputSchema else {"type": "object", "properties": {}},
                    server_name=name,
                    source="mcp",
                )
                self.tool_registry[t.name] = info
                registered.append(info)

            logger.info(f"Registered {len(registered)} tools from server '{name}'")
            return registered

    async def remove_server(self, name: str):
        async with self._lock:
            if name in self.connections:
                await self.connections[name].disconnect()
                del self.connections[name]
                # 移除关联工具
                to_remove = [k for k, v in self.tool_registry.items() if v.server_name == name]
                for k in to_remove:
                    del self.tool_registry[k]

    async def test_connection(self, config: dict) -> dict:
        """测试 MCP Server 连接，返回工具数量"""
        conn = MCPConnection(name="__test__", config=config)
        try:
            await conn.connect()
            tools = await conn.list_tools()
            await conn.disconnect()
            return {"success": True, "tool_count": len(tools)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── 工具权限 ─────────────────────────────────

    def disable_tool(self, tool_name: str):
        self._disabled_tools.add(tool_name)
        if tool_name in self.tool_registry:
            self.tool_registry[tool_name].enabled = False

    def enable_tool(self, tool_name: str):
        self._disabled_tools.discard(tool_name)
        if tool_name in self.tool_registry:
            self.tool_registry[tool_name].enabled = True

    def is_tool_enabled(self, tool_name: str) -> bool:
        return tool_name not in self._disabled_tools

    # ── 获取工具列表 ─────────────────────────────

    def get_all_tools(self) -> list[ToolInfo]:
        return list(self.tool_registry.values())

    def get_enabled_tool_schemas(self) -> list[dict]:
        """返回 OpenAI function-calling 格式的工具 schema (仅启用的)"""
        schemas = []
        for t in self.tool_registry.values():
            if not t.enabled:
                continue
            schemas.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            })
        return schemas

    # ── 统一工具调用 ─────────────────────────────

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict,
        agent_id: str = "",
        trace_id: str = "",
    ) -> str:
        # 权限拦截
        if not self.is_tool_enabled(tool_name):
            raise PermissionError(
                f"[{trace_id}] Tool '{tool_name}' is disabled — agent '{agent_id}' call rejected"
            )

        info = self.tool_registry.get(tool_name)
        if not info:
            raise ValueError(f"[{trace_id}] Tool '{tool_name}' not found")

        logger.info(f"[{trace_id}] Agent '{agent_id}' calling tool '{tool_name}' | args={arguments}")

        if info.source == "local":
            func = LOCAL_TOOLS_REGISTRY[tool_name]["func"]
            return await func(**arguments)
        else:
            conn = self.connections.get(info.server_name)
            if not conn or not conn.connected:
                raise RuntimeError(f"MCP server '{info.server_name}' not connected")
            return await conn.call_tool(tool_name, arguments)
