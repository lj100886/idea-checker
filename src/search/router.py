"""搜索路由：统一搜索入口，支持源的注册、降级和自动选择"""
import logging
from typing import List, Optional, Dict
from .base import SearchSource
from ..models import SearchQuery, SearchResult, AppError

logger = logging.getLogger(__name__)


class SearchRouter:
    """搜索路由器"""

    def __init__(self):
        self._sources: Dict[str, SearchSource] = {}

    def register_source(self, name: str, source: SearchSource) -> None:
        self._sources[name] = source
        logger.info(f"注册搜索源: {name}")

    def get_source(self, name: str) -> Optional[SearchSource]:
        """按名称取已注册搜索源，未注册返回 None"""
        return self._sources.get(name)

    def get_available_sources(self) -> List[str]:
        return [name for name, src in self._sources.items() if src.is_available()]

    def search(self, query: SearchQuery, trace_id: str = "") -> List[SearchResult]:
        if query.source and query.source in self._sources:
            return self._search_with_source(query.source, query.keyword, trace_id)
        keyword_lower = query.keyword.lower()
        source_order = ["github", "aihot", "tavily"]
        if any(k in keyword_lower for k in ["github", "开源", "repository", "repo"]):
            source_order = ["github", "tavily", "aihot"]
        elif any(k in keyword_lower for k in ["ai", "人工智能", "大模型", "llm", "gpt"]):
            source_order = ["tavily", "aihot", "github"]
        all_results = []
        for source_name in source_order:
            if source_name not in self._sources:
                continue
            try:
                results = self._search_with_source(source_name, query.keyword, trace_id)
                all_results.extend(results)
                if results:
                    logger.info(f"[{trace_id}] {source_name} 返回 {len(results)} 条")
                    break
            except AppError as e:
                logger.warning(f"[{trace_id}] {source_name} 失败: {e.message}，降级")
                continue
        return all_results

    def _search_with_source(self, source_name: str, keyword: str, trace_id: str) -> List[SearchResult]:
        source = self._sources[source_name]
        logger.info(f"[{trace_id}] 使用 {source_name} 搜索: {keyword}")
        return source.search(keyword)
