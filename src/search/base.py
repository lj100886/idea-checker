"""搜索源基类"""
from abc import ABC, abstractmethod
from typing import List
from ..models import SearchResult, AppError, ErrorCode


class SearchSource(ABC):
    """搜索源抽象基类"""
    name: str = "base"

    def __init__(self, config: dict):
        self.config = config
        self.max_results = config.get("max_results", 10)

    @abstractmethod
    def search(self, keyword: str) -> List[SearchResult]:
        pass

    def is_available(self) -> bool:
        return True
