"""编排器：统筹整个审查流程"""
import uuid
import logging
from typing import List, Optional
from ..models import Report, SearchQuery, SearchResult, Analysis, TokenUsage, AppError, ErrorCode, Rating
from ..config import Config
from ..search.router import SearchRouter
from ..search.github_source import GithubSource
from ..search.aihot_source import AihotSource
from ..search.tavily_source import TavilySource
from ..llm.router import LLMRouter
from .llm_engine import LLMEngine
from .prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """审查流程编排器"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.prompt_manager = PromptManager()
        llm_config = self.config.get("llm", {})
        self.llm_router = LLMRouter(llm_config)
        self.llm_engine = LLMEngine(self.llm_router, self.prompt_manager)
        self.search_router = SearchRouter()
        search_config = self.config.get("search", {})
        self._init_search_sources(search_config)
        self.max_rounds = self.config.get("review.max_rounds", 5)

    def _init_search_sources(self, config: dict):
        sources = config.get("sources", ["github", "aihot"])
        if "github" in sources:
            try:
                self.search_router.register_source("github", GithubSource(config.get("github", {})))
            except Exception as e:
                logger.warning(f"GitHub源初始化失败: {e}")
        if "aihot" in sources:
            try:
                self.search_router.register_source("aihot", AihotSource(config.get("aihot", {})))
            except Exception as e:
                logger.warning(f"aihot源初始化失败: {e}")
        if "tavily" in sources:
            try:
                self.search_router.register_source("tavily", TavilySource(config.get("tavily", {})))
            except Exception as e:
                logger.warning(f"Tavily源初始化失败: {e}")

    def _read_candidates(self, results: List[SearchResult]) -> None:
        """候选仓库精读：对本轮 github 源结果按 stars 取 top N 拉 README，失败静默跳过。

        精读文本附着在 SearchResult.readme 上，供分析阶段作为证据上下文使用，
        可显著减少"只看摘要误判撞车"的问题。
        """
        n = int(self.config.get("review.readme_top_n", 3) or 0)
        if n <= 0:
            return
        gh = self.search_router.get_source("github")
        if gh is None or not hasattr(gh, "fetch_readme"):
            return
        candidates = [r for r in results if r.source == "github" and r.url and not r.readme]
        candidates.sort(key=lambda r: (r.github_meta.stars if r.github_meta else 0), reverse=True)
        for r in candidates[:n]:
            parsed = gh.repo_name_from_url(r.url)
            if not parsed:
                continue
            r.readme = gh.fetch_readme(parsed[0], parsed[1])
            if r.readme:
                logger.info(f"[精读] {r.title}（{len(r.readme)} 字符）")

    def check_idea(self, idea: str, persona: str = "default") -> Report:
        trace_id = str(uuid.uuid4())[:8]
        logger.info(f"[{trace_id}] 开始审查: {idea}")
        total_usage = TokenUsage()
        search_log = []
        all_results: List[SearchResult] = []
        context = {}
        try:
            queries, usage = self.llm_engine.decompose_idea(idea, trace_id)
            total_usage = self._add_usage(total_usage, usage)
            analysis = None
            for round_num in range(1, self.max_rounds + 1):
                round_results = []
                for query in queries[:3]:
                    try:
                        results = self.search_router.search(query, trace_id)
                        round_results.extend(results)
                        search_log.append({"round": round_num, "keyword": query.keyword, "result_count": len(results)})
                    except AppError as e:
                        logger.warning(f"搜索失败: {e.message}")
                        search_log.append({"round": round_num, "keyword": query.keyword, "error": e.message})
                all_results.extend(round_results)
                self._read_candidates(round_results)
                if not all_results:
                    analysis = Analysis(has_similar=False, similar_count=0, max_quality="无搜索结果", differentiation="无法判断", rating=Rating.UNKNOWN, confidence=0.0, key_findings=["所有搜索源均未返回结果"], missing_info=["需要搜索结果"], search_rounds=round_num)
                    break
                analysis, usage = self.llm_engine.analyze_results(all_results, idea, context if round_num > 1 else None, trace_id)
                total_usage = self._add_usage(total_usage, usage)
                analysis.search_rounds = round_num
                if round_num >= self.max_rounds:
                    break
                should_continue, next_queries, usage = self.llm_engine.should_continue(analysis, trace_id)
                total_usage = self._add_usage(total_usage, usage)
                if not should_continue:
                    break
                queries = next_queries or queries
                context = {"previous_rating": analysis.rating.value, "previous_confidence": analysis.confidence}
            if analysis is None:
                analysis = Analysis(has_similar=False, similar_count=0, max_quality="", differentiation="", rating=Rating.UNKNOWN, confidence=0.0, key_findings=["审查异常"], missing_info=[])
            report, usage = self.llm_engine.generate_report(analysis, idea, persona, trace_id)
            total_usage = self._add_usage(total_usage, usage)
            report.token_usage = total_usage
            report.search_log = search_log
            return report
        except AppError as e:
            logger.error(f"审查失败: {e.message}")
            return Report(idea=idea, rating=Rating.UNKNOWN, findings=[], conclusion=f"审查失败: {e.message}", suggestions=["请检查配置和网络"], persona=persona, raw_analysis=Analysis(has_similar=False, similar_count=0, max_quality="", differentiation="", rating=Rating.UNKNOWN, confidence=0.0, key_findings=[f"错误: {e.message}"], missing_info=[]), trace_id=trace_id, token_usage=total_usage, search_log=search_log)

    @staticmethod
    def _add_usage(total: TokenUsage, new: TokenUsage) -> TokenUsage:
        total.prompt_tokens += new.prompt_tokens
        total.completion_tokens += new.completion_tokens
        total.total_tokens += new.total_tokens
        return total
