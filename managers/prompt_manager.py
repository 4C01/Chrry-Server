import json
import time
from pathlib import Path

from utils.logger import logger


class PromptManager:
    """Prompt管理器"""

    def __init__(self, config_dir: str = "data"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.prompts_file = self.config_dir / "prompts.json"
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> dict:
        """加载prompts"""
        if not self.prompts_file.exists():
            return {"common": {"prompt": "You are a helpful AI assistant."}}

        try:
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载prompts失败: {e}")
            return {"common": {"prompt": "You are a helpful AI assistant."}}

    def _save_prompts(self) -> bool:
        """保存prompts"""
        try:
            with open(self.prompts_file, 'w', encoding='utf-8') as f:
                json.dump(self.prompts, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存prompts失败: {e}")
            return False

    def set_common(self, prompt: str) -> bool:
        """设置common prompt"""
        if "common" not in self.prompts:
            self.prompts["common"] = {}

        self.prompts["common"]["prompt"] = prompt
        self.prompts["common"]["updated"] = int(time.time())
        return self._save_prompts()

    def set_prompt(self, name: str, prompt: str) -> bool:
        """设置prompt"""
        if name not in self.prompts:
            self.prompts[name] = {}
            self.prompts[name]["created"] = int(time.time())

        self.prompts[name]["prompt"] = prompt
        self.prompts[name]["updated"] = int(time.time())
        return self._save_prompts()

    def get_prompt(self, name: str) -> str:
        """获取prompt"""
        if name in self.prompts and "prompt" in self.prompts[name]:
            return self.prompts[name]["prompt"]
        return ""

    def get_full_prompt(self, prompt_type: str) -> str:
        """获取完整prompt（common + 指定类型）"""
        common = self.get_prompt("common")
        specific = self.get_prompt(prompt_type)

        if not specific:
            return common

        return f"{common}\n\n{specific}"

    def list_prompts(self) -> dict:
        """列出所有prompts（不包含common）"""

        result = self.prompts.copy()
        if "common" in result:
            del result["common"]

        return result

    def delete_prompt(self, name: str) -> bool:
        """删除prompt（不能删common）"""
        if name == "common" or name not in self.prompts:
            return False

        del self.prompts[name]
        return self._save_prompts()

prompt_manager = PromptManager()