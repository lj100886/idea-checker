"""OpenAI兼容API提供者（硅基流动、豆包、OpenRouter、DeepSeek、商汤SenseNova等）"""
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
        retried_for_empty = False  # 思考模型 content 被思考占满时，放大 max_tokens 重试一次
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                if resp.status_code == 429:
                    # 限流：部分平台（商汤SenseNova等）按短时频率限制，需更长退避
                    backoff = 10 * (attempt + 1)  # 10s / 20s / 30s
                    time.sleep(backoff)
                    raise AppError(code=ErrorCode.LLM_API_ERROR, message=f"限流429，已退避{backoff}s（第{attempt+1}次）", source="llm")
                resp.raise_for_status()
                data = resp.json()
                msg = data["choices"][0]["message"]
                content = msg.get("content") or ""
                reasoning = msg.get("reasoning_content") or ""
                usage_data = data.get("usage", {})
                usage = TokenUsage(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0),
                    model=self.model,
                )
                if not content and reasoning and not retried_for_empty:
                    # 思考模型：所有 token 都被 reasoning 占用，content 为空；放大 max_tokens 重试一次
                    retried_for_empty = True
                    payload["max_tokens"] = max(max_tokens * 2, 2048)
                    last_error = AppError(
                        code=ErrorCode.LLM_API_ERROR,
                        message="思考模型输出为空（reasoning占满token），放大max_tokens重试",
                        source="llm",
                    )
                    time.sleep(0.5)
                    continue
                if not content and reasoning:
                    # 兜底：重试后仍为空，退回 reasoning 内容，避免上层拿到空串崩溃
                    return reasoning, usage
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
