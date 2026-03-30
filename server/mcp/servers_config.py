"""
MCP 服务器配置管理
统一管理所有 MCP 服务器的注册和配置
"""
from typing import Dict, List, Any


# MCP 服务器配置文件
MCP_SERVERS_CONFIG: Dict[str, Dict[str, Any]] = {
    # Web Search MCP 服务器（本地 stdio）
    "web_search": {
        "name": "WebSearch",
        "description": "Web 搜索引擎，用于实时信息查询",
        "connection_type": "stdio",
        "command": "python",  # 将被替换为 sys.executable
        "args": ["-m", "server.mcp.servers.web_search_server"],
        "env_vars": {},  # 可选的环境变量
        "enabled": True,
        "timeout": 30,
        "category": "搜索"
    },
    
    # 示例：文件操作 MCP 服务器（未来扩展）
    "file_system": {
        "name": "FileSystem",
        "description": "文件系统操作工具",
        "connection_type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        "env_vars": {},
        "enabled": False,  # 默认禁用
        "timeout": 60,
        "category": "工具"
    },
    
    # 示例：数据库 MCP 服务器（未来扩展）
    "database": {
        "name": "Database",
        "description": "数据库查询工具",
        "connection_type": "stdio",
        "command": "python",
        "args": ["-m", "server.mcp.servers.database_server"],
        "env_vars": {},
        "enabled": False,
        "timeout": 60,
        "category": "数据"
    }
}


async def get_enabled_servers() -> List[Dict[str, Any]]:
    """获取所有启用的 MCP 服务器配置"""
    enabled = []
    for name, config in MCP_SERVERS_CONFIG.items():
        if config.get("enabled", False):
            # 添加名称到配置中
            config["name"] = name
            enabled.append(config)
    return enabled


async def get_server_config(server_name: str) -> Dict[str, Any]:
    """获取指定 MCP 服务器的配置"""
    return MCP_SERVERS_CONFIG.get(server_name)


async def enable_server(server_name: str) -> bool:
    """启用指定的 MCP 服务器"""
    if server_name in MCP_SERVERS_CONFIG:
        MCP_SERVERS_CONFIG[server_name]["enabled"] = True
        return True
    return False


async def disable_server(server_name: str) -> bool:
    """禁用指定的 MCP 服务器"""
    if server_name in MCP_SERVERS_CONFIG:
        MCP_SERVERS_CONFIG[server_name]["enabled"] = False
        return True
    return False


# 便捷函数：获取所有可用工具的分类
async def get_tool_categories() -> List[str]:
    """获取所有 MCP 服务器的分类"""
    categories = set()
    for config in MCP_SERVERS_CONFIG.values():
        if config.get("enabled"):
            categories.add(config.get("category", "其他"))
    return list(categories)
