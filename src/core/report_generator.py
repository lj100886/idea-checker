"""报告生成器：格式化输出"""
import json
from typing import Optional
from ..models import Report


class ReportGenerator:
    """报告格式化"""

    @staticmethod
    def to_text(report: Report) -> str:
        lines = ["=" * 50, f"选题审查报告", f"想法：{report.idea}", f"评级：{report.rating.value}", f"人设：{report.persona}", "=" * 50, "", "【结论】", report.conclusion, "", "【关键发现】"]
        for i, f in enumerate(report.findings, 1):
            lines.append(f"  {i}. {f}")
        lines.extend(["", "【建议】"])
        for i, s in enumerate(report.suggestions, 1):
            lines.append(f"  {i}. {s}")
        if report.token_usage:
            lines.extend(["", f"【统计】Token: {report.token_usage.total_tokens}, 轮次: {report.raw_analysis.search_rounds}"])
        lines.append("=" * 50)
        return "\n".join(lines)

    @staticmethod
    def to_json(report: Report) -> str:
        data = {"idea": report.idea, "rating": report.rating.value, "conclusion": report.conclusion, "findings": report.findings, "suggestions": report.suggestions, "persona": report.persona, "confidence": report.raw_analysis.confidence, "search_rounds": report.raw_analysis.search_rounds, "trace_id": report.trace_id}
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def to_markdown(report: Report) -> str:
        lines = [f"# 选题审查报告：{report.idea}", "", f"**评级：{report.rating.value}** | 置信度：{report.raw_analysis.confidence:.0%}", "", "## 结论", report.conclusion, "", "## 关键发现"]
        for f in report.findings:
            lines.append(f"- {f}")
        lines.extend(["", "## 建议"])
        for s in report.suggestions:
            lines.append(f"- {s}")
        return "\n".join(lines)
