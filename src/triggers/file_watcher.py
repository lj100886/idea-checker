"""文件监控触发器：监控智能体框架的会话目录，检测新项目自动审查"""
import os
import time
import logging
from pathlib import Path
from typing import List, Callable, Optional
from ..config import Config
from ..core.orchestrator import Orchestrator
from ..models import Report
from .llm_discoverer import LLMDiscoverer

logger = logging.getLogger(__name__)


class FileWatcherTrigger:
    """文件监控触发器"""

    PROJECT_MARKERS = ["README.md", "package.json", "pyproject.toml", "requirements.txt", "conversation.json", "agent.json", ".git"]

    def __init__(self, config: Optional[Config] = None, on_review: Optional[Callable[[Report], None]] = None, skip_llm_discover: bool = False):
        self.config = config or Config()
        self.orchestrator = Orchestrator(self.config)
        self.on_review = on_review or self._default_on_review
        self.watch_dirs: List[Path] = []
        self._known_files: set = set()
        self._running = False
        self._llm_discoverer = None
        self._use_llm_classify = False
        self._pending_ideas: dict = {}
        configured_dirs = self.config.get("triggers.file_watcher.watch_dirs", [])
        for d in configured_dirs:
            self.watch_dirs.append(Path(d))
        llm_discover_cfg = self.config.get("triggers.file_watcher.llm_discover", {})
        if not skip_llm_discover and llm_discover_cfg.get("enabled", False):
            self._use_llm_classify = llm_discover_cfg.get("use_llm_classify", True)
            # 安全约束：必须显式配置 scan_roots，禁止默认全量扫描 ~/ 与 D:\
            roots = llm_discover_cfg.get("scan_roots")
            if not roots:
                logger.error(
                    "llm_discover.scan_roots 未配置，拒绝默认全量扫描（会扫 ~/ 与 D:\\，存在隐私外发风险），"
                    "已禁用目录发现。如需启用，请在配置中显式指定 scan_roots（如只指向不含敏感内容的项目目录）。"
                )
                self._llm_discoverer = None
            else:
                try:
                    llm_provider = self.orchestrator.llm_router.api_provider
                    self._llm_discoverer = LLMDiscoverer(llm_provider, llm_discover_cfg)
                    roots = [r for r in roots if Path(r).exists()]
                    logger.info(f"LLM目录发现启动，扫描 {len(roots)} 个根目录")
                    tree = self._llm_discoverer.scan_directory_tree(roots)
                    discovered = self._llm_discoverer.discover_agent_dirs(tree)
                    for item in discovered:
                        p = Path(item.get("path", ""))
                        if p.exists() and p not in self.watch_dirs:
                            self.watch_dirs.append(p)
                            logger.info(f"LLM发现: {p} (置信度 {item.get('confidence', 0):.2f})")
                except Exception as e:
                    logger.error(f"LLM目录发现失败: {e}")
                    self._llm_discoverer = None

    def _default_on_review(self, report: Report):
        from ..core.report_generator import ReportGenerator
        print("\n" + "=" * 60)
        print("检测到新项目，自动审查完成！")
        print("=" * 60)
        print(ReportGenerator.to_text(report))

    def _extract_idea_from_dir(self, dir_path: Path) -> Optional[str]:
        if str(dir_path) in self._pending_ideas:
            idea = self._pending_ideas.pop(str(dir_path))
            if idea:
                return idea
        readme = dir_path / "README.md"
        if readme.exists():
            try:
                content = readme.read_text(encoding="utf-8", errors="ignore")
                return content[:500].strip()
            except Exception:
                pass
        conv = dir_path / "conversation.json"
        if conv.exists():
            try:
                import json
                data = json.loads(conv.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(data, dict) and "messages" in data:
                    for msg in data["messages"]:
                        if msg.get("role") == "user":
                            return msg.get("content", "")[:500]
            except Exception:
                pass
        pkg = dir_path / "package.json"
        if pkg.exists():
            try:
                import json
                data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
                return data.get("name", dir_path.name)
            except Exception:
                pass
        return dir_path.name

    def _is_project_dir(self, dir_path: Path) -> bool:
        for marker in self.PROJECT_MARKERS:
            if (dir_path / marker).exists():
                return True
        return False

    def _scan_new_dirs(self) -> List[Path]:
        new_dirs = []
        for watch_dir in self.watch_dirs:
            if not watch_dir.exists():
                continue
            try:
                for item in watch_dir.iterdir():
                    if item.is_dir() and str(item) not in self._known_files:
                        self._known_files.add(str(item))
                        if self._use_llm_classify and self._llm_discoverer:
                            is_project, idea, confidence = self._llm_discoverer.classify_new_dir(str(item))
                            if is_project and confidence >= 0.5:
                                self._pending_ideas[str(item)] = idea
                                new_dirs.append(item)
                        elif self._is_project_dir(item):
                            new_dirs.append(item)
            except Exception as e:
                logger.warning(f"扫描失败 {watch_dir}: {e}")
        return new_dirs

    def start(self, interval: int = 5):
        if not self.watch_dirs:
            logger.warning("没有监控目录")
            return
        logger.info(f"文件监控启动，{len(self.watch_dirs)} 个目录，每 {interval} 秒扫描")
        self._running = True
        for watch_dir in self.watch_dirs:
            if watch_dir.exists():
                for item in watch_dir.iterdir():
                    self._known_files.add(str(item))
        while self._running:
            try:
                new_dirs = self._scan_new_dirs()
                for new_dir in new_dirs:
                    logger.info(f"检测到新项目: {new_dir}")
                    idea = self._extract_idea_from_dir(new_dir)
                    if idea:
                        try:
                            persona = self.config.get("persona", "default")
                            report = self.orchestrator.check_idea(idea, persona)
                            self.on_review(report)
                        except Exception as e:
                            logger.error(f"审查失败: {e}")
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"监控异常: {e}")
            time.sleep(interval)

    def stop(self):
        self._running = False
