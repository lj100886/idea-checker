"""GitHub搜索源"""
import re
import logging
import requests
import urllib3
from typing import List, Optional, Tuple
from .base import SearchSource
from ..models import SearchResult, GithubMetadata, AppError, ErrorCode

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class GithubSource(SearchSource):
    name = "github"

    def __init__(self, config: dict):
        super().__init__(config)
        self.token = config.get("token", "")
        self.base_url = "https://api.github.com/search/repositories"

    def _headers(self) -> dict:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def search(self, keyword: str) -> List[SearchResult]:
        headers = self._headers()
        params = {"q": keyword, "sort": "stars", "order": "desc", "per_page": self.max_results}
        try:
            resp = requests.get(self.base_url, headers=headers, params=params, timeout=10, verify=False)
            if resp.status_code == 403:
                raise AppError(code=ErrorCode.SEARCH_QUOTA_EXCEEDED, message="GitHub额度用完（未认证60次/小时）", source="github")
            resp.raise_for_status()
            data = resp.json()
        except AppError:
            raise
        except Exception as e:
            raise AppError(code=ErrorCode.SEARCH_SOURCE_UNAVAILABLE, message=f"GitHub搜索失败: {str(e)}", source="github")
        results = []
        for item in data.get("items", []):
            lic = item.get("license") or {}
            results.append(SearchResult(title=item.get("full_name", ""), url=item.get("html_url", ""), snippet=item.get("description", "") or "无描述", source="github", github_meta=GithubMetadata(
                stars=item.get("stargazers_count", 0),
                forks=item.get("forks_count", 0),
                language=item.get("language", "") or "",
                updated_at=item.get("updated_at", "") or None,
                license=(lic.get("spdx_id") if isinstance(lic, dict) else None) or None,
                archived=bool(item.get("archived", False)),
                pushed_at=item.get("pushed_at", "") or None,
            )))
        return results

    @staticmethod
    def repo_name_from_url(url: str) -> Optional[Tuple[str, str]]:
        """从仓库URL提取 (owner, repo)；无法解析返回 None"""
        if not url:
            return None
        m = re.match(r"https?://github\.com/([^/]+)/([^/]+)", url)
        if m:
            return m.group(1), m.group(2).rstrip("/")
        return None

    def fetch_readme(self, owner: str, repo: str, max_chars: int = 1500) -> Optional[str]:
        """拉取仓库 README 前 max_chars 字符用于候选精读；无 README/限速/失败返回 None"""
        headers = {"Accept": "application/vnd.github.raw+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        try:
            resp = requests.get(url, headers=headers, timeout=10, verify=False)
            if resp.status_code == 404:
                return None
            if resp.status_code == 403:
                logger.warning(f"GitHub限速，跳过精读 {owner}/{repo}")
                return None
            resp.raise_for_status()
            text = resp.text.strip()
            if not text:
                return None
            return text[:max_chars]
        except Exception as e:
            logger.warning(f"精读失败 {owner}/{repo}: {e}")
            return None
