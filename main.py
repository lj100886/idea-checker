#!/usr/bin/env python3
"""idea-checker 入口文件"""
import sys
import logging
import argparse


def _ensure_standard_streams():
    """保证 stdin/stdout/stderr 可用。

    PyInstaller 以 windowed 模式（console=False）打包时，三个标准流会被置为 None，
    此时任何 print()/input()/logging 写流都会抛 `RuntimeError: lost sys.stderr`。
    这里优先附加到父控制台，失败则新建控制台；仍失败则兜底到 devnull，避免崩溃。
    """
    if sys.platform != "win32":
        return
    if sys.stdin is not None and sys.stdout is not None and sys.stderr is not None:
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        if not kernel32.AttachConsole(-1):  # ATTACH_PARENT_PROCESS
            kernel32.AllocConsole()
        sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="replace")
        sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
        sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
    except Exception:
        try:
            import os
            if sys.stdout is None:
                sys.stdout = open(os.devnull, "w", encoding="utf-8")
            if sys.stderr is None:
                sys.stderr = open(os.devnull, "w", encoding="utf-8")
        except Exception:
            pass


# 无控制台构建下先补齐标准流，再做 UTF-8 设置
_ensure_standard_streams()

# Windows控制台UTF-8编码（避免emoji/中文输出崩溃）
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(description="idea-checker: 选题/项目查重AI工具")
    parser.add_argument("idea", nargs="?", help="要审查的想法/项目描述")
    parser.add_argument("-p", "--persona", default="default", help="人设（default/toxic_dev/catgirl/idiot_ai）")
    parser.add_argument("-f", "--format", default="text", choices=["text", "json", "markdown"], help="输出格式")
    parser.add_argument("-w", "--watch", action="store_true", help="启动文件监控模式（监控智能体会话目录）")
    parser.add_argument("--pet", action="store_true", help="启动桌面宠物模式")
    parser.add_argument("--mcp", action="store_true", help="启动MCP服务器模式")
    parser.add_argument("-c", "--config", help="配置文件路径")
    parser.add_argument("--list-personas", action="store_true", help="列出所有人设")
    parser.add_argument("--config-ui", "--gui", action="store_true", help="打开图形化配置界面")

    args = parser.parse_args()

    if args.config_ui:
        from src.ui.config_window import run_config_ui
        run_config_ui(args.config)
        return

    if args.pet:
        from src.ui.pet_window import run_desktop_pet
        run_desktop_pet(args.config)
        return

    if args.mcp:
        from src.triggers.mcp_server import run_mcp_server
        run_mcp_server(args.config)
        return

    if args.watch:
        from src.triggers.file_watcher import FileWatcherTrigger
        from src.config import Config
        config = Config(args.config) if args.config else Config()
        watcher = FileWatcherTrigger(config)
        watcher.start()
        return

    if args.list_personas:
        from src.config import Config
        config = Config(args.config) if args.config else Config()
        print("可用人设：")
        for p in config.list_personas():
            print(f"  - {p}")
        return

    if not args.idea:
        # 交互模式
        print("📋 idea-checker 选题审查工具")
        print("输入你的想法/项目描述，输入 'quit' 退出")
        print()
        from src.config import Config
        from src.core.orchestrator import Orchestrator
        from src.core.report_generator import ReportGenerator
        config = Config(args.config) if args.config else Config()
        orchestrator = Orchestrator(config)

        while True:
            try:
                idea = input("想法> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                break
            if idea.lower() in ("quit", "exit", "q"):
                break
            if not idea:
                continue
            print(f"\n🔍 正在审查...")
            report = orchestrator.check_idea(idea, args.persona)
            if args.format == "json":
                print(ReportGenerator.to_json(report))
            elif args.format == "markdown":
                print(ReportGenerator.to_markdown(report))
            else:
                print(ReportGenerator.to_text(report))
            print()
        return

    # 单次审查
    from src.config import Config
    from src.core.orchestrator import Orchestrator
    from src.core.report_generator import ReportGenerator

    config = Config(args.config) if args.config else Config()
    print(f"🔍 正在审查: {args.idea}")
    print(f"   人设: {args.persona}")
    print()

    orchestrator = Orchestrator(config)
    report = orchestrator.check_idea(args.idea, args.persona)

    if args.format == "json":
        print(ReportGenerator.to_json(report))
    elif args.format == "markdown":
        print(ReportGenerator.to_markdown(report))
    else:
        print(ReportGenerator.to_text(report))


if __name__ == "__main__":
    main()