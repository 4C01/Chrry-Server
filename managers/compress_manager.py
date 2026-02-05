# managers/compress_manager.py
"""
压缩管理器 - 负责对话历史的智能压缩
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from utils.logger import logger


class CompressManager:
    """压缩管理器 - 负责对话历史的智能压缩"""

    def __init__(self, history_dir: str = "data/history"):
        self.history_dir = Path(history_dir)

    def compress(self, conversation_id: str, tactical_content: List[Dict]) -> bool:
        """
        压缩对话历史

        Args:
            conversation_id: 对话ID
            tactical_content: tactical的当前内容

        Returns:
            是否成功压缩（如果用户拒绝压缩，返回False）
        """
        logger.info(f"[CompressManager] 收到压缩请求: {conversation_id}, 消息数: {len(tactical_content)}")

        try:
            # 1. 首先检查是否需要压缩
            if len(tactical_content) <= 10:  # 消息太少，不压缩
                logger.info(f"对话 {conversation_id} 消息太少 ({len(tactical_content)}条)，跳过压缩")
                return False

            # 2. TODO: 这里应该使用conversation里同款AI调用生成summary archive或memory
            # 目前先简单处理：自动压缩

            # 3. 生成压缩摘要
            compressed_summary = self._generate_summary(tactical_content)

            # 4. 调用ConversationManager更新数据
            from .conversation_manager import conversation_manager
            success = conversation_manager.update_after_compression(
                conversation_id=conversation_id,
                compressed_summary=compressed_summary,
                keep_recent_messages=5  # 保留最近5条
            )

            if success:
                logger.info(f"对话 {conversation_id} 压缩成功")
                return True
            else:
                logger.error(f"对话 {conversation_id} 压缩失败")
                return False

        except Exception as e:
            logger.error(f"压缩对话失败: {e}")
            return False

    def _generate_summary(self, messages: List[Dict]) -> str:
        """
        生成对话摘要（简化版）

        TODO: 这里应该调用AI来生成真正的摘要,
        """


        return "summary is null,check coding"


# 全局实例
compress_manager = CompressManager()