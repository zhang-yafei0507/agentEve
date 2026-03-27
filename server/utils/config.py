"""
配置管理模块
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./agent_eve.db"
    
    # LLM 配置
    LLM_PROVIDER: str = "local"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "Qwen"
    LLM_BASE_URL: str = "http://192.168.83.238:49869/v1"
    
    # MCP 配置
    MCP_TIMEOUT: int = 30
    MAX_SUB_AGENTS: int = 4
    
    # CORS 配置
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
