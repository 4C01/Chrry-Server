
from utils.logger import logger


def extract_openai_response(ai_response: dict):
    """
    从OpenAI兼容格式的响应中提取核心数据

    Args:
        ai_response: OpenAI格式的AI响应字典

    Returns:
        提取后的数据:
        {
            "message": "文本内容",              # content
            "tools": [],                       # tool_calls
            "reason": "stop",                  # finish_reason
            "tokens": 100                      # usage.total_tokens
        }
    """
    result = {
        "message": "",      # content -> message
        "tools": [],        # tool_calls -> tools
        "reason": "unknown", # finish_reason -> reason
        "tokens": 0         # usage.total_tokens -> tokens
    }

    try:
        # 1. 检查choices字段
        if "choices" not in ai_response or not ai_response["choices"]:
            logger.warning("AI响应中没有choices字段或为空")
            return result

        choice = ai_response["choices"][0]
        message = choice.get("message", {})

        # 2. 提取message (content)
        result["message"] = message.get("content", "") or ""

        # 3. 提取tools (tool_calls)
        if "tool_calls" in message and message["tool_calls"]:
            result["tools"] = message["tool_calls"]

        # 4. 提取reason (finish_reason)
        result["reason"] = choice.get("finish_reason", "unknown")

        # 5. 提取tokens (usage.total_tokens)
        if "usage" in ai_response:
            usage = ai_response["usage"]
            result["tokens"] = usage.get("total_tokens", 0)

            # 记录到日志
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            logger.info(f"[Token使用] 本次请求: {result['tokens']}总tokens "
                        f"({prompt_tokens}输入 + {completion_tokens}输出)")

        # 6. 记录提取结果到日志
        logger.debug(f"提取AI响应: {len(result['message'])}字符, "
                     f"{len(result['tools'])}个工具调用, "
                     f"原因: {result['reason']}")

    except Exception as e:
        logger.error(f"提取OpenAI响应失败: {e}")
        # 保留原始响应以便调试
        result["_raw"] = ai_response

    logger.debug(f"收到AI回复:{result}")
    return result

def extract_ai_response(ai_response: dict, provider: str):
    response = {}
    if provider in ("openai", "deepseek", "ollama", "siliconflow"):
        response = extract_openai_response(ai_response)

    return response