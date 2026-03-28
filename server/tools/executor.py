"""
工具调用执行器模块
支持 MCP 工具和内置工具的调用、验证、日志记录
"""
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
from datetime import datetime

try:
    # 尝试导入 jsonschema（如果已安装）
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    print("[Tools] ⚠️ jsonschema 未安装，参数验证功能受限。请运行：pip install jsonschema")

from ..utils.database import Tool, ToolCallLog
from ..mcp.client import MCPClient


class ToolExecutor:
    """工具调用执行器"""
    
    def __init__(self, db_session: AsyncSession):
        """
        初始化工具执行器
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
        self.mcp_clients: Dict[str, MCPClient] = {}  # server_id -> MCPClient
    
    async def get_or_create_client(self, server_id: str) -> MCPClient:
        """
        获取或创建 MCP 客户端
        
        Args:
            server_id: MCP 服务器 ID
            
        Returns:
            MCP 客户端实例
        """
        if server_id not in self.mcp_clients:
            # 从数据库加载服务器配置
            result = await self.db.execute(
                select(Tool).where(Tool.mcp_server_id == server_id)
            )
            tools = result.scalars().all()
            
            if not tools:
                raise ValueError(f"未找到服务器 {server_id} 的工具")
            
            # 使用第一个工具的服务器配置
            first_tool = tools[0]
            mcp_server = first_tool.mcp_server
            
            if not mcp_server:
                raise ValueError(f"工具 {first_tool.name} 未关联 MCP 服务器")
            
            # 创建客户端并连接
            client = MCPClient({
                "name": mcp_server.name,
                "connection_type": mcp_server.connection_type,
                "command": mcp_server.command,
                "url": mcp_server.url,
                "env_vars": mcp_server.env_vars
            })
            
            await client.connect()
            self.mcp_clients[server_id] = client
        
        return self.mcp_clients[server_id]
    
    async def execute_tool(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict:
        """
        执行工具调用
        
        Args:
            tool_id: 工具 ID
            arguments: 工具参数
            timeout: 超时时间（秒）
            
        Returns:
            执行结果
        """
        # 1. 获取工具信息
        result = await self.db.execute(select(Tool).where(Tool.id == tool_id))
        tool = result.scalar_one_or_none()
        
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")
        
        if not tool.is_enabled:
            raise ValueError(f"Tool {tool.name} is disabled")
        
        # 2. 参数验证（使用 JSON Schema）
        if tool.config_schema and JSONSCHEMA_AVAILABLE:
            try:
                jsonschema.validate(arguments, tool.config_schema)
            except jsonschema.ValidationError as e:
                raise ValueError(f"Invalid parameters: {e.message}")
        
        # 3. 执行调用（带超时）
        start_time = datetime.utcnow()
        try:
            if tool.is_mcp:
                # MCP 工具调用
                client = await self.get_or_create_client(tool.mcp_server_id)
                mcp_result = await asyncio.wait_for(
                    client.call_tool(tool.name, arguments),
                    timeout=timeout
                )
                
                if not mcp_result.get("success"):
                    raise RuntimeError(f"MCP 工具调用失败：{mcp_result.get('error', '未知错误')}")
                
                result_data = mcp_result.get("result")
                
            else:
                # 内置工具调用（TODO: 待实现）
                result_data = await self._call_builtin_tool(tool, arguments)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # 4. 记录日志
            log = ToolCallLog(
                tool_id=tool_id,
                session_id=None,  # 可选：传入会话 ID
                agent_id=None,  # 可选：传入智能体 ID
                params=arguments,
                result=result_data if isinstance(result_data, (dict, list)) else {"output": result_data},
                status="success",
                duration=duration
            )
            self.db.add(log)
            
            # 5. 更新统计
            tool.usage_count += 1
            # TODO: 计算成功率
            
            return {
                "success": True,
                "result": result_data,
                "duration": duration,
                "tool_name": tool.name
            }
            
        except asyncio.TimeoutError:
            # 记录超时日志
            duration = timeout
            log = ToolCallLog(
                tool_id=tool_id,
                session_id=None,
                agent_id=None,
                params=arguments,
                result=None,
                status="timeout",
                duration=duration,
                error_message=f"Timeout after {timeout}s"
            )
            self.db.add(log)
            raise
            
        except Exception as e:
            # 记录错误日志
            duration = (datetime.utcnow() - start_time).total_seconds()
            log = ToolCallLog(
                tool_id=tool_id,
                session_id=None,
                agent_id=None,
                params=arguments,
                result=None,
                status="error",
                duration=duration,
                error_message=str(e)
            )
            self.db.add(log)
            raise
    
    async def _call_builtin_tool(self, tool: Tool, arguments: Dict) -> Any:
        """
        调用内置工具（真实实现）
        
        Args:
            tool: 工具对象
            arguments: 工具参数
            
        Returns:
            执行结果
        """
        print(f"[Tools] 🛠️ 调用内置工具：{tool.name}")
        
        # 根据工具名称调用不同的真实工具
        if tool.name in ["web_search", "search_web", "network_search"]:
            # 真实 Web 搜索
            from .web_search import RealWebSearchTool
            
            query = arguments.get("query") or arguments.get("keyword", "")
            if not query:
                raise ValueError("缺少搜索关键词 'query'")
            
            search_tool = RealWebSearchTool()
            try:
                results = await search_tool.search(query, num_results=5)
                print(f"[Tools] ✅ Web 搜索成功，找到 {len(results)} 条结果")
                
                # 格式化输出
                output = f"## 网络搜索结果（共{len(results)}条）\n\n"
                for i, result in enumerate(results, 1):
                    output += f"{i}. **{result['title']}**\n"
                    output += f"   来源：{result.get('source', '未知')}\n"
                    output += f"   链接：{result['url']}\n"
                    output += f"   摘要：{result.get('snippet', '')}\n\n"
                
                return {
                    "success": True,
                    "output": output,
                    "results": results,
                    "count": len(results)
                }
            finally:
                await search_tool.close()
        
        elif tool.name in ["web_reader", "fetch_url", "read_webpage"]:
            # 真实网页抓取
            from .web_search import RealWebSearchTool
            
            url = arguments.get("url")
            if not url:
                raise ValueError("缺少 URL 参数")
            
            search_tool = RealWebSearchTool()
            try:
                content = await search_tool.fetch_url(url)
                print(f"[Tools] ✅ 网页抓取成功：{content.get('title', '无标题')}")
                
                return {
                    "success": True,
                    "output": f"网页标题：{content['title']}\n\n内容:\n{content['content']}",
                    "content": content
                }
            finally:
                await search_tool.close()
        
        else:
            # 其他工具：返回提示信息
            return {
                "message": f"工具 {tool.name} 暂未实现真实调用",
                "status": "not_implemented",
                "available_tools": ["web_search", "web_reader"]
            }
    
    async def close(self):
        """关闭所有 MCP 客户端"""
        for client in self.mcp_clients.values():
            try:
                await client.disconnect()
            except Exception as e:
                print(f"[Tools] 断开 MCP 客户端时出错：{e}")
        
        self.mcp_clients.clear()
