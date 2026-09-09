"""LLM引擎：AI拆解、分析、停止判断、报告生成"""
import json
import logging
import re
from typing import List, Dict, Tuple, Optional
from ..models import SearchQuery, SearchResult, Analysis, Rating, Report, TokenUsage, AppError, ErrorCode
from ..llm.router import LLMRouter
from .prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class LLMEngine:
    """AI核心引擎"""

    def __init__(self, llm_router: LLMRouter, prompt_manager: PromptManager):
        self.llm = llm_router
        self.prompts = prompt_manager

    def _parse_json_response(self, content: str) -> dict:
        """解析LLM返回的JSON，四级容错"""
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                pass
        if start >= 0:
            truncated = content[start:]
            last_newline = truncated.rfind("\n")
            if last_newline > 0:
                truncated = truncated[:last_newline]
            open_braces = truncated.count("{") - truncated.count("}")
            open_brackets = truncated.count("[") - truncated.count("]")
            truncated = truncated.rstrip().rstrip(",")
            truncated += "]" * max(0, open_brackets)
            truncated += "}" * max(0, open_braces)
            try:
                return json.loads(truncated)
            except json.JSONDecodeError:
                pass
        result = {}
        rating_match = re.search(r'"rating"\s*:\s*"([^"]+)"', content)
        if rating_match:
            result["rating"] = rating_match.group(1)
        conf_match = re.search(r'"confidence"\s*:\s*([\d.]+)', content)
        if conf_match:
            result["confidence"] = float(conf_match.group(1))
        has_sim_match = re.search(r'"has_similar"\s*:\s*(true|false)', content, re.IGNORECASE)
        if has_sim_match:
            result["has_similar"] = has_sim_match.group(1).lower() == "true"
        count_match = re.search(r'"similar_count"\s*:\s*(\d+)', content)
        if count_match:
            result["similar_count"] = int(count_match.group(1))
        if result:
            logger.warning(f"JSON解析降级为正则提取")
            return result
        raise AppError(code=ErrorCode.LLM_API_ERROR, message=f"LLM返回JSON解析失败: {content[:200]}")

    def decompose_idea(self, idea: str, trace_id: str = "") -> Tuple[List[SearchQuery], TokenUsage]:
        system_prompt = self.prompts.get_prompt("decompose")
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"用户想法：{idea}"}]
        content, usage = self.llm.chat(messages, temperature=0.3, max_tokens=500, trace_id=trace_id)
        data = self._parse_json_response(content)
        queries = []
        for q in data.get("queries", []):
            queries.append(SearchQuery(keyword=q.get("keyword", ""), dimension=q.get("dimension", "直接命中"), priority=q.get("priority", 0)))
        queries.sort(key=lambda x: x.priority)
        return queries, usage

    def analyze_results(self, results: List[SearchResult], idea: str, context: Optional[dict] = None, trace_id: str = "") -> Tuple[Analysis, TokenUsage]:
        system_prompt = self.prompts.get_prompt("analyze")
        results_text = ""
        for i, r in enumerate(results[:20]):
            results_text += f"{i+1}. [{r.source}] {r.title}\n   URL: {r.url}\n   摘要: {r.snippet[:200]}\n"
            if r.github_meta:
                results_text += f"   Stars: {r.github_meta.stars}\n"
            if r.readme:
                results_text += f"   README精读: {r.readme[:600].replace(chr(10), ' ')}\n"
        user_msg = f"用户想法：{idea}\n\n搜索结果：\n{results_text}"
        if context:
            user_msg += f"\n\n历史分析：{json.dumps(context, ensure_ascii=False)[:1000]}"
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}]
        content, usage = self.llm.chat(messages, temperature=0.4, max_tokens=3000, trace_id=trace_id)
        data = self._parse_json_response(content)
        try:
            rating = Rating(data.get("rating", "信息不足"))
        except ValueError:
            rating = Rating.UNKNOWN
        evidence = data.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = []
        analysis = Analysis(has_similar=data.get("has_similar", False), similar_count=data.get("similar_count", 0), max_quality=data.get("max_quality", ""), differentiation=data.get("differentiation", ""), rating=rating, confidence=data.get("confidence", 0.0), key_findings=data.get("key_findings", []), missing_info=data.get("missing_info", []), evidence=evidence)
        return analysis, usage

    def should_continue(self, analysis: Analysis, trace_id: str = "") -> Tuple[bool, List[SearchQuery], TokenUsage]:
        system_prompt = self.prompts.get_prompt("should_continue")
        analysis_dict = {"has_similar": analysis.has_similar, "similar_count": analysis.similar_count, "rating": analysis.rating.value, "confidence": analysis.confidence, "missing_info": analysis.missing_info, "search_rounds": analysis.search_rounds}
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"当前分析：{json.dumps(analysis_dict, ensure_ascii=False)}"}]
        content, usage = self.llm.chat(messages, temperature=0.2, max_tokens=800, trace_id=trace_id)
        try:
            data = self._parse_json_response(content)
        except Exception:
            return False, [], usage
        should = data.get("should_continue", False)
        next_queries = []
        for q in data.get("next_queries", []):
            next_queries.append(SearchQuery(keyword=q.get("keyword", ""), dimension=q.get("dimension", "补充搜索"), priority=q.get("priority", 0)))
        return should, next_queries, usage

    def generate_report(self, analysis: Analysis, idea: str, persona: str = "default", trace_id: str = "") -> Tuple[Report, TokenUsage]:
        system_prompt = self.prompts.get_prompt("report")
        from ..config import Config
        config = Config()
        persona_prompt = config.get_persona(persona)
        if persona_prompt:
            system_prompt += f"\n\n【人设】\n{persona_prompt}"
        analysis_dict = {"rating": analysis.rating.value, "confidence": analysis.confidence, "key_findings": analysis.key_findings, "differentiation": analysis.differentiation, "evidence": analysis.evidence}
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"想法：{idea}\n分析：{json.dumps(analysis_dict, ensure_ascii=False)}"}]
        content, usage = self.llm.chat(messages, temperature=0.6, max_tokens=1000, trace_id=trace_id)
        data = self._parse_json_response(content)
        report = Report(idea=idea, rating=analysis.rating, findings=data.get("findings", analysis.key_findings), conclusion=data.get("conclusion", ""), suggestions=data.get("suggestions", []), persona=persona, raw_analysis=analysis, trace_id=trace_id, token_usage=usage)
        return report, usage
