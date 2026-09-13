"""搜索路由：统一搜索入口，支持源的注册、降级和自动选择"""
import logging
import concurrent.futures
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
        # 多源并行聚合：不再"首个非空源就停"，所有已注册源都查，再按 URL 去重
        keyword_lower = query.keyword.lower()
        source_order = ["github", "aihot", "tavily"]
        if any(k in keyword_lower for k in ["github", "开源", "repository", "repo"]):
            source_order = ["github", "tavily", "aihot"]
        elif any(k in keyword_lower for k in ["ai", "人工智能", "大模型", "llm", "gpt"]):
            source_order = ["tavily", "aihot", "github"]
        active = [s for s in source_order if s in self._sources]
        if not active:
            return []
        per_source: Dict[str, List[SearchResult]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(active)) as ex:
            future_to_src = {ex.submit(self._safe_search, s, query.keyword, trace_id): s for s in active}
            for fut in concurrent.futures.as_completed(future_to_src):
                s = future_to_src[fut]
                try:
                    per_source[s] = fut.result()
                except Exception as e:
                    logger.warning(f"[{trace_id}] {s} 聚合异常: {e}")
                    per_source[s] = []
        # 聚合 + 按 URL 去重（保留先命中的源）
        seen = set()
        all_results: List[SearchResult] = []
        for s in active:
            for r in per_source.get(s, []):
                key = (r.url or "").strip().lower()
                if key:
                    if key in seen:
                        continue
                    seen.add(key)
                all_results.append(r)
        logger.info(f"[{trace_id}] 多源聚合完成：{len(active)} 个源，共 {len(all_results)} 条（去重后）")
        return all_results

    def _safe_search(self, source_name: str, keyword: str, trace_id: str) -> List[SearchResult]:
        try:
            results = self._search_with_source(source_name, keyword, trace_id)
            logger.info(f"[{trace_id}] {source_name} 返回 {len(results)} 条")
            return results
        except AppError as e:
            logger.warning(f"[{trace_id}] {source_name} 失败: {e.message}，跳过")
            return []

    def _search_with_source(self, source_name: str, keyword: str, trace_id: str) -> List[SearchResult]:
        source = self._sources[source_name]
        logger.info(f"[{trace_id}] 使用 {source_name} 搜索: {keyword}")
        return source.search(keyword)
