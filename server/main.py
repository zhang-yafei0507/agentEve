"""
Agentic RAG 多智能体协作系统 - 后端服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.routes import chat, tools, sessions, mcp
from server.utils.db_init import init_db

app = FastAPI(
    title="Agent Eve - Agentic RAG System",
    description="多智能体协作平台",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
@app.on_event("startup")
async def startup_event():
    await init_db()
    print("🚀 Agent Eve 服务启动成功!")

# 路由注册
app.include_router(chat.router, prefix="/api/chat", tags=["聊天"])
app.include_router(tools.router, prefix="/api/tools", tags=["工具"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["会话"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["MCP"])

@app.get("/")
async def root():
    return {
        "message": "欢迎使用 Agent Eve - Agentic RAG 多智能体协作系统",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
