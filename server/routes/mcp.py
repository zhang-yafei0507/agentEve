"""
MCP (Model Context Protocol) 集成路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import subprocess
import asyncio
from typing import Optional

from ..utils.db_init import get_db
from ..utils.database import MCPServer, Tool

router = APIRouter()


@router.get("/servers/list")
async def list_mcp_servers(db: AsyncSession = Depends(get_db)):
    """获取所有 MCP 服务器"""
    result = await db.execute(select(MCPServer))
    servers = result.scalars().all()
    
    return {
        "servers": [
            {
                "id": s.id,
                "name": s.name,
                "connection_type": s.connection_type,
                "status": s.status,
                "last_heartbeat": s.last_heartbeat.isoformat() if s.last_heartbeat else None,
                "tools_count": len(s.tools)
            }
            for s in servers
        ]
    }


@router.post("/servers/add")
async def add_mcp_server(
    name: str,
    connection_type: str,  # stdio/sse/websocket
    command: Optional[str] = None,
    url: Optional[str] = None,
    env_vars: dict = None,
    auto_enable_tools: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """添加 MCP 服务器"""
    # 验证参数
    if connection_type == "stdio" and not command:
        raise HTTPException(status_code=400, detail="stdio 连接需要提供启动命令")
    if connection_type in ["sse", "websocket"] and not url:
        raise HTTPException(status_code=400, detail="SSE/WebSocket 连接需要提供 URL")
    
    # 创建服务器记录
    mcp_server = MCPServer(
        name=name,
        connection_type=connection_type,
        command=command,
        url=url,
        env_vars=env_vars or {}
    )
    db.add(mcp_server)
    await db.commit()
    await db.refresh(mcp_server)
    
    # 尝试连接并获取工具列表
    try:
        await connect_and_discover_tools(mcp_server, db, auto_enable_tools)
    except Exception as e:
        mcp_server.status = "error"
        mcp_server.error_message = str(e)
        await db.commit()
        
        return {
            "success": False,
            "server_id": mcp_server.id,
            "error": str(e)
        }
    
    return {
        "success": True,
        "server_id": mcp_server.id,
        "tools_discovered": len(mcp_server.tools)
    }


async def connect_and_discover_tools(
    mcp_server: MCPServer, 
    db: AsyncSession,
    auto_enable: bool
):
    """连接 MCP 服务器并发现工具"""
    # MVP: 模拟连接过程
    # TODO: 实际实现需要使用 MCP SDK
    
    mcp_server.status = "connecting"
    await db.commit()
    
    # 模拟连接延迟
    await asyncio.sleep(2)
    
    # 模拟成功连接
    mcp_server.status = "connected"
    
    # 模拟发现工具
    mock_tools = [
        {
            "name": f"{mcp_server.name}_tool_1",
            "description": f"来自 {mcp_server.name} 的工具 1",
            "category": "MCP 工具",
            "icon": "🛠️"
        },
        {
            "name": f"{mcp_server.name}_tool_2",
            "description": f"来自 {mcp_server.name} 的工具 2",
            "category": "MCP 工具",
            "icon": "🔧"
        }
    ]
    
    for tool_data in mock_tools:
        tool = Tool(
            **tool_data,
            is_mcp=True,
            mcp_server_id=mcp_server.id,
            is_enabled=auto_enable
        )
        db.add(tool)
    
    await db.commit()


@router.delete("/servers/{server_id}")
async def delete_mcp_server(server_id: str, db: AsyncSession = Depends(get_db)):
    """删除 MCP 服务器"""
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    
    # 删除关联的工具
    await db.delete(server)
    await db.commit()
    
    return {"success": True}


@router.post("/servers/{server_id}/test")
async def test_mcp_server(server_id: str, db: AsyncSession = Depends(get_db)):
    """测试 MCP 服务器连接"""
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    
    # MVP: 模拟测试
    # TODO: 实际发送测试请求
    
    success = True
    error_msg = None
    
    if not success:
        server.status = "error"
        server.error_message = error_msg
    else:
        server.status = "connected"
        server.error_message = None
    
    await db.commit()
    
    return {
        "success": success,
        "status": server.status,
        "message": "连接成功" if success else error_msg
    }


@router.get("/tools/discover")
async def discover_mcp_tools(db: AsyncSession = Depends(get_db)):
    """发现所有 MCP 工具"""
    result = await db.execute(
        select(Tool).where(Tool.is_mcp == True)
    )
    tools = result.scalars().all()
    
    return {
        "tools": [
            {
                "id": tool.id,
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "icon": tool.icon,
                "is_enabled": tool.is_enabled,
                "mcp_server": tool.mcp_server.name if tool.mcp_server else None
            }
            for tool in tools
        ]
    }
