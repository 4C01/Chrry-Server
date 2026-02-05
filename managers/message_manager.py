import requests
from typing import Dict, Optional, Any

from utils.ai_response_util import extract_ai_response
from utils.logger import logger
from utils.payload_util import generate_payload

from .conversation_manager import conversation_manager
from .ai_manager import ai_manager



class MessageManager:
    """消息管理器 - 只协调消息处理流程"""

    def __init__(self):
        pass  # 不存储状态，只调用其他模块

    def process_message(self, data: Dict) -> Dict[str, Any]:
        """
        处理一条消息的完整流程

        Args:
            data: {
                "conversation": "对话UUID",
                "device": "设备标识",
                "message": "用户消息内容",  # 字符串
                "tool_response": {  # 可选
                    "tool_call_id": "call_123",
                    "content": "工具执行结果JSON"
                },
                "tools": [...]  # 可选，本次可用的工具列表
            }

        Returns:
            {
                "success": True/False,
                "response": {  # 只有AI的回复
                    "content": "文本内容",
                    "tool_calls": [],  # 如果有工具调用
                    "finish_reason": "stop"
                },
                "error": "错误信息（如果失败）"
            }
        """
        try:
            logger.info(f"处理消息: conversation={data.get('conversation')}")

            # 1. 验证必需字段
            conversation = data.get("conversation")
            device = data.get("device")
            message = data.get("message")

            if not conversation or not device:
                return self._error("缺少conversation或device")

            # 2. 获取对话上下文
            context_data = conversation_manager.get_conversation_context(conversation)
            if not context_data:
                return self._error(f"对话不存在: {conversation}")

            metadata = context_data["metadata"]

            # 3. 处理工具响应（如果有）
            tool_response = data.get("tool_response")
            if tool_response:
                # 保存为role: "tool"的消息
                success = conversation_manager.add_message(
                    conversation_id=conversation,
                    role="tool",
                    content=tool_response.get("content", "")
                )
                if not success:
                    logger.warning(f"保存tool_response失败: {tool_response}")

            # 4. 保存用户消息（如果有文本内容）
            if message and isinstance(message, str) and message.strip():
                success = conversation_manager.add_message(
                    conversation_id=conversation,
                    role="user",
                    content=message
                )
                if not success:
                    return self._error("保存用户消息失败")

            # 5. 获取AI配置
            ai_config = ai_manager.get(metadata["ai"])
            if not ai_config:
                return self._error(f"AI配置不存在: {metadata['ai']}")

            provider = ai_config.get("provider", "openai")

            # 6. 获取用于AI的上下文（包含所有历史消息，包括刚添加的tool_response）
            ai_context = conversation_manager.get_context_for_ai(conversation)

            # 7. 生成payload
            tools = data.get("tools")
            payload = generate_payload(
                prompt_type=metadata["prompt"],
                messages=[message] if isinstance(message, str) and message.strip() else [],
                role="user",
                context=ai_context,
                ai=metadata["ai"],
                device=device,
                tools=tools
            )

            if not payload:
                return self._error("生成请求参数失败")

            # 8. 调用AI服务
            ai_response = self._call_ai(ai_config, payload)
            if not ai_response:
                return self._error("AI服务无响应")

            # 9. 提取AI响应
            extracted = extract_ai_response(ai_response, provider)
            if not extracted:
                return self._error("解析AI响应失败")

            # 10. 保存AI回复
            success = conversation_manager.add_message(
                conversation_id=conversation,
                role="assistant",
                content=extracted.get("message", ""),
                tool_calls=extracted.get("tools", []),
                finish_reason=extracted.get("reason"),
                total_tokens=extracted.get("tokens", 0)
            )

            if not success:
                logger.warning("保存AI回复失败，但继续返回响应")

            # 11. 返回给客户端
            return self._success({
                "content": extracted.get("message", ""),
                "tool_calls": extracted.get("tools", []),
                "finish_reason": extracted.get("reason", "unknown")
            })

        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
            return self._error(f"服务器错误: {str(e)}")

    def _call_ai(self, ai_config: Dict, payload: Dict) -> Optional[Dict]:
        """调用AI服务"""
        try:
            provider = ai_config.get("provider", "openai")
            base_url = ai_config.get("base_url", "https://api.openai.com/v1")
            api_key = ai_config.get("api_key", "")

            # 设置endpoint
            if provider == "ollama":
                endpoint = "/api/chat"
                if "localhost" not in base_url:
                    base_url = "http://localhost:11434"
            else:
                endpoint = "/chat/completions"

            url = f"{base_url.rstrip('/')}{endpoint}"

            headers = {"Content-Type": "application/json"}
            if provider != "ollama":
                headers["Authorization"] = f"Bearer {api_key}"

            # 设置超时
            timeout = ai_config.get("timeout", 30)

            logger.debug(f"发送请求到: {url}")

            response = requests.post(url, headers=headers, json=payload, timeout=timeout)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"AI请求失败 {response.status_code}: {response.text[:200]}")
                return None

        except Exception as e:
            logger.error(f"调用AI失败: {e}")
            return None

    def _success(self, response_data: Dict) -> Dict[str, Any]:
        """成功响应"""
        return {
            "success": True,
            "response": response_data,
            "error": None
        }

    def _error(self, message: str) -> Dict[str, Any]:
        """错误响应"""
        return {
            "success": False,
            "response": None,
            "error": message
        }


# 全局实例
message_manager = MessageManager()