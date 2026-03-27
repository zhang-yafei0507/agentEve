"""
工具管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from ..utils.db_init import get_db
from ..utils.database import Tool, MCPServer

router = APIRouter()


@router.get("/list")
async def list_tools(
    category: Optional[str] = None,
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """获取工具列表"""
    query = select(Tool)
    
    if category:
        query = query.where(Tool.category == category)
    if enabled_only:
        query = query.where(Tool.is_enabled == True)
    
    result = await db.execute(query)
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
                "is_available": tool.is_available,
                "is_mcp": tool.is_mcp
            }
            for tool in tools
        ]
    }


@router.get("/{tool_id}")
async def get_tool(tool_id: str, db: AsyncSession = Depends(get_db)):
    """获取工具详情"""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    
    return {
        "tool": {
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "icon": tool.icon,
            "config_schema": tool.config_schema,
            "user_config": tool.user_config,
            "is_enabled": tool.is_enabled,
            "is_available": tool.is_available,
            "usage_count": tool.usage_count,
            "success_rate": tool.success_rate
        }
    }


@router.put("/{tool_id}/toggle")
async def toggle_tool(tool_id: str, db: AsyncSession = Depends(get_db)):
    """启用/禁用工具"""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    
    tool.is_enabled = not tool.is_enabled
    await db.commit()
    
    return {
        "success": True,
        "is_enabled": tool.is_enabled
    }


@router.put("/{tool_id}/config")
async def update_tool_config(
    tool_id: str,
    config: dict,
    db: AsyncSession = Depends(get_db)
):
    """更新工具配置"""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    
    tool.user_config = config
    await db.commit()
    
    return {"success": True}


@router.post("/builtin/init")
async def initialize_builtin_tools(db: AsyncSession = Depends(get_db)):
    """初始化内置工具（MVP 用）"""
    # 检查是否已存在
    result = await db.execute(select(Tool).limit(1))
    if result.scalar_one_or_none():
        return {"success": True, "message": "工具已存在"}
    
    # 添加工具
    builtin_tools = [
        {
            "name": "联网搜索",
            "description": "使用搜索引擎检索互联网信息",
            "category": "网络检索",
            "icon": "🔍",
        },
        {
            "name": "新闻检索",
            "description": "检索最新新闻资讯",
            "category": "网络检索",
            "icon": "📰",
        },
        {
            "name": "数据分析",
            "description": "进行数据对比、趋势分析等",
            "category": "数据分析",
            "icon": "📊",
        },
        {
            "name": "计算器",
            "description": "执行数学计算",
            "category": "数据分析",
            "icon": "🧮",
        },
        {
            "name": "代码解释器",
            "description": "执行 Python 代码",
            "category": "编程",
            "icon": "💻",
        },
        {
            "name": "文本摘要",
            "description": "提取文本关键信息",
            "category": "文本处理",
            "icon": "✍️",
        },
    ]
    
    for tool_data in builtin_tools:
        tool = Tool(**tool_data)
        db.add(tool)
    
    await db.commit()
    
    return {"success": True, "count": len(builtin_tools)}
