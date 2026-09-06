"""智能体框架提供者（主路线）：将任务转发给用户已接入的智能体框架执行"""
import requests
import json
from typing import List, Dict, Tuple, Optional
from .base import LLMProvider
from ..models import TokenUsage, AppError, ErrorCode


class AgentFrameworkProvider(LLMProvider):
    name = "agent_framework"

    def __init__(self, config: dict):
        super().__init__(config)
        self.framework_type = config.get("type", "auto")
        self.endpoint = config.get("endpoint", "")
        self.api_key = config.get("api_key", "")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000) -> Tuple[str, TokenUsage]:
        if not self.endpoint:
            raise AppError(code=ErrorCode.CONFIG_ERROR, message="未配置智能体框架端点", source="agent_framework")
        payload = {"task": "idea_review", "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=self.timeout * 2)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("content", data.get("result", data.get("response", "")))
            if not content:
                raise AppError(code=ErrorCode.AGENT_FRAMEWORK_ERROR, message=f"框架返回格式异常: {str(data)[:200]}", source="agent_framework")
            usage = TokenUsage(prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0), completion_tokens=data.get("usage", {}).get("completion_tokens", 0), total_tokens=data.get("usage", {}).get("total_tokens", 0), model=f"agent_framework:{self.framework_type}")
            return content, usage
        except AppError:
            raise
        except Exception as e:
            raise AppError(code=ErrorCode.AGENT_FRAMEWORK_ERROR, message=f"框架调用失败: {str(e)}", source="agent_framework")

    def is_available(self) -> bool:
        return bool(self.endpoint)
