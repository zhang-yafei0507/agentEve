"""
LLM 客户端 - 真实的大模型调用
"""
import aiohttp
import json
from typing import Dict, List, Optional, AsyncGenerator


class LLMClient:
    """通用 LLM 客户端（支持多种 API）"""
    
    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.base_url = base_url or "http://localhost:8000/v1"
        self.model = model or "default-model"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self):
        """确保 HTTP 会话已创建"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """关闭 HTTP 会话"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        top_p: float = 0.8,
        top_k: int = 1
    ) -> Dict:
        """
        非流式对话完成
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大 token 数
            stream: 是否流式输出
            top_p: Top-P 采样参数
            top_k: Top-K 采样参数
            
        Returns:
            {"content": "...", "usage": {...}}
        """
        await self._ensure_session()
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "AgentEve3/1.0.0",
        }
        
        # 使用 token header（根据你的接口要求）
        if self.api_key:
            headers["token"] = self.api_key
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "stream": stream
        }
        
        # 只添加有值的参数
        if max_tokens > 0:
            payload["max_tokens"] = max_tokens
        
        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LLM API 错误 ({response.status}): {error_text}")
                
                result = await response.json()
                
                # 提取回复内容
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = result.get("usage", {})
                
                return {
                    "content": content,
                    "usage": usage
                }
        except Exception as e:
            print(f"[LLM Client] 调用失败：{e}")
            raise
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.8,
        top_k: int = 1
    ) -> AsyncGenerator[str, None]:
        """
        流式对话完成
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Yields:
            文本片段
        """
        await self._ensure_session()
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "AgentEve3/1.0.0",
        }
        
        if self.api_key:
            headers["token"] = self.api_key
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "stream": True
        }
        
        if max_tokens > 0:
            payload["max_tokens"] = max_tokens
        
        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LLM API 错误 ({response.status}): {error_text}")
                
                # 处理 SSE 流
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]  # 去掉 "data: " 前缀
                        if data == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            print(f"[LLM Client] 流式调用失败：{e}")
            raise
    
    async def simple_call(self, prompt: str) -> str:
        """
        简单调用（单次对话）
        
        Args:
            prompt: 用户输入
            
        Returns:
            AI 回复
        """
        messages = [
            {"role": "system", "content": "你是一个智能助手，请用中文回答用户的问题。"},
            {"role": "user", "content": prompt}
        ]
        
        result = await self.chat_completion(messages)
        return result["content"]


async def create_llm_client(provider: str = "local", **kwargs) -> LLMClient:
    """
    创建 LLM 客户端的工厂函数
    
    Args:
        provider: 提供商 ("local", "openai", "custom")
        **kwargs: 其他参数
        
    Returns:
        LLMClient 实例
    """
    if provider == "openai":
        return LLMClient(
            api_key=kwargs.get("api_key", ""),
            base_url="https://api.openai.com/v1",
            model=kwargs.get("model", "gpt-3.5-turbo")
        )
    elif provider == "local" or provider == "custom":
        # 本地的免费 LLM 接口（你的接口）
        return LLMClient(
            api_key=kwargs.get("api_key", ""),
            base_url=kwargs.get("base_url", "http://192.168.83.238:49869/v1"),
            model=kwargs.get("model", "Qwen")
        )
    else:
        raise ValueError(f"不支持的 LLM 提供商：{provider}")
