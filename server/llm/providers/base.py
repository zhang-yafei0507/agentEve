"""
LLM Provider 抽象层 - 支持流式输出
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, List, Optional


class LLMProvider(ABC):
    """LLM Provider 抽象基类"""
    
    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式聊天完成
        
        Yields:
            Dict: {
                "content": str,           # 当前 token 内容
                "finish_reason": str,     # 结束原因 (null, stop, length)
                "usage": Dict             # Token 使用情况（仅在最后一条）
            }
        """
        pass
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        普通/流式聊天完成
        
        Args:
            stream: 是否启用流式
            
        Returns:
            Dict: {
                "content": str,
                "usage": Dict,
                "stream_response": AsyncGenerator  # 如果 stream=True
            }
        """
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI Provider 实现"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """真实的 OpenAI 流式调用"""
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    content = delta.content if delta.content else ""
                    
                    yield {
                        "content": content,
                        "finish_reason": chunk.choices[0].finish_reason,
                        "usage": None
                    }
                    
        except Exception as e:
            yield {
                "content": "",
                "finish_reason": "error",
                "error": str(e)
            }
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """OpenAI 普通/流式调用"""
        if stream:
            return {
                "stream_response": self.chat_completion_stream(
                    messages, temperature, max_tokens, **kwargs
                )
            }
        
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }


# 其他 Provider 实现（Azure, Claude 等）
class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI Provider"""
    # TODO: 实现 Azure 的流式接口
    pass


class AnthropicProvider(LLMProvider):
    """Claude Provider"""
    # TODO: 实现 Claude 的流式接口
    pass


# Provider 工厂函数
def create_llm_provider(
    provider_type: str,
    api_key: str,
    base_url: str,
    model: str
) -> LLMProvider:
    """创建 LLM Provider 实例"""
    providers = {
        "openai": OpenAIProvider,
        "azure": AzureOpenAIProvider,
        "anthropic": AnthropicProvider,
    }
    
    provider_class = providers.get(provider_type.lower())
    if not provider_class:
        raise ValueError(f"不支持的 Provider: {provider_type}")
    
    return provider_class(api_key, base_url, model)
