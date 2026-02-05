import json
from pathlib import Path
from utils.logger import logger


class AIConfigManager:
    """AI 配置管理器"""

    def __init__(self, config_dir: str = "data"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.ai_file = self.config_dir / "ai.json"
        self.ais = self._load_ai()

    def _load_ai(self) -> dict:
        if not self.ai_file.exists():
            return {}

        try:
            with open(self.ai_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载 AI 配置失败: {e}")
            return {}

    def save(self) -> bool:
        """保存所有AI配置"""
        try:
            with open(self.ai_file, "w", encoding="utf-8") as f:
                json.dump(self.ais, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存 AI 配置失败: {e}")
            return False

    def get(self, uuid: str) -> dict | None:
        """获取AI配置"""
        return self.ais.get(uuid)

    def set(self, uuid: str, config: dict) -> bool:
        self.ais[uuid] = config
        return self.save()

    def list(self) -> dict:
        """列出所有AI配置（返回副本）"""
        return self.ais.copy()

    def delete(self, uuid: str) -> bool:
        """删除指定UUID的AI配置"""
        if uuid not in self.ais:
            logger.warning(f"尝试删除不存在的UUID: {uuid}")
            return False

        del self.ais[uuid]
        return self.save()

ai_manager = AIConfigManager()