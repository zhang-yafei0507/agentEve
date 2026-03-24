from pydantic import BaseModel
from typing import Optional


# ── Chat ────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    query: str


# ── MCP Server ──────────────────────────────────
class MCPServerCreate(BaseModel):
    name: str
    transport: str = "stdio"
    command: Optional[str] = None
    args: list[str] = []
    env_vars: dict[str, str] = {}
    url: Optional[str] = None


class ToolToggle(BaseModel):
    tool_name: str
    enabled: bool
