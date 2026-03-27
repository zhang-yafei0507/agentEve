"""
会话管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime
from typing import Optional

from ..utils.db_init import get_db
from ..utils.database import Session as DBSession, Message

router = APIRouter()


@router.get("/list")
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """获取会话列表"""
    result = await db.execute(
        select(DBSession)
        .where(DBSession.deleted_at.is_(None))
        .order_by(DBSession.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    sessions = result.scalars().all()
    
    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "tags": s.tags or []
            }
            for s in sessions
        ],
        "total": len(sessions)
    }


@router.get("/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """获取会话详情"""
    result = await db.execute(
        select(DBSession).where(DBSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session or session.deleted_at:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {
        "session": {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "tags": session.tags or [],
            "shared_board_snapshot": session.shared_board_snapshot
        }
    }


@router.put("/{session_id}/rename")
async def rename_session(
    session_id: str,
    title: str,
    db: AsyncSession = Depends(get_db)
):
    """重命名会话"""
    result = await db.execute(
        select(DBSession).where(DBSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session or session.deleted_at:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    session.title = title
    session.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"success": True}


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    soft_delete: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """删除会话"""
    result = await db.execute(
        select(DBSession).where(DBSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    if soft_delete:
        # 软删除
        session.deleted_at = datetime.utcnow()
    else:
        # 硬删除
        await db.delete(session)
    
    await db.commit()
    
    return {"success": True}


@router.post("/create")
async def create_session(
    title: Optional[str] = None,
    tags: list = None,
    db: AsyncSession = Depends(get_db)
):
    """创建新会话"""
    session = DBSession(
        title=title or "新对话",
        tags=tags or []
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    return {
        "session": {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat()
        }
    }


@router.get("/{session_id}/export")
async def export_session(
    session_id: str,
    format: str = "markdown",  # markdown/json
    db: AsyncSession = Depends(get_db)
):
    """导出会话"""
    # 获取会话
    result = await db.execute(
        select(DBSession).where(DBSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session or session.deleted_at:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 获取消息
    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.timestamp)
    )
    messages = msg_result.scalars().all()
    
    if format == "json":
        return {
            "session_id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ]
        }
    
    elif format == "markdown":
        md_content = f"# {session.title}\n\n"
        md_content += f"**创建时间**: {session.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        md_content += "---\n\n"
        
        for msg in messages:
            role_name = "用户" if msg.role == "user" else "AI"
            md_content += f"## {role_name} ({msg.timestamp.strftime('%H:%M')})\n\n"
            md_content += f"{msg.content}\n\n"
            
            if msg.role == "assistant" and msg.thinking_process:
                md_content += "**思考过程**:\n"
                for thought in msg.thinking_process:
                    md_content += f"- {thought.get('agent', 'AI')}: {thought.get('action', '')}\n"
                md_content += "\n"
            
            md_content += "---\n\n"
        
        return {
            "content": md_content,
            "filename": f"{session.title}.md"
        }
    
    else:
        raise HTTPException(status_code=400, detail="不支持的导出格式")
