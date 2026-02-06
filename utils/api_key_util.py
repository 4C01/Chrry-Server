import uuid
import json
from pathlib import Path

from utils.logger import logger


class ApiKeyManager:
    """API密钥管理器"""

    def __init__(self, key_file: str = "data/api_key.json"):
        self.key_file = Path(key_file)
        self.key: str = ""
        self._load_or_create()

    def _load_or_create(self):
        """加载或创建API密钥"""
        try:
            if self.key_file.exists():
                with open(self.key_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.key = data.get('api_key', '')

                if self.key:
                    logger.info(f"已加载API密钥: {self.key[:8]}...")
                else:
                    logger.warning("密钥文件格式错误，重新生成")
                    self._generate_key()
            else:
                self._generate_key()

        except Exception as e:
            logger.error(f"加载密钥失败: {e}")
            self._generate_key()

    def _generate_key(self):
        """生成新密钥"""
        self.key = str(uuid.uuid4())
        data = {
            "api_key": self.key
        }

        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.key_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        logger.info(f" 新API密钥已生成: {self.key},保存至data/api_key.json")
        logger.info(" 使用示例:")
        logger.info(f"   curl -H 'X-API-Key: {self.key}' http://localhost:5000/health")
        logger.info(f"   或 curl 'http://localhost:5000/health?key={self.key}'")

    def validate(self, provided_key: str) -> bool:
        """验证API密钥"""
        if not provided_key:
            return False
        return uuid.UUID(provided_key) == uuid.UUID(self.key)


# 全局密钥管理器实例
key_manager = ApiKeyManager()