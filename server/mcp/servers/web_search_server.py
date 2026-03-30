"""
Web Search MCP Server - 将 web_search 工具封装为 MCP 服务器
"""
import sys
import asyncio
from typing import Any

# 导入真实的 web_search 工具
sys.path.insert(0, '/Users/guoczhang/PycharmProjects/agentEve3/server')
from tools.web_search import RealWebSearchTool

try:
    from mcp.server.fastmcp import FastMCP
    
    # 创建 MCP 服务器实例
    mcp = FastMCP("WebSearch")
    
    # 创建搜索工具实例
    search_tool = RealWebSearchTool(search_engine="duckduckgo")
    
    @mcp.tool()
    async def web_search(query: str, num_results: int = 5) -> list:
        """
        执行 Web 搜索
        
        Args:
            query: 搜索查询词
            num_results: 返回结果数量（默认 5）
            
        Returns:
            搜索结果列表，每项包含 title, url, snippet 字段
        """
        try:
            print(f"[WebSearch MCP] 🔍 搜索：{query}")
            results = await search_tool.search(query, num_results)
            
            # 转换为标准格式
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("snippet", ""),
                    "source": r.get("source", "Web"),
                    "timestamp": r.get("timestamp", "")
                }
                for r in results
            ]
        except Exception as e:
            print(f"[WebSearch MCP] ❌ 搜索失败：{e}")
            return [{"error": str(e)}]
    
    @mcp.tool()
    async def web_reader(url: str) -> dict:
        """
        抓取网页内容
        
        Args:
            url: 网页 URL
            
        Returns:
            包含 title, content, url 的字典
        """
        try:
            print(f"[WebSearch MCP] 📖 读取网页：{url}")
            content = await search_tool.fetch_url(url)
            return content
        except Exception as e:
            print(f"[WebSearch MCP] ❌ 读取失败：{e}")
            return {"error": str(e), "url": url}
    
    if __name__ == "__main__":
        print("[WebSearch MCP] 🚀 启动 Web Search MCP 服务器...")
        # 使用 stdio 传输
        mcp.run(transport="stdio")

except ImportError:
    print("[WebSearch MCP] ⚠️ MCP SDK 未安装，无法启动服务器")
    print("请运行：pip install mcp")
    sys.exit(1)
