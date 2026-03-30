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
        
    async def connect(self, max_retries: int = 3, timeout: int = 30):
        """连接到 MCP 服务器（增强版：带重试和超时）"""
        if not MCP_SDK_AVAILABLE:
            # 模拟连接（降级方案）
            print(f"[MCP] 📡 模拟连接到 {self.config.get('name', 'unknown')}")
            await asyncio.sleep(0.5)  # 模拟延迟
            
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
        
        # 重试机制
        last_error = None
        for attempt in range(max_retries):
            try:
                print(f"[MCP] 🔌 正在连接 MCP 服务器：{self.config.get('name')} (尝试 {attempt + 1}/{max_retries})")
                
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
                    transport = await asyncio.wait_for(
                        stdio_client(params).__aenter__(),
                        timeout=timeout
                    )
                    
                elif self.connection_type == "sse":
                    # SSE 连接
                    url = self.config.get("url")
                    if not url:
                        raise ValueError("SSE 连接需要提供 URL")
                    
                    print(f"[MCP] SSE 地址：{url}")
                    transport = await asyncio.wait_for(
                        sse_client(url).__aenter__(),
                        timeout=timeout
                    )
                    
                elif self.connection_type == "websocket":
                    # WebSocket 连接（TODO: 待实现）
                    raise NotImplementedError("WebSocket 连接暂不支持")
                    
                else:
                    raise ValueError(f"不支持的连接类型：{self.connection_type}")
                
                # 获取读写流
                reader, writer = transport
                
                # 创建并初始化会话
                self.session = ClientSession(reader, writer)
                await asyncio.wait_for(
                    self.session.initialize(),
                    timeout=timeout
                )
                
                # 获取工具列表
                response = await self.session.list_tools()
                self.tools = response.tools or []
                
                self.is_connected = True
                print(f"[MCP] ✅ 连接成功，发现 {len(self.tools)} 个工具")
                return  # 成功则退出
                
            except asyncio.TimeoutError as e:
                last_error = e
                print(f"[MCP] ⏰ 连接超时（{timeout}秒），准备重试...")
                
            except Exception as e:
                last_error = e
                print(f"[MCP] ❌ 连接失败：{e}")
                
            # 指数退避
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 1.0  # 1s, 2s, 4s
                print(f"[MCP] 等待 {wait_time:.1f}秒后重试...")
                await asyncio.sleep(wait_time)
        
        # 所有重试失败
        print(f"[MCP] ❌ 所有连接尝试失败，共{max_retries}次")
        self.is_connected = False
        if last_error:
            raise last_error
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: int = 60) -> Dict:
        """
        调用 MCP 工具（增强版：带超时和错误分类）
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            timeout: 执行超时（秒）
            
        Returns:
            工具执行结果
        """
        if not self.is_connected:
            raise RuntimeError("MCP 客户端未连接")
        
        if not self.session:
            raise RuntimeError("MCP 会话未初始化")
        
        try:
            print(f"[MCP] 🔧 调用工具：{tool_name}, 参数：{arguments}")
            
            # 参数校验
            if tool_name not in [t.get("name") for t in self.tools]:
                return {
                    "success": False,
                    "error": f"未知工具：{tool_name}",
                    "error_type": "invalid_tool"
                }
            
            # 调用工具（带超时）
            result = await asyncio.wait_for(
                self.session.call_tool(tool_name, arguments),
                timeout=timeout
            )
            
            # 转换结果为字典格式
            return {
                "success": True,
                "result": result.content if hasattr(result, 'content') else result,
                "tool_name": tool_name,
                "error_type": None
            }
            
        except asyncio.TimeoutError:
            print(f"[MCP] ⏰ 工具调用超时：{tool_name} (超过{timeout}秒)")
            return {
                "success": False,
                "error": f"工具调用超时（超过{timeout}秒）",
                "tool_name": tool_name,
                "error_type": "timeout"
            }
            
        except Exception as e:
            error_type = "network_error" if "connection" in str(e).lower() else "api_error"
            print(f"[MCP] ❌ 工具调用失败：{tool_name}, 错误：{e}, 类型：{error_type}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name,
                "error_type": error_type
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
