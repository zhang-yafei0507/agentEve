"""SQLAlchemy ORM 模型"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, JSON, ForeignKey
from app.database import Base


def gen_id() -> str:
    return uuid.uuid4().hex[:16]


class MCPServerConfig(Base):
    __tablename__ = "mcp_server_configs"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, unique=True, nullable=False)
    transport = Column(String, default="stdio")          # stdio | sse
    command = Column(String, nullable=True)
    args = Column(JSON, default=list)
    env_vars = Column(JSON, default=dict)
    url = Column(String, nullable=True)                  # SSE transport 使用
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ToolPermission(Base):
    __tablename__ = "tool_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_name = Column(String, nullable=False, unique=True)
    server_name = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
    source = Column(String, default="mcp")              # mcp | local


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
