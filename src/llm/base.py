"""LLM提供者基类"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models import TokenUsage, AppError


class LLMProvider(ABC):
    """LLM提供者抽象基类"""
    name: str = "base"

    def __init__(self, config: dict):
        self.config = config
        self.timeout = config.get("timeout", 30)
        self.max_retries = config.get("max_retries", 2)

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000) -> tuple[str, TokenUsage]:
        pass

    def is_available(self) -> bool:
        return True
