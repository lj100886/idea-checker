"""DuckDuckGo搜索源（完全免费，无需API key）"""
from typing import List
from .base import SearchSource
from ..models import SearchResult, WebMetadata, AppError, ErrorCode


class DuckDuckGoSource(SearchSource):
    name = "duckduckgo"

    def __init__(self, config: dict):
        super().__init__(config)
        self.region = config.get("region", "cn-zh")

    def search(self, keyword: str) -> List[SearchResult]:
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
        except ImportError:
            raise AppError(code=ErrorCode.CONFIG_ERROR, message="未安装ddgs: pip install ddgs", source="duckduckgo")
        try:
            with DDGS() as ddgs:
                try:
                    raw_results = list(ddgs.text(query=keyword, region=self.region, max_results=self.max_results))
                except TypeError:
                    raw_results = list(ddgs.text(keywords=keyword, region=self.region, max_results=self.max_results))
        except Exception as e:
            raise AppError(code=ErrorCode.SEARCH_SOURCE_UNAVAILABLE, message=f"DuckDuckGo失败: {str(e)}", source="duckduckgo")
        results = []
        for i, item in enumerate(raw_results):
            results.append(SearchResult(title=item.get("title", ""), url=item.get("href", ""), snippet=item.get("body", "") or "", source="web", web_meta=WebMetadata(domain=item.get("href", "").split("/")[2] if "://" in item.get("href", "") else "", position=i + 1)))
        return results
