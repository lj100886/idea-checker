"""搜索源模块"""
from .base import SearchSource
from .router import SearchRouter
from .github_source import GithubSource
from .duckduckgo_source import DuckDuckGoSource
from .aihot_source import AihotSource

__all__ = ["SearchSource", "SearchRouter", "GithubSource", "DuckDuckGoSource", "AihotSource"]
