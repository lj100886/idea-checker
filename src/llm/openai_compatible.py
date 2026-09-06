"""OpenAI兼容API提供者（硅基流动、豆包、OpenRouter、DeepSeek等）"""
import time
import requests
from typing import List, Dict, Tuple
from .base import LLMProvider
from ..models import TokenUsage, AppError, ErrorCode


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://api.siliconflow.cn/v1")
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "Qwen/Qwen3-8B")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000) -> Tuple[str, TokenUsage]:
        if not self.api_key:
            raise AppError(code=ErrorCode.CONFIG_ERROR, message="未配置LLM API Key", source="llm")
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                if resp.status_code == 429:
                    raise AppError(code=ErrorCode.LLM_API_ERROR, message=f"限流429，尝试{attempt+1}", source="llm")
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                usage_data = data.get("usage", {})
                usage = TokenUsage(prompt_tokens=usage_data.get("prompt_tokens", 0), completion_tokens=usage_data.get("completion_tokens", 0), total_tokens=usage_data.get("total_tokens", 0), model=self.model)
                return content, usage
            except AppError as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(1 * (attempt + 1))
                    continue
                raise
            except Exception as e:
                last_error = AppError(code=ErrorCode.LLM_API_ERROR, message=f"调用失败: {str(e)}", source="llm")
                if attempt < self.max_retries:
                    time.sleep(1 * (attempt + 1))
                    continue
                raise last_error
        raise last_error
