"""
数据库模型定义
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class Session(Base):
    """会话表"""
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    tags = Column(JSON, default=list)
    
    # 关联消息
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    # 共享状态板快照
    shared_board_snapshot = Column(JSON, default=dict)


class Message(Base):
    """消息表"""
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), index=True)
    role = Column(String)  # user/assistant
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # AI 消息特有字段
    thinking_process = Column(JSON, default=list)
    sub_agent_results = Column(JSON, default=list)
    citations = Column(JSON, default=list)
    msg_metadata = Column(JSON, default=dict)
    
    # 关联
    session = relationship("Session", back_populates="messages")


class Tool(Base):
    """工具表"""
    __tablename__ = "tools"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True)
    description = Column(Text)
    category = Column(String, index=True)  # 网络检索/数据分析/图像生成等
    icon = Column(String)
    
    # MCP 相关
    is_mcp = Column(Boolean, default=False)
    mcp_server_id = Column(String, ForeignKey("mcp_servers.id"), nullable=True)
    
    # 配置
    config_schema = Column(JSON, default=dict)
    user_config = Column(JSON, default=dict)
    
    # 状态
    is_enabled = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    last_health_check = Column(DateTime, nullable=True)
    
    # 统计
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=1.0)
    
    # 关联
    mcp_server = relationship("MCPServer", back_populates="tools")


class MCPServer(Base):
    """MCP 服务器表"""
    __tablename__ = "mcp_servers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True)
    connection_type = Column(String)  # stdio/sse/websocket
    command = Column(String, nullable=True)  # stdio 启动命令
    url = Column(String, nullable=True)  # SSE/WebSocket 地址
    env_vars = Column(JSON, default=dict)
    
    # 状态
    status = Column(String, default="disconnected")  # disconnected/connecting/connected/error
    error_message = Column(Text, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    tools = relationship("Tool", back_populates="mcp_server", cascade="all, delete-orphan")


class ToolCallLog(Base):
    """工具调用日志表"""
    __tablename__ = "tool_call_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tool_id = Column(String, ForeignKey("tools.id"), index=True)
    session_id = Column(String, ForeignKey("sessions.id"), index=True)
    agent_id = Column(String)
    
    # 调用信息
    params = Column(JSON, default=dict)
    result = Column(JSON, nullable=True)
    status = Column(String)  # success/error/timeout
    duration = Column(Float)  # 耗时 (秒)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)
