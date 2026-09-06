"""配置管理"""
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class Config:
    """配置管理器：支持配置文件 + 环境变量"""

    DEFAULT_CONFIG = {
        "llm": {
            "mode": "api",
            "api": {
                "base_url": "https://api.siliconflow.cn/v1",
                "api_key": "",
                "model": "Qwen/Qwen3-8B",
                "timeout": 30,
                "max_retries": 2,
            },
            "agent_framework": {
                "type": "auto",
                "endpoint": "",
                "api_key": "",
            },
        },
        "search": {
            "sources": ["github", "aihot"],
            "github": {
                "token": "",
                "max_results": 10,
            },
            "aihot": {
                "endpoint": "https://aihot.virxact.com/api/mcp?aihot_actor=YOUR_AIHOT_ACTOR_TOKEN",
                "max_results": 10,
            },
        },
        "review": {
            "max_rounds": 5,
            "confidence_threshold": 0.7,
            "min_rounds": 1,
            "timeout_seconds": 300,
        },
        "persona": "default",
        "triggers": {
            "file_watcher": {
                "enabled": True,
                "watch_dirs": [],
                "patterns": ["README.md", "package.json", "*.py", "conversation.json", "*.md"],
            },
            "desktop_pet": {
                "enabled": True,
                "image_path": "",
                "swing_speed": 1000,
            },
        },
        "output": {
            "notify": True,
            "save_to_file": True,
            "output_dir": "./reports",
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else Path.home() / ".idea-checker" / "config.json"
        self._config = self._load()

    def _load(self) -> Dict[str, Any]:
        config = self.DEFAULT_CONFIG.copy()
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8-sig") as f:
                    user_config = json.load(f)
                config = self._deep_merge(config, user_config)
            except Exception as e:
                print(f"[Config] 加载配置文件失败: {e}，使用默认配置")
        env_key = os.getenv("IDEA_CHECKER_LLM_API_KEY")
        if env_key:
            config["llm"]["api"]["api_key"] = env_key
        return config

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def get_persona(self, name: str) -> str:
        persona_file = Path(__file__).parent.parent / "config" / "personas" / f"{name}.yaml"
        if persona_file.exists():
            import yaml
            with open(persona_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("system_prompt", "")
        return ""

    def list_personas(self) -> List[str]:
        persona_dir = Path(__file__).parent.parent / "config" / "personas"
        if not persona_dir.exists():
            return []
        return [f.stem for f in persona_dir.glob("*.yaml")]

    def get_prompt(self, scene: str, version: str = "v1") -> str:
        prompt_file = Path(__file__).parent.parent / "config" / "prompts" / f"{scene}_{version}.yaml"
        if prompt_file.exists():
            import yaml
            with open(prompt_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("system_prompt", "")
        return ""
