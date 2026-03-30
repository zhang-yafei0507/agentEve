"""
MCP 工具管理器 - 统一管理所有 MCP 服务器和工具
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

from .client import MCPClient


class ToolMetadata:
    """工具元数据"""
    
    def __init__(self, tool_info: Dict, server_name: str):
        self.name = tool_info.get("name", "unknown")
        self.description = tool_info.get("description", "")
        self.category = tool_info.get("category", "General")
        self.icon = tool_info.get("icon", "🔧")
        self.input_schema = tool_info.get("inputSchema", {})
        self.server_name = server_name
        self.created_at = datetime.utcnow()
        
        # 统计数据
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_duration = 0.0
    
    def to_dict(self) -> Dict:
        success_rate = (
            self.successful_calls / self.total_calls 
            if self.total_calls > 0 else 0.0
        )
        avg_duration = (
            self.total_duration / self.total_calls
            if self.total_calls > 0 else 0.0
        )
        
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "inputSchema": self.input_schema,
            "server_name": self.server_name,
            "stats": {
                "total_calls": self.total_calls,
                "success_rate": success_rate,
                "avg_duration": avg_duration
            }
        }


class MCPToolManager:
    """
    MCP 工具管理器
    
    核心职责：
    1. 管理多个 MCP 服务器连接
    2. 自动发现和注册工具
    3. 统一工具调用接口
    4. 统计工具使用情况
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPClient] = {}
        self.tools: Dict[str, ToolMetadata] = {}
        self.is_initialized = False
    
    async def register_server(self, name: str, config: Dict) -> bool:
        """
        注册 MCP 服务器
        
        Args:
            name: 服务器名称
            config: 服务器配置（connection_type, command/url, env_vars 等）
            
        Returns:
            bool: 是否成功注册
        """
        try:
            print(f"[ToolManager] 📡 正在注册 MCP 服务器：{name}")
            
            # 创建客户端
            client = MCPClient({
                **config,
                "name": name
            })
            
            # 连接到服务器
            await client.connect()
            
            if not client.is_connected:
                raise Exception("连接失败")
            
            # 获取工具列表
            tools = client.get_tools()
            print(f"[ToolManager] ✅ 服务器 {name} 提供 {len(tools)} 个工具")
            
            # 注册工具
            for tool_info in tools:
                tool_name = tool_info.get("name")
                if tool_name:
                    metadata = ToolMetadata(tool_info, name)
                    self.tools[tool_name] = metadata
                    print(f"  - 注册工具：{tool_name}")
            
            # 保存服务器引用
            self.servers[name] = client
            self.is_initialized = len(self.tools) > 0
            
            return True
            
        except Exception as e:
            print(f"[ToolManager] ❌ 注册服务器失败：{name}, 错误：{e}")
            return False
    
    async def list_tools(self) -> List[Dict]:
        """获取所有可用工具"""
        return [metadata.to_dict() for metadata in self.tools.values()]
    
    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            args: 工具参数
            
        Returns:
            工具执行结果
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"未知工具：{tool_name}",
                "tool_name": tool_name
            }
        
        metadata = self.tools[tool_name]
        server_name = metadata.server_name
        
        if server_name not in self.servers:
            return {
                "success": False,
                "error": f"服务器未连接：{server_name}",
                "tool_name": tool_name
            }
        
        client = self.servers[server_name]
        start_time = datetime.utcnow()
        
        try:
            print(f"[ToolManager] 🔧 调用工具：{tool_name}, 参数：{args}")
            
            # 调用工具（带超时）
            result = await asyncio.wait_for(
                client.call_tool(tool_name, args),
                timeout=60.0
            )
            
            # 更新统计
            duration = (datetime.utcnow() - start_time).total_seconds()
            metadata.total_calls += 1
            metadata.total_duration += duration
            
            if result.get("success", False):
                metadata.successful_calls += 1
            else:
                metadata.failed_calls += 1
            
            return result
            
        except asyncio.TimeoutError:
            print(f"[ToolManager] ⏰ 工具调用超时：{tool_name}")
            metadata.total_calls += 1
            metadata.failed_calls += 1
            
            return {
                "success": False,
                "error": f"工具调用超时（超过 60 秒）",
                "tool_name": tool_name
            }
            
        except Exception as e:
            print(f"[ToolManager] ❌ 工具调用失败：{tool_name}, 错误：{e}")
            metadata.total_calls += 1
            metadata.failed_calls += 1
            
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }
    
    def get_tool_stats(self) -> Dict[str, Dict]:
        """获取所有工具统计信息"""
        return {
            name: metadata.to_dict()["stats"]
            for name, metadata in self.tools.items()
        }
    
    async def discover_new_tools(self) -> Dict[str, List[str]]:
        """
        发现新工具（重新扫描所有服务器）
        
        Returns:
            {"new_tools": [...], "updated_tools": [...]}
        """
        new_tools = []
        updated_tools = []
        
        for server_name, client in self.servers.items():
            try:
                # 重新获取工具列表
                await client.connect()
                current_tools = client.get_tools()
                
                for tool_info in current_tools:
                    tool_name = tool_info.get("name")
                    if not tool_name:
                        continue
                    
                    if tool_name not in self.tools:
                        # 新工具
                        metadata = ToolMetadata(tool_info, server_name)
                        self.tools[tool_name] = metadata
                        new_tools.append(tool_name)
                        print(f"[ToolManager] ✨ 发现新工具：{tool_name}")
                    else:
                        # 已存在，可能更新了
                        old_metadata = self.tools[tool_name]
                        if old_metadata.description != tool_info.get("description"):
                            updated_tools.append(tool_name)
                            print(f"[ToolManager] 🔄 工具更新：{tool_name}")
                            
            except Exception as e:
                print(f"[ToolManager] 扫描服务器失败：{server_name}, 错误：{e}")
        
        return {
            "new_tools": new_tools,
            "updated_tools": updated_tools
        }
    
    async def cleanup(self):
        """清理资源（断开所有连接）"""
        print("[ToolManager] 🧹 正在清理资源...")
        
        for client in self.servers.values():
            try:
                await client.disconnect()
            except Exception as e:
                print(f"[ToolManager] 断开连接时出错：{e}")
        
        self.servers.clear()
        self.tools.clear()
        self.is_initialized = False
        
        print("[ToolManager] ✅ 资源清理完成")
