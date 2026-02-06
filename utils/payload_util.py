from managers.ai_manager import ai_manager
from managers.prompt_manager import prompt_manager
from utils.logger import logger
import time

compression_prompt = """# 对话历史压缩专家

## 你的任务
将提供的对话历史压缩成一个简洁的总结，用于未来的上下文参考。

## 压缩规则
1. 分析对话历史，判断当前对话是否适合压缩：
   - 如果用户和助手正在积极讨论、编写代码、解决问题等未完成的工作，**不适合压缩**
   - 如果对话已经完成一个完整的任务或进入自然停顿，**适合压缩**

2. 压缩内容要求：
   - 如果是完整的对话：用2-3句话总结核心内容
   - 重点记录：用户的意图、助手的关键回复、重要结果/决策
   - 保持时间顺序和逻辑连贯性
   - 如果有工具调用，简要说明工具的作用和结果

3. 工具调用的处理：
   - tool_call的function参数很重要，应该保留或简要说明
   - tool_call的返回内容，如果很关键（如查询结果、数据），简要提及
   - 如果tool_call返回内容只是简单的确认或状态，可以省略

## 输出格式
1. 如果**不适合压缩**：调用no_compress工具
2. 如果**适合压缩**：直接输出压缩总结（纯文本）"""

def build_messages(system_prompt: str, context: list, messages: list, role: str, device: str):
    final = []

    if system_prompt:
        if "压缩任务" in device:
            final.append({
                "role": "system",
                "content": system_prompt + "\n\n" + compression_prompt
            })
        else:
            final.append({
                "role": "system",
                "content": system_prompt
            })

    if "压缩任务" in device:
        final.append({
            "role": "system",
            "content": f"【压缩任务】{device}"
        })
    else:
        final.append({
            "role": "system",
            "content": f"【当前设备】{device}"
        })

    for msg in context:
        message_item = {
            "role": msg["role"],
            "content": msg["content"]
        }

        # 如果是 assistant 且有工具调用
        if msg["role"] == "assistant" and msg.get("tool_calls"):
            message_item["tool_calls"] = msg["tool_calls"]

        # 如果是 tool 消息，必须包含 tool_call_id
        if msg["role"] == "tool" and msg.get("tool_call_id"):
            message_item["tool_call_id"] = msg["tool_call_id"]
        elif msg["role"] == "tool":
            # 如果上下文中没有tool_call_id，添加一个占位符
            message_item["tool_call_id"] = f"call_missing_{int(time.time())}"
            logger.warning(f"上下文中的tool消息缺少tool_call_id，使用占位符: {message_item['tool_call_id']}")
        final.append(message_item)

    for m in messages:
        final.append({
            "role": role,
            "content": m
        })

    return final

def generate_openai_payload(
    prompt_type: str,
    messages: list,
    role: str,
    context: list,
    ai: dict,
    device: str,
    tools
) -> dict:
    """
    生成OpenAI格式的payload
    :param prompt_type: 使用的Prompt的identifier(存储在Prompt里)
    :param messages: 新消息
    :param role: role
    :param context: 上下文
    :param ai: 正在使用的ai的配置文件
    :param device: 正在使用的设备(正在使用的用户)
    :param tools: 可用Tools
    :return:
    """
    system_prompt = prompt_manager.get_full_prompt(prompt_type)

    final_messages = build_messages(
        system_prompt=system_prompt,
        context=context,
        messages=messages,
        role=role,
        device=device
    )

    payload = {
        "model": ai["model"],
        "messages": final_messages,
        "temperature": ai.get("temperature", 0.7),
        "top_p": ai.get("top_p", 1.0),
        "max_tokens": ai.get("max_tokens", 1024),
        "stream": ai.get("stream", False),
    }

    # 检查是否包含"压缩任务"
    if "压缩任务" in device:
        payload["temperature"] = 0.3  # 压缩任务需要更确定性
        payload["max_tokens"] = 1000  # 限制压缩输出的长度

    if tools:
        payload["tools"] = tools
        # 某些模型可能需要显式设置tool_choice为"auto"或"required"
        payload["tool_choice"] = ai.get("tool_choice", "auto")

    # seed 不是所有家都有，但 OpenAI / DeepSeek 支持
    if ai.get("seed") is not None:
        payload["seed"] = ai["seed"]

    return payload

def generate_payload(
            prompt_type,
            messages,
            role,
            context,
            ai,
        device,
    tools = None):
    """
    生成用于AI的json payload
    :param prompt_type: 使用的Prompt的identifier(存储在Prompt里)
    :param messages: 新消息
    :param role: role
    :param context: 上下文
    :param ai: 正在使用的ai的UUID
    :param device: 正在使用的设备
    :param tools: 可用Tools
    :return:
    """
    ai = ai_manager.get(ai)
    payload = {}

    if ai["provider"] in ("openai", "deepseek", "ollama", "siliconflow"):
        payload = generate_openai_payload(
            prompt_type,
            messages,
            role,
            context,
            ai,
            device,
            tools
        )
    return payload