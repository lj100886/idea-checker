"""aihot MCP搜索源（AI热点新闻）"""
import requests
import json
from typing import List
from .base import SearchSource
from ..models import SearchResult, AihotMetadata, AppError, ErrorCode


class AihotSource(SearchSource):
    name = "aihot"

    def __init__(self, config: dict):
        super().__init__(config)
        self.endpoint = config.get("endpoint", "")

    def _parse_sse(self, text: str) -> dict:
        for line in text.strip().split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str:
                    try:
                        return json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
        raise ValueError(f"无法解析SSE: {text[:200]}")

    def _mcp_call(self, tool_name: str, arguments: dict) -> dict:
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        init_payload = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "idea-checker", "version": "0.1.0"}}}
        try:
            resp = requests.post(self.endpoint, headers=headers, json=init_payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            raise AppError(code=ErrorCode.SEARCH_SOURCE_UNAVAILABLE, message=f"aihot初始化失败: {str(e)}", source="aihot")
        call_payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool_name, "arguments": arguments}}
        try:
            resp = requests.post(self.endpoint, headers=headers, json=call_payload, timeout=15)
            resp.raise_for_status()
            if resp.encoding and resp.encoding.lower() == 'iso-8859-1':
                resp.encoding = 'utf-8'
            return self._parse_sse(resp.text)
        except AppError:
            raise
        except Exception as e:
            raise AppError(code=ErrorCode.SEARCH_SOURCE_UNAVAILABLE, message=f"aihot调用失败: {str(e)}", source="aihot")

    def search(self, keyword: str) -> List[SearchResult]:
        result = self._mcp_call("aihot_search", {"q": keyword, "limit": self.max_results})
        structured = result.get("result", {}).get("structuredContent", {})
        items = structured.get("items", [])
        results = []
        for item in items:
            if isinstance(item, dict):
                links = item.get("links", {})
                source = item.get("source", {})
                results.append(SearchResult(title=item.get("title", ""), url=links.get("original", links.get("aihot", "")), snippet=item.get("summary", "") or "", source="aihot", aihot_meta=AihotMetadata(publish_date=item.get("publishedAt", ""), source_name=source.get("name", ""))))
        return results
