"""本地内置工具"""

import math
from datetime import datetime


LOCAL_TOOLS_REGISTRY: dict[str, dict] = {}


def register_local_tool(name: str, description: str, parameters: dict):
    """装饰器：注册本地工具"""
    def decorator(func):
        LOCAL_TOOLS_REGISTRY[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "func": func,
        }
        return func
    return decorator


@register_local_tool(
    name="calculator",
    description="Evaluate a mathematical expression. E.g. '2+3*4'",
    parameters={
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "Math expression to evaluate"}
        },
        "required": ["expression"],
    },
)
async def calculator(expression: str) -> str:
    try:
        allowed = set("0123456789+-*/().% ")
        if not all(c in allowed for c in expression):
            return f"Error: expression contains disallowed characters"
        result = eval(expression, {"__builtins__": {}}, {"math": math})
        return str(result)
    except Exception as e:
        return f"Calculation error: {e}"


@register_local_tool(
    name="get_current_time",
    description="Get the current date and time in ISO format",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def get_current_time() -> str:
    return datetime.now().isoformat()


@register_local_tool(
    name="text_length",
    description="Count words and characters in a text",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to analyze"}
        },
        "required": ["text"],
    },
)
async def text_length(text: str) -> str:
    words = len(text.split())
    chars = len(text)
    return f"Words: {words}, Characters: {chars}"
