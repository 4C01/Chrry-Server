from managers.ai_manager import ai_manager
from managers.prompt_manager import prompt_manager
from utils.logger import logger
import time

compression_prompt = """# 智能对话压缩器

## 任务
分析对话，智能判断是否适合压缩，生成简洁总结。

## 压缩策略
✅ **立即压缩**（看到这些信号就压缩）：
- 话题明显切换（"对了"、"换个话题"）
- 任务完成（"搞定"、"谢谢"、"明白了"）
- 工作转闲聊（代码写完→聊天气/吃饭）
- 多轮讨论已结束（已给最终方案）

❌ **不压缩**（看到这些就调用no_compress）：
- 正在工作（"调试中"、"让我试试"、"还在"）
- 连续追问中（连续问相关问题的第1-3轮）
- 刚刚得到建议还没回应

## 总结要求
- 1-2句话，30字左右
- 抓核心：做了什么事，得到什么结果
- 重要代码功能、关键决策、工具结果

## 示例
✅ "用户完成了登录模块开发，开始聊周末计划"
✅ "讨论完Python装饰器原理，用户表示感谢"
❌ 不压缩：用户刚收到代码建议，正在尝试

**核心原则**：能压就压，但别压断当前思路！"""

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