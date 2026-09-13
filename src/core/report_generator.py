"""报告生成器：格式化输出"""
import json
from typing import Optional
from ..models import Report


class ReportGenerator:
    """报告格式化"""

    @staticmethod
    def _evidence_lines(report: Report) -> list:
        """提取证据链行；无证据返回空列表"""
        evidence = getattr(report.raw_analysis, "evidence", []) or []
        lines = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            url = item.get("url", "")
            title = item.get("title", "")
            verdict = item.get("verdict", "")
            ev = item.get("evidence", "")
            lines.append(f"  - {title}（{verdict}）：{ev} {url}".rstrip())
        return lines

    @staticmethod
    def to_text(report: Report) -> str:
        lines = ["=" * 50, f"选题审查报告", f"想法：{report.idea}", f"评级：{report.rating.value}", f"人设：{report.persona}", "=" * 50, "", "【结论】", report.conclusion, "", "【关键发现】"]
        for i, f in enumerate(report.findings, 1):
            lines.append(f"  {i}. {f}")
        evidence_lines = ReportGenerator._evidence_lines(report)
        if evidence_lines:
            lines.extend(["", "【证据链】"])
            lines.extend(evidence_lines)
        # 竞品量化排序（数据驱动，替代纯 LLM 定级）
        if report.saturation:
            lines.extend(["", "【竞品量化排序 · 数据驱动】"])
            sat = report.saturation
            lines.append(f"  市场量化档：{sat['tier']}级 · {sat['label']}（最高分 {sat['max_score']}，Top5 均值 {sat['index']}，共 {sat['top_n']} 个 GitHub 对标）")
            for i, r in enumerate(report.ranking[:10], 1):
                sig = r.get("signals", {})
                lic = sig.get("license") or "无协议"
                arch = " [已归档]" if sig.get("archived") else ""
                lines.append(f"  {i}. {r['title']}  {r['score']}分  ★{sig.get('stars', 0)} Fork{sig.get('forks', 0)}  {lic}{arch}")
        lines.extend(["", "【建议】"])
        for i, s in enumerate(report.suggestions, 1):
            lines.append(f"  {i}. {s}")
        if report.token_usage:
            lines.extend(["", f"【统计】Token: {report.token_usage.total_tokens}, 轮次: {report.raw_analysis.search_rounds}"])
        lines.append("=" * 50)
        return "\n".join(lines)

    @staticmethod
    def to_json(report: Report) -> str:
        data = {"idea": report.idea, "rating": report.rating.value, "conclusion": report.conclusion, "findings": report.findings, "suggestions": report.suggestions, "persona": report.persona, "confidence": report.raw_analysis.confidence, "search_rounds": report.raw_analysis.search_rounds, "evidence": getattr(report.raw_analysis, "evidence", []), "trace_id": report.trace_id, "market_saturation": report.saturation, "ranking": report.ranking}
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def to_markdown(report: Report) -> str:
        lines = [f"# 选题审查报告：{report.idea}", "", f"**评级：{report.rating.value}** | 置信度：{report.raw_analysis.confidence:.0%}", "", "## 结论", report.conclusion, "", "## 关键发现"]
        for f in report.findings:
            lines.append(f"- {f}")
        evidence_lines = ReportGenerator._evidence_lines(report)
        if evidence_lines:
            lines.extend(["", "## 证据链"])
            lines.extend(evidence_lines)
        if report.saturation:
            sat = report.saturation
            lines.extend(["", "## 竞品量化排序（数据驱动）", f"**市场量化档：{sat['tier']}级 · {sat['label']}**（最高分 {sat['max_score']}，Top5 均值 {sat['index']}，共 {sat['top_n']} 个 GitHub 对标）"])
            for i, r in enumerate(report.ranking[:10], 1):
                sig = r.get("signals", {})
                lic = sig.get("license") or "无协议"
                arch = "（已归档）" if sig.get("archived") else ""
                lines.append(f"{i}. **{r['title']}** {r['score']}分 — ★{sig.get('stars', 0)} Fork{sig.get('forks', 0)} {lic}{arch}")
        lines.extend(["", "## 建议"])
        for s in report.suggestions:
            lines.append(f"- {s}")
        return "\n".join(lines)
