"""Tavily 搜索源（免费网页搜索）"""
import logging
import requests
from typing import List
from .base import SearchSource
from ..models import SearchResult, WebMetadata, AppError, ErrorCode

logger = logging.getLogger(__name__)


class TavilySource(SearchSource):
    name = "tavily"

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.base_url = "https://api.tavily.com/search"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, keyword: str) -> List[SearchResult]:
        if not self.api_key:
            raise AppError(code=ErrorCode.SEARCH_SOURCE_UNAVAILABLE, message="Tavily未配置API key", source="tavily")
        try:
            resp = requests.post(self.base_url, json={"api_key": self.api_key, "query": keyword, "max_results": self.max_results, "search_depth": "basic"}, timeout=15)
            if resp.status_code in (401, 403, 429):
                raise AppError(code=ErrorCode.SEARCH_QUOTA_EXCEEDED, message="Tavily key无效或额度用完", source="tavily")
            resp.raise_for_status()
            data = resp.json()
        except AppError:
            raise
        except Exception as e:
            raise AppError(code=ErrorCode.SEARCH_SOURCE_UNAVAILABLE, message=f"Tavily搜索失败: {str(e)}", source="tavily")
        results = []
        for item in data.get("results", []):
            results.append(SearchResult(title=item.get("title", ""), url=item.get("url", ""), snippet=item.get("content", "") or "无摘要", source="tavily", web_meta=WebMetadata(domain=item.get("domain", ""))))
        return results
