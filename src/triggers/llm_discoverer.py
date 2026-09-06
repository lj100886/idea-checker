"""LLM驱动的目录发现器：脚本只读文件系统，LLM做语义判断"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from ..llm.base import LLMProvider
from ..models import TokenUsage

logger = logging.getLogger(__name__)

SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "env", "AppData", "Windows", "Program Files", "$Recycle.Bin", ".cache", ".npm", ".pip", "dist", "build", "target"}

AGENT_DIR_KEYWORDS = ["agent", "gpt", "claude", "cursor", "doubao", "qwen", "tongyi", "auto", "crew", "马维斯", "智能", "协作", "chat", "conversation", "ai", "llm", "prompt", "workspace", "project"]

PROJECT_MARKERS = ["README.md", "package.json", "pyproject.toml", "requirements.txt", "conversation.json", "agent.json", "task.json", ".git", "main_agent_context", "run_meta.json", "mode.txt", "outline.md"]


class LLMDiscoverer:
    def __init__(self, llm_provider: LLMProvider, config: Optional[dict] = None):
        self.llm = llm_provider
        self.config = config or {}
        self.max_depth = self.config.get("max_depth", 3)
        self.max_dirs = self.config.get("max_dirs", 500)

    def scan_directory_tree(self, roots: List[str]) -> List[Dict]:
        tree = []
        total = [0]
        def _scan(path: Path, depth: int):
            if total[0] >= self.max_dirs or depth > self.max_depth:
                return
            try:
                entries = list(path.iterdir())
            except (PermissionError, OSError):
                return
            dirs = []
            files = []
            for e in entries:
                if e.name in SKIP_DIRS:
                    continue
                if e.is_dir():
                    dirs.append(e.name)
                elif e.is_file():
                    if any(k in e.name.lower() for k in ["readme", "package", "conversation", "agent", "task", "config", "json", "meta", "context", "outline", "mode"]):
                        files.append(e.name)
            node = {"path": str(path), "name": path.name, "depth": depth, "dirs": dirs[:30], "files": files[:20]}
            tree.append(node)
            total[0] += 1
            for d in dirs:
                if total[0] >= self.max_dirs:
                    break
                child = path / d
                if depth <= 1 or any(k in d.lower() for k in AGENT_DIR_KEYWORDS):
                    _scan(child, depth + 1)
        for root in roots:
            p = Path(root)
            if p.exists():
                _scan(p, 0)
        logger.info(f"目录扫描完成，{len(tree)} 个节点")
        return tree

    def read_dir_details(self, dir_path: str) -> Dict:
        p = Path(dir_path)
        if not p.exists():
            return {"path": dir_path, "exists": False}
        result = {"path": str(p), "name": p.name, "exists": True, "dirs": [], "files": [], "file_contents": {}}
        try:
            for e in p.iterdir():
                if e.name in SKIP_DIRS:
                    continue
                if e.is_dir():
                    result["dirs"].append(e.name)
                elif e.is_file():
                    result["files"].append(e.name)
                    if e.name in PROJECT_MARKERS or e.suffix in (".md", ".json", ".txt", ".yaml"):
                        try:
                            result["file_contents"][e.name] = e.read_text(encoding="utf-8", errors="ignore")[:500]
                        except Exception:
                            pass
        except (PermissionError, OSError):
            pass
        result["dirs"] = result["dirs"][:30]
        result["files"] = result["files"][:30]
        return result

    def discover_agent_dirs(self, tree: List[Dict]) -> List[Dict]:
        if not tree:
            return []
        tree_text = self._tree_to_text(tree)
        system_prompt = "你是AI工具目录识别专家。从目录结构中找出所有可能是AI智能体/编程助手/对话工具的会话目录或工作目录。判断依据：目录名含agent/gpt/claude/cursor/doubao/qwen/马维斯/智能/chat/conversation/ai/llm/workspace等关键词；目录内含conversation.json/agent.json/README.md/.git等特征文件。排除系统目录、缓存目录、纯媒体目录。输出JSON：{\"dirs\":[{\"path\":\"...\",\"reason\":\"...\",\"confidence\":0.0-1.0}]}"
        user_prompt = f"目录结构：\n{tree_text}\n\n找出AI智能体会话目录。"
        try:
            content, _ = self.llm.chat(messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], temperature=0.3, max_tokens=2000)
            return self._parse_discover_result(content)
        except Exception as e:
            logger.error(f"LLM目录发现失败: {e}")
            return []

    def classify_new_dir(self, dir_path: str) -> Tuple[bool, str, float]:
        details = self.read_dir_details(dir_path)
        if not details["exists"]:
            return False, "", 0.0
        details_text = json.dumps(details, ensure_ascii=False, indent=2)[:3000]
        system_prompt = "你是项目识别专家。判断新目录是不是新的AI项目/智能体会话/开发项目，是则提取核心想法。输出JSON：{\"is_project\":true/false,\"idea\":\"一句话\",\"confidence\":0.0-1.0}"
        user_prompt = f"目录详情：\n{details_text}\n\n判断是不是新项目。"
        try:
            content, _ = self.llm.chat(messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], temperature=0.3, max_tokens=800)
            return self._parse_classify_result(content)
        except Exception as e:
            logger.error(f"LLM项目分类失败: {e}")
            return False, "", 0.0

    def _tree_to_text(self, tree: List[Dict]) -> str:
        lines = []
        for node in tree:
            indent = "  " * node["depth"]
            line = f"{indent}[{node['name']}]"
            if node["dirs"]:
                line += f" 子目录: {', '.join(node['dirs'][:10])}"
            if node["files"]:
                line += f" 文件: {', '.join(node['files'][:5])}"
            lines.append(line)
        return "\n".join(lines)[:8000]

    def _parse_discover_result(self, content: str) -> List[Dict]:
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        try:
            start = content.index("{")
            end = content.rindex("}") + 1
            data = json.loads(content[start:end])
            return data.get("dirs", [])
        except (ValueError, json.JSONDecodeError):
            return []

    def _parse_classify_result(self, content: str) -> Tuple[bool, str, float]:
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        try:
            data = json.loads(content)
            return bool(data.get("is_project", False)), str(data.get("idea", "")), float(data.get("confidence", 0.0))
        except json.JSONDecodeError:
            pass
        try:
            start = content.index("{")
            end = content.rindex("}") + 1
            data = json.loads(content[start:end])
            return bool(data.get("is_project", False)), str(data.get("idea", "")), float(data.get("confidence", 0.0))
        except (ValueError, json.JSONDecodeError):
            return False, "", 0.0
