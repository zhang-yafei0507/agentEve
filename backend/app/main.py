"""
FastAPI 主入口：SSE 流式聊天、MCP 工具管理、会话 CRUD。
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import init_db, get_db, async_session
from app.models import MCPServerConfig, ToolPermission, ChatSession, ChatMessage, gen_id
from app.schemas import ChatRequest, MCPServerCreate, ToolToggle
from app.mcp.mcp_manager import MCPToolManager
from app.agents.langgraph_agent import AgentOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s  %(message)s")
logger = logging.getLogger("main")


# ═══════════════════════════════════════════════════
#  Lifespan
# ═══════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    await init_db()

    mcp_manager = MCPToolManager()
    await mcp_manager.initialize()

    # 从 DB 加载已配置的 MCP Server
    async with async_session() as db:
        configs = (await db.execute(select(MCPServerConfig).where(MCPServerConfig.enabled == True))).scalars().all()
        for cfg in configs:
            try:
                await mcp_manager.add_server(cfg.name, {
                    "transport": cfg.transport,
                    "command": cfg.command,
                    "args": cfg.args or [],
                    "env_vars": cfg.env_vars or {},
                    "url": cfg.url,
                })
            except Exception as e:
                logger.warning(f"Could not auto-connect MCP server '{cfg.name}': {e}")

        # 加载工具权限
        perms = (await db.execute(select(ToolPermission))).scalars().all()
        for p in perms:
            if not p.enabled:
                mcp_manager.disable_tool(p.tool_name)

    app.state.mcp_manager = mcp_manager
    app.state.orchestrator = AgentOrchestrator(mcp_manager)

    logger.info("🚀 Agentic RAG System started")
    yield

    # ── Shutdown ──
    await mcp_manager.shutdown()
    logger.info("System shutdown complete")


app = FastAPI(title="Agentic RAG Multi-Agent System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════
#  Chat API — SSE 流式
# ═══════════════════════════════════════════════════

@app.post("/api/chat")
async def chat_stream(req: ChatRequest):
    orchestrator: AgentOrchestrator = app.state.orchestrator

    # 创建或获取 session
    session_id = req.session_id or gen_id()

    async with async_session() as db:
        existing = await db.get(ChatSession, session_id)
        if not existing:
            db.add(ChatSession(id=session_id, title=req.query[:50]))
            await db.commit()
        # 存用户消息
        db.add(ChatMessage(session_id=session_id, role="user", content=req.query))
        await db.commit()

    async def event_generator():
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        final_content = ""
        async for event in orchestrator.stream_run(req.query, session_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            if event.get("type") == "done":
                final_content = event.get("content", "")
            elif event.get("type") == "error":
                final_content = f"Error: {event.get('content', 'Unknown')}"

        # 存 assistant 消息
        if final_content:
            async with async_session() as db:
                db.add(ChatMessage(session_id=session_id, role="assistant", content=final_content))
                await db.commit()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ═══════════════════════════════════════════════════
#  Tool / MCP Server 管理 API
# ═══════════════════════════════════════════════════

@app.get("/api/tools/list")
async def list_tools():
    mgr: MCPToolManager = app.state.mcp_manager
    tools = mgr.get_all_tools()
    return [
        {
            "name": t.name,
            "description": t.description,
            "source": t.source,
            "server_name": t.server_name,
            "enabled": t.enabled,
        }
        for t in tools
    ]


@app.post("/api/tools/configure")
async def configure_mcp_server(req: MCPServerCreate):
    mgr: MCPToolManager = app.state.mcp_manager
    try:
        registered = await mgr.add_server(req.name, {
            "transport": req.transport,
            "command": req.command,
            "args": req.args,
            "env_vars": req.env_vars,
            "url": req.url,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 持久化到 DB
    async with async_session() as db:
        existing = (await db.execute(
            select(MCPServerConfig).where(MCPServerConfig.name == req.name)
        )).scalar_one_or_none()
        if existing:
            existing.transport = req.transport
            existing.command = req.command
            existing.args = req.args
            existing.env_vars = req.env_vars
            existing.url = req.url
            existing.enabled = True
        else:
            db.add(MCPServerConfig(
                name=req.name, transport=req.transport,
                command=req.command, args=req.args,
                env_vars=req.env_vars, url=req.url,
            ))
        # 同时持久化工具权限
        for t in registered:
            perm = (await db.execute(
                select(ToolPermission).where(ToolPermission.tool_name == t.name)
            )).scalar_one_or_none()
            if not perm:
                db.add(ToolPermission(tool_name=t.name, server_name=req.name, enabled=True, source="mcp"))
        await db.commit()

    return {"status": "ok", "tools_registered": len(registered)}


@app.put("/api/tools/toggle")
async def toggle_tool(req: ToolToggle):
    mgr: MCPToolManager = app.state.mcp_manager
    if req.enabled:
        mgr.enable_tool(req.tool_name)
    else:
        mgr.disable_tool(req.tool_name)

    async with async_session() as db:
        perm = (await db.execute(
            select(ToolPermission).where(ToolPermission.tool_name == req.tool_name)
        )).scalar_one_or_none()
        if perm:
            perm.enabled = req.enabled
            await db.commit()

    return {"status": "ok", "tool": req.tool_name, "enabled": req.enabled}


@app.post("/api/tools/test")
async def test_mcp_connection(req: MCPServerCreate):
    mgr: MCPToolManager = app.state.mcp_manager
    result = await mgr.test_connection({
        "transport": req.transport,
        "command": req.command,
        "args": req.args,
        "env_vars": req.env_vars,
        "url": req.url,
    })
    return result


@app.delete("/api/tools/server/{name}")
async def remove_mcp_server(name: str):
    mgr: MCPToolManager = app.state.mcp_manager
    await mgr.remove_server(name)
    async with async_session() as db:
        cfg = (await db.execute(
            select(MCPServerConfig).where(MCPServerConfig.name == name)
        )).scalar_one_or_none()
        if cfg:
            cfg.enabled = False
            await db.commit()
    return {"status": "ok"}


# ═══════════════════════════════════════════════════
#  Session API
# ═══════════════════════════════════════════════════

@app.get("/api/sessions")
async def list_sessions():
    async with async_session() as db:
        rows = (await db.execute(
            select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(50)
        )).scalars().all()
        return [{"id": r.id, "title": r.title, "created_at": r.created_at.isoformat()} for r in rows]


@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    async with async_session() as db:
        rows = (await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
        )).scalars().all()
        return [{"role": r.role, "content": r.content, "created_at": r.created_at.isoformat()} for r in rows]


# ═══════════════════════════════════════════════════
#  Health
# ═══════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    mgr: MCPToolManager = app.state.mcp_manager
    return {
        "status": "ok",
        "connected_servers": list(mgr.connections.keys()),
        "total_tools": len(mgr.tool_registry),
    }
