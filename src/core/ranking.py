"""竞品量化排序：基于 GitHub 信号的加权打分，替代纯 LLM 定级。

评分维度（单仓库 0-100）：
  - 流行度 popularity 45：stars 对数压缩，避免大仓库碾压小项目
  - 参与度 engagement 15：forks/stars 比，反映社区实际贡献意愿
  - 活跃度 recency   25：最近更新距今，两年内线性衰减
  - 维护状态 maintain -10：已归档（停止维护）直接扣分
  - 开放性 license    10：有开源协议加分，无协议偏私有/不开放

市场饱和度：取 Top5 平均分 + 全量最高分，映射到 S/A/B/C 数据档。
所有信号均来自 GitHub API 元数据，不依赖 LLM 主观判断。
"""
from typing import List, Dict, Optional
from datetime import datetime, timezone

from ..models import SearchResult, GithubMetadata


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        # GitHub API 返回如 2026-09-01T12:00:00Z 或 2026-09-01T12:00:00（无时区），统一按 UTC 处理
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def score_repo(meta: GithubMetadata) -> Dict:
    """对单个仓库计算加权分（0-100）与信号明细。"""
    stars = max(0, int(meta.stars or 0))
    forks = max(0, int(meta.forks or 0))

    # 流行度：stars 对数压缩，封顶 45，stars=50→22.5，500→40.9，5000→44.5
    popularity = 45 * (1 - 1 / (1 + stars / 50.0))

    # 参与度：forks/stars 比，封顶 15
    fork_ratio = (forks / stars) if stars > 0 else 0.0
    engagement = min(15.0, fork_ratio * 60.0)

    # 活跃度：最近更新距今，两年内线性衰减，封顶 25
    recency = 0.0
    updated = _parse_date(meta.updated_at) or _parse_date(meta.pushed_at)
    if updated:
        days = max(0, (datetime.now(timezone.utc) - updated).days)
        recency = max(0.0, min(25.0, 25.0 * (1 - days / 730.0)))

    # 维护状态：归档扣 10
    maintain = -10.0 if getattr(meta, "archived", False) else 0.0

    # 开放性：有协议 +10
    license_score = 10.0 if getattr(meta, "license", None) else 0.0

    score = max(0.0, popularity + engagement + recency + maintain + license_score)
    return {
        "score": round(score, 1),
        "signals": {
            "stars": stars,
            "forks": forks,
            "fork_ratio": round(fork_ratio, 3),
            "updated_at": meta.updated_at,
            "license": getattr(meta, "license", None),
            "archived": getattr(meta, "archived", False),
        },
    }


def rank_results(results: List[SearchResult]) -> List[Dict]:
    """对全部 GitHub 结果打分排序，返回带分列表（按分降序）。"""
    scored = []
    for r in results:
        meta = r.github_meta
        if meta is None:
            continue
        s = score_repo(meta)
        scored.append({
            "title": r.title,
            "url": r.url,
            "score": s["score"],
            "signals": s["signals"],
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def market_saturation(scored: List[Dict]) -> Dict:
    """综合市场饱和度：看 Top 候选的聚合热度，映射到 S/A/B/C 数据档。"""
    if not scored:
        return {
            "index": 0.0,
            "max_score": 0.0,
            "tier": "S",
            "label": "蓝海（无 GitHub 对标）",
            "top_n": 0,
        }
    top = scored[:5]
    avg = sum(x["score"] for x in top) / len(top)
    max_score = max(x["score"] for x in scored)
    if max_score < 20:
        tier, label = "S", "蓝海（几乎没人做/都很弱）"
    elif max_score < 45:
        tier, label = "A", "有空间（有人做但不强）"
    elif max_score < 70:
        tier, label = "B", "竞争中（已有较强对标）"
    else:
        tier, label = "C", "红海（头部成熟产品明显）"
    return {
        "index": round(avg, 1),
        "max_score": round(max_score, 1),
        "tier": tier,
        "label": label,
        "top_n": len(scored),
    }
