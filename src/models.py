"""数据模型定义"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class Rating(Enum):
    """审查评级"""
    S_BLUE_OCEAN = "S级·蓝海"
    A_HAS_SPACE = "A级·有空间"
    B_COMPETING = "B级·竞争中"
    C_RED_OCEAN = "C级·红海"
    UNKNOWN = "信息不足"


class ErrorCode(Enum):
    """统一错误码"""
    LLM_API_ERROR = "LLM_001"
    LLM_TIMEOUT = "LLM_002"
    SEARCH_SOURCE_UNAVAILABLE = "SRCH_001"
    SEARCH_QUOTA_EXCEEDED = "SRCH_002"
    ALL_SOURCES_FAILED = "SRCH_003"
    INVALID_INPUT = "INPUT_001"
    CONFIG_ERROR = "CFG_001"
    AGENT_FRAMEWORK_ERROR = "AGENT_001"


class AppError(Exception):
    """统一错误结构"""
    def __init__(self, code: ErrorCode, message: str, trace_id: str = "",
                 details: Optional[Dict[str, Any]] = None, recoverable: bool = True,
                 source: str = ""):
        self.code = code
        self.message = message
        self.trace_id = trace_id
        self.details = details
        self.recoverable = recoverable
        self.source = source
        super().__init__(message)


@dataclass
class SearchQuery:
    """搜索查询"""
    keyword: str
    dimension: str
    source: Optional[str] = None
    priority: int = 0


@dataclass
class GithubMetadata:
    stars: int = 0
    forks: int = 0
    language: str = ""
    updated_at: Optional[str] = None
    license: Optional[str] = None      # SPDX 标识，无协议为 None
    archived: bool = False             # 仓库是否已归档（停止维护）
    pushed_at: Optional[str] = None    # 最近一次 push 时间


@dataclass
class WebMetadata:
    domain: str = ""
    position: int = 0


@dataclass
class AihotMetadata:
    publish_date: Optional[str] = None
    source_name: str = ""


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    url: str
    snippet: str
    source: str
    github_meta: Optional[GithubMetadata] = None
    web_meta: Optional[WebMetadata] = None
    aihot_meta: Optional[AihotMetadata] = None
    readme: Optional[str] = None  # 候选仓库精读（README 截断文本），仅 github 源 top N 有值


@dataclass
class TokenUsage:
    """token用量统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model: str = ""


@dataclass
class Analysis:
    """分析结果"""
    has_similar: bool
    similar_count: int
    max_quality: str
    differentiation: str
    rating: Rating
    confidence: float
    key_findings: List[str]
    missing_info: List[str]
    search_rounds: int = 0
    evidence: List[Dict] = field(default_factory=list)  # 证据链：[{url, title, verdict, evidence}]


@dataclass
class Report:
    """审查报告"""
    idea: str
    rating: Rating
    findings: List[str]
    conclusion: str
    suggestions: List[str]
    persona: str
    raw_analysis: Analysis
    trace_id: str = ""
    token_usage: Optional[TokenUsage] = None
    search_log: List[Dict] = field(default_factory=list)
    ranking: List[Dict] = field(default_factory=list)        # 竞品量化排序（见 core/ranking.py）
    saturation: Optional[Dict] = None                        # 市场饱和度（数据量化档 S/A/B/C）
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class QuotaStatus:
    """API额度状态"""
    source: str
    remaining: Optional[int] = None
    limit: Optional[int] = None
    warning: bool = False
