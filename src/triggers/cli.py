"""命令行触发器"""
import argparse
import sys
from ..config import Config
from ..core.orchestrator import Orchestrator
from ..core.report_generator import ReportGenerator


def cli_trigger():
    parser = argparse.ArgumentParser(description="idea-checker: 选题/项目查重AI工具")
    parser.add_argument("idea", nargs="?", help="要审查的想法/项目描述")
    parser.add_argument("-p", "--persona", default="default", help="人设")
    parser.add_argument("-f", "--format", default="text", choices=["text", "json", "markdown"], help="输出格式")
    parser.add_argument("-w", "--watch", action="store_true", help="启动文件监控模式")
    parser.add_argument("-c", "--config", help="配置文件路径")
    parser.add_argument("--list-personas", action="store_true", help="列出所有人设")
    args = parser.parse_args()
    config = Config(args.config) if args.config else Config()
    if args.list_personas:
        print("可用人设：")
        for p in config.list_personas():
            print(f"  - {p}")
        return
    if args.watch:
        from .file_watcher import FileWatcherTrigger
        watcher = FileWatcherTrigger(config)
        watcher.start()
        return
    if not args.idea:
        print("idea-checker 选题审查工具")
        print("输入想法，输入 'quit' 退出")
        while True:
            try:
                idea = input("想法> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("再见！")
                break
            if idea.lower() in ("quit", "exit", "q"):
                break
            if not idea:
                continue
            _run_review(idea, args.persona, args.format, config)
        return
    _run_review(args.idea, args.persona, args.format, config)


def _run_review(idea: str, persona: str, fmt: str, config: Config):
    print(f"正在审查: {idea}")
    print(f"人设: {persona}")
    orchestrator = Orchestrator(config)
    report = orchestrator.check_idea(idea, persona)
    if fmt == "json":
        print(ReportGenerator.to_json(report))
    elif fmt == "markdown":
        print(ReportGenerator.to_markdown(report))
    else:
        print(ReportGenerator.to_text(report))
