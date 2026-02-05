import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

from managers.compress_manager import compress_manager
from utils.logger import logger


class ConversationManager:
    """对话管理器 - 负责对话数据的存储和检索"""

    def __init__(self, base_dir: str = "data/history"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # 元数据文件
        self.meta_file = self.base_dir / "data.json"
        self.conversations = self._load_metadata()

    def _load_metadata(self) -> Dict:
        """加载对话元数据"""
        if not self.meta_file.exists():
            return {}

        try:
            with open(self.meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载对话元数据失败: {e}")
            return {}

    def _save_metadata(self) -> bool:
        """保存对话元数据"""
        try:
            with open(self.meta_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversations, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存对话元数据失败: {e}")
            return False

    def create_conversation(
            self,
            name: str,
            prompt_type: str,
            ai_uuid: str,
            device_id: str
    ) -> str:
        """
        创建新对话

        Args:
            name: 对话名称
            prompt_type: 使用的prompt类型
            ai_uuid: 使用的AI配置UUID
            device_id: 设备ID

        Returns:
            新对话的UUID
        """
        conversation_id = str(uuid4())
        conv_dir = self.base_dir / conversation_id
        conv_dir.mkdir(parents=True, exist_ok=True)

        # 初始化三个空文件
        initial_data = []
        for filename in ["tactical.json", "archive.json", "raw_context.json"]:
            filepath = conv_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)

        # 保存元数据
        self.conversations[conversation_id] = {
            "name": name,
            "prompt": prompt_type,
            "ai": ai_uuid,
            "interval": 10,  # 默认10条消息后尝试压缩
            "device": device_id,
            "created": int(time.time()),
            "updated": int(time.time()),
            "message_count": 0,
            "last_compress_attempt": 0  # 上次尝试压缩的时间戳
        }

        self._save_metadata()
        logger.info(f"创建新对话: {name} (ID: {conversation_id})")

        return conversation_id

    def add_message(
            self,
            conversation_id: str,
            role: str,
            content: str,
            tool_calls: Optional[List] = None,
            finish_reason: Optional[str] = None,
            total_tokens: int = 0
    ) -> bool:
        """
        添加一条消息到对话（用户或AI消息）

        Args:
            conversation_id: 对话ID
            role: 消息角色 (user/assistant/system/tool)
            content: 消息内容
            tool_calls: 工具调用列表（仅assistant角色可能有）
            finish_reason: 完成原因（仅assistant角色）
            total_tokens: token使用量（仅assistant角色）

        Returns:
            是否成功
        """
        if conversation_id not in self.conversations:
            logger.error(f"对话不存在: {conversation_id}")
            return False

        conv_dir = self.base_dir / conversation_id
        if not conv_dir.exists():
            logger.error(f"对话目录不存在: {conv_dir}")
            return False

        # 创建消息对象
        message = {
            "role": role,
            "content": content,
            "timestamp": int(time.time())
        }

        # 添加可选字段
        if tool_calls is not None:
            message["tool_calls"] = tool_calls
        if finish_reason is not None:
            message["finish_reason"] = finish_reason
        if total_tokens > 0:
            message["usage"] = {"total_tokens": total_tokens}

        try:
            # 1. 添加到raw_context（完整历史记录）
            self._append_to_file(conv_dir / "raw_context.json", message)

            # 2. 添加到tactical（当前上下文）
            self._append_to_file(conv_dir / "tactical.json", message)

            # 3. 更新元数据：消息计数和更新时间
            self.conversations[conversation_id]["message_count"] += 1
            self.conversations[conversation_id]["updated"] = int(time.time())

            # 4. 检查是否需要尝试压缩
            metadata = self.conversations[conversation_id]

            # interval减1（但不能小于0）
            current_interval = metadata.get("interval", 10)
            if current_interval > 0:
                self.conversations[conversation_id]["interval"] = current_interval - 1
                logger.debug(f"对话 {conversation_id} interval减至: {current_interval - 1}")
            else:
                # interval为0时，尝试压缩
                logger.info(f"对话 {conversation_id} interval为0，触发压缩检查")

                # 获取tactical内容用于压缩
                tactical_file = conv_dir / "tactical.json"
                with open(tactical_file, 'r', encoding='utf-8') as f:
                    tactical_content = json.load(f)

                # 这里调用CompressManager.compress()，先假设存在
                try:
                    compress_success = compress_manager.compress(conversation_id, tactical_content)

                    if compress_success:
                        # 压缩成功，重置interval为10
                        self.conversations[conversation_id]["interval"] = 10
                        self.conversations[conversation_id]["last_compress_attempt"] = int(time.time())
                        logger.info(f"对话 {conversation_id} 压缩成功，interval重置为10")
                    else:
                        # 压缩失败或被拒绝，将interval设为10，避免频繁尝试
                        self.conversations[conversation_id]["interval"] = 10
                        self.conversations[conversation_id]["last_compress_attempt"] = int(time.time())
                        logger.info(f"对话 {conversation_id} 压缩失败或被拒绝，interval重置为10")

                except ImportError:
                    # CompressManager还没实现，暂时跳过
                    logger.warning(f"CompressManager未实现，跳过压缩检查")
                    # 即使没有CompressManager，也重置interval避免无限循环
                    self.conversations[conversation_id]["interval"] = 10

            # 5. 保存元数据
            self._save_metadata()

            logger.debug(
                f"对话 {conversation_id} 添加{role}消息，当前interval: {self.conversations[conversation_id]['interval']}")
            return True

        except Exception as e:
            logger.error(f"添加消息失败: {e}")
            return False

    def _append_to_file(self, filepath: Path, data: Dict, max_items: int = 0):
        """向JSON文件追加数据"""
        existing_data = []
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

        existing_data.append(data)

        # 如果设置了最大数量，只保留最新的（tactical可能需要这个限制）
        if max_items > 0 and len(existing_data) > max_items:
            existing_data = existing_data[-max_items:]

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

    def get_context_for_ai(self, conversation_id: str) -> List[Dict]:
        """
        获取用于AI调用的上下文

        规则：archive的后8条 + tactical的全部

        Args:
            conversation_id: 对话ID

        Returns:
            组合后的消息列表
        """
        if conversation_id not in self.conversations:
            return []

        conv_dir = self.base_dir / conversation_id
        if not conv_dir.exists():
            return []

        try:
            # 1. 读取archive（压缩记忆）
            archive_file = conv_dir / "archive.json"
            archive = []
            if archive_file.exists():
                with open(archive_file, 'r', encoding='utf-8') as f:
                    archive = json.load(f)

            # 2. 读取tactical（当前上下文）
            tactical_file = conv_dir / "tactical.json"
            tactical = []
            if tactical_file.exists():
                with open(tactical_file, 'r', encoding='utf-8') as f:
                    tactical = json.load(f)

            # 3. 合并：archive后8条 + tactical全部
            memory = archive[-8:] if len(archive) >= 8 else archive
            combined_context = memory + tactical

            logger.debug(f"为对话 {conversation_id} 准备上下文: {len(memory)}记忆 + {len(tactical)}当前")
            return combined_context

        except Exception as e:
            logger.error(f"获取上下文失败: {e}")
            return []

    def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """
        获取对话的完整上下文数据

        Returns:
            {
                "metadata": {...},      # 对话元数据
                "tactical": [...],      # 当前上下文
                "archive": [...],       # 压缩记忆
                "raw_context": [...]    # 完整历史
            }
        """
        if conversation_id not in self.conversations:
            return {}

        conv_dir = self.base_dir / conversation_id
        if not conv_dir.exists():
            return {}

        context = {"metadata": self.conversations[conversation_id]}

        for filename in ["tactical", "archive", "raw_context"]:
            filepath = conv_dir / f"{filename}.json"
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    context[filename] = json.load(f)
            else:
                context[filename] = []

        return context

    def get_tactical_content(self, conversation_id: str) -> List[Dict]:
        """获取tactical内容（用于压缩）"""
        if conversation_id not in self.conversations:
            return []

        conv_dir = self.base_dir / conversation_id
        tactical_file = conv_dir / "tactical.json"

        if not tactical_file.exists():
            return []

        try:
            with open(tactical_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取tactical失败: {e}")
            return []

    def update_after_compression(
            self,
            conversation_id: str,
            compressed_summary: str,
            keep_recent_messages: int = 5
    ) -> bool:
        """
        压缩后更新对话数据

        Args:
            conversation_id: 对话ID
            compressed_summary: 压缩后的摘要内容
            keep_recent_messages: 保留最近的消息条数

        Returns:
            是否成功
        """
        if conversation_id not in self.conversations:
            return False

        conv_dir = self.base_dir / conversation_id
        if not conv_dir.exists():
            return False

        try:
            # 1. 读取当前tactical
            tactical_file = conv_dir / "tactical.json"
            tactical = []
            if tactical_file.exists():
                with open(tactical_file, 'r', encoding='utf-8') as f:
                    tactical = json.load(f)

            if len(tactical) <= keep_recent_messages:
                # 消息太少，不需要压缩，但还是重置interval
                logger.info(f"对话 {conversation_id} 消息太少 ({len(tactical)}条)，跳过压缩")
                return True

            # 2. 保留最近的消息，压缩之前的消息
            to_keep = tactical[-keep_recent_messages:]  # 保留最近的N条
            to_compress = tactical[:-keep_recent_messages]  # 压缩之前的

            # 3. 将压缩摘要添加到archive
            archive_file = conv_dir / "archive.json"
            archive = []
            if archive_file.exists():
                with open(archive_file, 'r', encoding='utf-8') as f:
                    archive = json.load(f)

            archive.append({
                "type": "compressed",
                "content": compressed_summary,
                "original_count": len(to_compress),
                "timestamp": int(time.time())
            })

            # 保存archive
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(archive, f, ensure_ascii=False, indent=2)

            # 4. 更新tactical为保留的消息
            with open(tactical_file, 'w', encoding='utf-8') as f:
                json.dump(to_keep, f, ensure_ascii=False, indent=2)

            # 5. 记录日志
            logger.info(
                f"对话 {conversation_id} 压缩完成: {len(to_compress)}条消息压缩为1条摘要，保留{len(to_keep)}条消息")

            return True

        except Exception as e:
            logger.error(f"压缩后更新失败: {e}")
            return False

    def list_conversations(self, device_id: Optional[str] = None) -> Dict:
        """列出对话列表"""
        if device_id:
            return {
                conv_id: meta
                for conv_id, meta in self.conversations.items()
                if meta.get("device") == device_id
            }
        return self.conversations.copy()

    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        if conversation_id not in self.conversations:
            return False

        # 删除文件夹
        conv_dir = self.base_dir / conversation_id
        if conv_dir.exists():
            import shutil
            try:
                shutil.rmtree(conv_dir)
            except Exception as e:
                logger.error(f"删除对话目录失败: {e}")
                return False

        # 删除元数据
        del self.conversations[conversation_id]
        return self._save_metadata()


# 全局实例
conversation_manager = ConversationManager()