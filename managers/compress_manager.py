"""
压缩管理器 - 负责对话历史的智能压缩
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from utils.ai_response_util import extract_ai_response
from utils.logger import logger
from managers.ai_manager import ai_manager
from managers.conversation_manager import conversation_manager
from utils.payload_util import generate_payload


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

            # 2. 获取对话元数据
            conv_data = conversation_manager.get_conversation_context(conversation_id)
            if not conv_data:
                logger.error(f"无法获取对话 {conversation_id} 的数据")
                return False

            metadata = conv_data.get("metadata", {})
            ai_uuid = metadata.get("ai")
            prompt_type = metadata.get("prompt", "common")

            if not ai_uuid:
                logger.error(f"对话 {conversation_id} 没有配置AI")
                return False

            # 3. 获取AI配置
            ai_config = ai_manager.get(ai_uuid)
            if not ai_config:
                logger.error(f"AI配置 {ai_uuid} 不存在")
                return False

            # 4. 准备要压缩的消息（除了最近5条）
            if len(tactical_content) <= 5:
                logger.info(f"对话 {conversation_id} 消息太少，跳过压缩")
                return False

            # 保留最近5条，压缩前面的消息
            keep_recent = 5
            messages_to_compress = tactical_content[:-keep_recent]

            if len(messages_to_compress) == 0:
                logger.info(f"没有消息需要压缩")
                return False

            # 5. 准备压缩上下文
            # 获取对话的原始prompt

            # 格式化历史消息
            formatted_history = self._format_messages_for_compression(messages_to_compress)

            # 构建用户消息
            user_message = f"请分析以上对话历史，判断是否适合压缩并生成压缩总结。\n\n对话历史（共{len(messages_to_compress)}条消息）：\n{formatted_history}"

            # 6. 准备工具（只提供no_compress工具）
            compression_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "no_compress",
                        "description": "当对话未完成，不适合压缩时调用",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "reason": {
                                    "type": "string",
                                    "description": "不适合压缩的原因"
                                }
                            },
                            "required": ["reason"]
                        }
                    }
                }
            ]

            # 7. 调用AI进行压缩判断
            logger.info(f"调用AI进行压缩判断，provider: {ai_config['provider']}, model: {ai_config['model']}")

            # 构建payload - 使用相同的prompt_type和ai_uuid
            # device包含"压缩任务"字符串，这会触发payload_util中的压缩逻辑
            payload = generate_payload(
                prompt_type=prompt_type,  # 使用对话的原始prompt_type
                messages=[user_message],
                role="user",
                context=[],  # 不需要额外上下文，因为历史已经在user_message中
                ai=ai_uuid,  # 使用相同的AI配置
                device=f"压缩任务-{conversation_id}",  # 包含"压缩任务"，触发压缩逻辑
                tools=compression_tools
            )

            if not payload:
                logger.error("生成压缩payload失败")
                return False


            # 8. 发送请求
            provider = ai_config.get("provider", "openai")
            response = ai_manager.call_ai(ai_config, payload)

            if not response:
                logger.error("AI压缩调用失败")
                return False

            # 9. 处理响应
            extracted = extract_ai_response(response, provider)

            # 检查是否有工具调用
            if extracted.get("tools") and len(extracted["tools"]) > 0:
                tool_call = extracted["tools"][0]
                if tool_call["function"]["name"] == "no_compress":
                    reason = tool_call["function"]["arguments"]
                    logger.info(f"AI判断不适合压缩: {reason}")
                    return False

            # 10. 获取压缩总结
            compressed_summary = extracted.get("message", "").strip()
            if not compressed_summary:
                logger.warning("AI返回的压缩总结为空")
                return False

            # 11. 调用ConversationManager更新数据
            success = conversation_manager.update_after_compression(
                conversation_id=conversation_id,
                compressed_summary=compressed_summary,
                keep_recent_messages=keep_recent
            )

            if success:
                logger.info(f"对话 {conversation_id} 压缩成功，生成{len(compressed_summary)}字符的总结")
                return True
            else:
                logger.error(f"对话 {conversation_id} 压缩失败")
                return False

        except Exception as e:
            logger.error(f"压缩对话失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _format_messages_for_compression(self, messages: List[Dict]) -> str:
        """格式化消息用于压缩处理"""
        formatted = []

        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # 处理不同角色
            if role == "user":
                formatted.append(f"[用户] {content}")
            elif role == "assistant":
                # 检查是否有工具调用
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    tools_summary = []
                    for tool in tool_calls:
                        func = tool.get("function", {})
                        name = func.get("name", "")
                        args = func.get("arguments", "")
                        try:
                            # 尝试解析JSON参数
                            import json as json_lib
                            args_dict = json_lib.loads(args)
                            args_str = ", ".join([f"{k}={v}" for k, v in args_dict.items()])
                        except:
                            args_str = args
                        tools_summary.append(f"调用工具: {name}({args_str})")

                    tool_text = "；".join(tools_summary)
                    formatted.append(f"[助手] {content if content else '调用工具'}")
                    if tool_text:
                        formatted.append(f"  -> {tool_text}")
                else:
                    formatted.append(f"[助手] {content}")
            elif role == "tool":
                # 对tool返回的内容进行适当处理
                tool_call_id = msg.get("tool_call_id", "unknown")

                # 如果是JSON内容，尝试解析并简化
                if content.startswith("{") and content.endswith("}"):
                    try:
                        import json as json_lib
                        data = json_lib.loads(content)
                        # 简化显示：只显示键名和类型
                        simplified = {k: type(v).__name__ for k, v in data.items()}
                        content_summary = f"返回数据: {simplified}"
                    except:
                        content_summary = "返回数据（格式复杂）"
                else:
                    # 非JSON内容，适当截断
                    if len(content) > 100:
                        content_summary = f"返回内容: {content[:100]}..."
                    else:
                        content_summary = f"返回内容: {content}"

                formatted.append(f"[工具响应 {tool_call_id[:8]}] {content_summary}")

        return "\n".join(formatted)


# 全局实例
compress_manager = CompressManager()