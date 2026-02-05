from managers.ai_manager import ai_manager
from managers.prompt_manager import prompt_manager


def build_messages(system_prompt: str, context: list, messages: list, role: str, device: str):
    final = []

    if system_prompt:
        final.append({
            "role": "system",
            "content": system_prompt
        })

    final.append({
        "role": "system",
        "content": f"【当前设备】{device}"
    })

    for msg in context:
        final.append({
            "role": msg["role"],
            "content": msg["content"]
        })

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