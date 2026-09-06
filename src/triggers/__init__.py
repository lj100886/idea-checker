"""触发器模块"""
from .file_watcher import FileWatcherTrigger
from .cli import cli_trigger

__all__ = ["FileWatcherTrigger", "cli_trigger"]
