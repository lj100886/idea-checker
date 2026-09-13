"""独立配置界面入口：构建为 config-ui.exe（GUI 子系统，双击无黑框直接弹窗）

构建命令示例：
  pyinstaller config_gui_main.py --name config-ui --noconsole --onefile ^
    --hidden-import src.ui.config_window --hidden-import requests ^
    --paths .
"""
import sys

# 顶层导入 PyQt6，确保 PyInstaller 的 hook 收集到 Qt 二进制与插件（如 qwindows.dll）
import PyQt6  # noqa: F401
from src.ui.config_window import run_config_ui

if __name__ == "__main__":
    run_config_ui()
