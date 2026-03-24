"""全局配置 — 从 .env 读取"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── LLM ─────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o"

    # ── 数据库 ──────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./agentic_rag.db"

    # ── 智能体 ──────────────────────────────────────
    MAX_WORKERS: int = 4
    AGENT_TIMEOUT: int = 120          # 单个智能体超时 (秒)
    MAX_TOOL_ITERATIONS: int = 6      # 单个 Agent ReAct 循环上限
    MAX_GRAPH_ITERATIONS: int = 20    # 图全局循环上限

    # ── CORS ────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()
