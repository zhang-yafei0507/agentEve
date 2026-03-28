"""
MCP (Model Context Protocol) 客户端模块
支持 stdio/SSE/WebSocket 三种连接方式
"""
from typing import Dict, List, Any, Optional
import asyncio
import json

try:
    # 尝试导入官方 MCP SDK（如果已安装）
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    MCP_SDK_AVAILABLE = True
except ImportError:
    # SDK 未安装时的降级方案
    MCP_SDK_AVAILABLE = False
    print("[MCP] ⚠️ MCP SDK 未安装，使用模拟模式。请运行：pip install mcp")


class MCPClient:
    """MCP 服务器客户端"""
    
    def __init__(self, server_config: Dict):
        """
        初始化 MCP 客户端
        
        Args:
            server_config: 服务器配置
                - connection_type: stdio/sse/websocket
                - command: stdio 启动命令（如 "npx -y @modelcontextprotocol/server-filesystem"）
                - url: SSE/WebSocket 地址
                - env_vars: 环境变量
        """
        self.config = server_config
        self.connection_type = server_config.get("connection_type", "stdio")
        self.session = None
        self.tools: List[Dict] = []
        self.is_connected = False
        
    async def connect(self):
        """连接到 MCP 服务器"""
        if not MCP_SDK_AVAILABLE:
            # 模拟连接（降级方案）
            print(f"[MCP] 📡 模拟连接到 {self.config.get('name', 'unknown')}")
            await asyncio.sleep(1)  # 模拟延迟
            
            # 模拟发现工具
            self.tools = [
                {
                    "name": f"{self.config.get('name', 'mock')}_tool_1",
                    "description": f"来自 {self.config.get('name', 'mock')} 的示例工具 1",
                    "category": "MCP 工具",
                    "icon": "🛠️",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "查询参数"}
                        },
                        "required": ["query"]
                    }
                }
            ]
            self.is_connected = True
            return
        
        try:
            print(f"[MCP] 🔌 正在连接 MCP 服务器：{self.config.get('name')}")
            
            if self.connection_type == "stdio":
                # stdio 连接
                command_parts = self.config.get("command", "").split()
                if not command_parts:
                    raise ValueError("stdio 连接需要提供启动命令")
                
                params = StdioServerParameters(
                    command=command_parts[0],
                    args=command_parts[1:],
                    env=self.config.get("env_vars", {})
                )
                
                print(f"[MCP] 启动命令：{params.command} {' '.join(params.args)}")
                transport = await stdio_client(params).__aenter__()
                
            elif self.connection_type == "sse":
                # SSE 连接
                url = self.config.get("url")
                if not url:
                    raise ValueError("SSE 连接需要提供 URL")
                
                print(f"[MCP] SSE 地址：{url}")
                transport = await sse_client(url).__aenter__()
                
            elif self.connection_type == "websocket":
                # WebSocket 连接（TODO: 待实现）
                raise NotImplementedError("WebSocket 连接暂不支持")
                
            else:
                raise ValueError(f"不支持的连接类型：{self.connection_type}")
            
            # 获取读写流
            reader, writer = transport
            
            # 创建并初始化会话
            self.session = ClientSession(reader, writer)
            await self.session.initialize()
            
            # 获取工具列表
            response = await self.session.list_tools()
            self.tools = response.tools or []
            
            self.is_connected = True
            print(f"[MCP] ✅ 连接成功，发现 {len(self.tools)} 个工具")
            
        except Exception as e:
            print(f"[MCP] ❌ 连接失败：{e}")
            self.is_connected = False
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        if not self.is_connected:
            raise RuntimeError("MCP 客户端未连接")
        
        if not self.session:
            raise RuntimeError("MCP 会话未初始化")
        
        try:
            print(f"[MCP] 🔧 调用工具：{tool_name}, 参数：{arguments}")
            result = await self.session.call_tool(tool_name, arguments)
            
            # 转换结果为字典格式
            return {
                "success": True,
                "result": result.content if hasattr(result, 'content') else result,
                "tool_name": tool_name
            }
            
        except Exception as e:
            print(f"[MCP] ❌ 工具调用失败：{tool_name}, 错误：{e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }
    
    async def disconnect(self):
        """断开连接"""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
                print(f"[MCP] 🔓 已断开连接")
            except Exception as e:
                print(f"[MCP] 断开连接时出错：{e}")
        
        self.session = None
        self.is_connected = False
        self.tools = []
    
    def get_tools(self) -> List[Dict]:
        """获取工具列表"""
        return self.tools
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.config.get("name"),
            "connection_type": self.connection_type,
            "is_connected": self.is_connected,
            "tools_count": len(self.tools)
        }
