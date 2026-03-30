"""
工具调用基类 - 定义真实工具的执行逻辑
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator
import json


class BaseTool(ABC):
    """工具基类"""
    
    name: str = "base_tool"
    description: str = "基础工具"
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具调用"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """返回工具参数 Schema"""
        pass


class WebSearchTool(BaseTool):
    """网络搜索工具"""
    
    name = "web_search"
    description = "从互联网搜索最新信息"
    
    async def execute(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        真实的网络搜索
        
        TODO: 对接真实的搜索 API（如 Google Custom Search、Bing Search）
        """
        # 示例：使用 SerpAPI 或其他搜索服务
        try:
            # from serpapi import GoogleSearch  # 示例
            # client = GoogleSearch({"q": query, "api_key": "..."})
            # results = client.get_dict()
            
            # 临时实现：返回模拟数据（需替换为真实 API）
            return {
                "success": True,
                "query": query,
                "results": [
                    {
                        "title": f"搜索结果 {i+1} for '{query}'",
                        "url": f"https://example.com/result-{i}",
                        "snippet": f"这是关于'{query}'的搜索结果片段...",
                        "source": "Example Source"
                    }
                    for i in range(min(num_results, 5))
                ],
                "search_metadata": {
                    "total_results": "约 1,000,000 个结果",
                    "time_taken": 0.5
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询词"
                },
                "num_results": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 5
                }
            },
            "required": ["query"]
        }


class CalculatorTool(BaseTool):
    """计算器工具"""
    
    name = "calculator"
    description = "执行数学计算"
    
    async def execute(self, expression: str) -> Dict[str, Any]:
        """
        真实的数学计算
        
        TODO: 对接安全的表达式求值器（禁止 eval）
        """
        try:
            # 安全做法：使用 ast 或 numexpr
            import ast
            import operator
            
            # 定义允许的操作符
            operators = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }
            
            def eval_expr(node):
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    left = eval_expr(node.left)
                    right = eval_expr(node.right)
                    return operators[type(node.op)](left, right)
                elif isinstance(node, ast.UnaryOp):
                    operand = eval_expr(node.operand)
                    return operators[type(node.op)](operand)
                else:
                    raise ValueError("不支持的操作")
            
            tree = ast.parse(expression, mode='eval')
            result = eval_expr(tree.body)
            
            return {
                "success": True,
                "expression": expression,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "expression": expression
            }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '2 + 2 * 3'"
                }
            },
            "required": ["expression"]
        }


# 工具注册表
TOOL_REGISTRY = {
    "web_search": WebSearchTool,
    "calculator": CalculatorTool,
}


def get_tool(tool_name: str) -> Optional[BaseTool]:
    """获取工具实例"""
    tool_class = TOOL_REGISTRY.get(tool_name)
    if tool_class:
        return tool_class()
    return None


def list_available_tools() -> list:
    """列出所有可用工具"""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "schema": tool().get_schema()
        }
        for tool in TOOL_REGISTRY.values()
    ]
