"""GitHub搜索源"""
import requests
import urllib3
from typing import List
from .base import SearchSource
from ..models import SearchResult, GithubMetadata, AppError, ErrorCode

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class GithubSource(SearchSource):
    name = "github"

    def __init__(self, config: dict):
        super().__init__(config)
        self.token = config.get("token", "")
        self.base_url = "https://api.github.com/search/repositories"

    def search(self, keyword: str) -> List[SearchResult]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
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
            results.append(SearchResult(title=item.get("full_name", ""), url=item.get("html_url", ""), snippet=item.get("description", "") or "无描述", source="github", github_meta=GithubMetadata(stars=item.get("stargazers_count", 0), forks=item.get("forks_count", 0), language=item.get("language", ""), updated_at=item.get("updated_at", ""))))
        return results
