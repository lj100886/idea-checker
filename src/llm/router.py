"""LLM路由器：主用智能体框架，失败降级到直接API"""
import logging
from typing import List, Dict, Tuple, Optional
from .base import LLMProvider
from .openai_compatible import OpenAICompatibleProvider
from .agent_framework import AgentFrameworkProvider
from ..models import TokenUsage, AppError

logger = logging.getLogger(__name__)


class LLMRouter:
    """LLM路由器：智能体框架优先，API降级"""

    def __init__(self, config: dict):
        self.config = config
        self.mode = config.get("mode", "api")
        self.api_provider = OpenAICompatibleProvider(config.get("api", {}))
        self.agent_provider = AgentFrameworkProvider(config.get("agent_framework", {}))

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000, trace_id: str = "") -> Tuple[str, TokenUsage]:
        if self.mode == "api":
            return self._call_provider(self.api_provider, messages, temperature, max_tokens, trace_id)
        if self.mode == "agent_framework":
            return self._call_provider(self.agent_provider, messages, temperature, max_tokens, trace_id)
        if self.agent_provider.is_available():
            try:
                return self._call_provider(self.agent_provider, messages, temperature, max_tokens, trace_id)
            except AppError as e:
                logger.warning(f"框架失败: {e.message}，降级API")
                return self._call_provider(self.api_provider, messages, temperature, max_tokens, trace_id)
        return self._call_provider(self.api_provider, messages, temperature, max_tokens, trace_id)

    def _call_provider(self, provider, messages, temperature, max_tokens, trace_id):
        logger.info(f"[{trace_id}] 使用 {provider.name}")
        return provider.chat(messages, temperature, max_tokens)
