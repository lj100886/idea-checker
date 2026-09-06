"""提示词管理器"""
import yaml
from pathlib import Path
from typing import Optional


class PromptManager:
    """管理所有系统提示词，支持版本化"""

    def __init__(self, prompts_dir: Optional[str] = None):
        if prompts_dir:
            self.prompts_dir = Path(prompts_dir)
        else:
            self.prompts_dir = Path(__file__).parent.parent.parent / "config" / "prompts"

    def get_prompt(self, scene: str, version: str = "v1") -> str:
        prompt_file = self.prompts_dir / f"{scene}_{version}.yaml"
        if not prompt_file.exists():
            candidates = list(self.prompts_dir.glob(f"{scene}_*.yaml"))
            if candidates:
                prompt_file = candidates[0]
            else:
                return ""
        with open(prompt_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("system_prompt", "")

    def list_scenes(self) -> list:
        scenes = set()
        for f in self.prompts_dir.glob("*.yaml"):
            name = f.stem
            if "_" in name:
                scenes.add(name.rsplit("_", 1)[0])
        return sorted(scenes)
