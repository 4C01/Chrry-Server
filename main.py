from flask import Flask, request, jsonify
from functools import wraps

from managers.ai_manager import ai_manager
from managers.prompt_manager import prompt_manager
from managers.conversation_manager import conversation_manager
from managers.message_manager import message_manager
from utils.api_key_util import key_manager
from utils.response_utils import ResponseUtil
from utils.logger import logger

app = Flask(__name__)


# API密钥验证装饰器
def require_api_key(func):
    """API密钥验证装饰器 - 同时支持Header和Query参数"""

    @wraps(func)
    def decorated_function(*args, **kwargs):
        # 优先级：Header > Query参数
        api_key = (
                request.headers.get('X-API-Key') or
                request.args.get('key') or
                request.args.get('api_key')
        )

        if not api_key:
            logger.warning("API请求缺少密钥")
            return ResponseUtil.error(403)

        if not key_manager.validate(api_key):
            logger.warning(f"API密钥验证失败: {api_key[:8]}...")
            return ResponseUtil.error(403)

        logger.info(f"API密钥验证成功: {api_key[:8]}...")
        return func(*args, **kwargs)

    return decorated_function


# ==================== Prompt相关路由 ====================

@app.route('/v1/prompt/set', methods=['POST'])
@require_api_key
def set_prompt():
    """
    创建或更新提示词
    """
    try:
        data = request.get_json()
        if not data:
            return ResponseUtil.error(400, "请求体不能为空")

        name = data.get('name')
        value = data.get('value')

        if not name or not value:
            return ResponseUtil.error(400, "name和value字段不能为空")

        success = prompt_manager.set_prompt(name, value)

        if success:
            return ResponseUtil.success({"message": "提示词设置成功", "name": name})
        else:
            return ResponseUtil.error(500, "保存提示词失败")

    except Exception as e:
        logger.error(f"设置提示词失败: {e}")
        return ResponseUtil.error(500, str(e))


@app.route('/v1/prompt/create', methods=['POST'])
@require_api_key
def create_prompt():
    """
    创建新的提示词（不允许覆盖已存在的）
    """
    try:
        data = request.get_json()
        if not data:
            return ResponseUtil.error(400, "请求体不能为空")

        name = data.get('name')
        value = data.get('value')

        if not name or not value:
            return ResponseUtil.error(400, "name和value字段不能为空")

        existing = prompt_manager.get_prompt(name)
        if existing:
            return ResponseUtil.error(400, f"提示词 '{name}' 已存在")

        success = prompt_manager.set_prompt(name, value)

        if success:
            return ResponseUtil.success({"message": "提示词创建成功", "name": name}, 201)
        else:
            return ResponseUtil.error(500, "创建提示词失败")

    except Exception as e:
        logger.error(f"创建提示词失败: {e}")
        return ResponseUtil.error(500, str(e))


@app.route('/v1/prompt/get', methods=['GET', 'POST'])
@require_api_key
def get_prompt():
    """
    获取提示词
    """
    try:
        if request.method == 'GET':
            name = request.args.get('name')
        else:
            data = request.get_json() or {}
            name = data.get('name')

        if not name:
            return ResponseUtil.error(400, "name参数不能为空")

        prompt_value = prompt_manager.get_prompt(name)

        if not prompt_value:
            return ResponseUtil.error(404, f"提示词 '{name}' 不存在")

        return ResponseUtil.success({
            "name": name,
            "value": prompt_value
        })

    except Exception as e:
        logger.error(f"获取提示词失败: {e}")
        return ResponseUtil.error(500, str(e))


@app.route('/v1/prompt/list', methods=['GET'])
@require_api_key
def list_prompts():
    """
    列出所有提示词
    """
    try:
        prompts = prompt_manager.list_prompts()

        formatted_prompts = {}
        for name, data in prompts.items():
            formatted_prompts[name] = data.get("prompt", "")

        return ResponseUtil.success(formatted_prompts)

    except Exception as e:
        logger.error(f"列出提示词失败: {e}")
        return ResponseUtil.error(500, str(e))


# ==================== AI配置相关路由 ====================

@app.route('/v1/ai/list', methods=['GET'])
@require_api_key
def list_ais():
    """
    列出所有AI配置
    """
    try:
        ais = ai_manager.list()
        return ResponseUtil.success(ais)
    except Exception as e:
        logger.error(f"列出AI配置失败: {e}")
        return ResponseUtil.error(500, str(e))


@app.route('/v1/ai/get', methods=['GET'])
@require_api_key
def get_ai():
    """
    获取单个AI配置
    """
    try:
        uuid = request.args.get('uuid')
        if not uuid:
            return ResponseUtil.error(400, "uuid参数不能为空")

        ai_config = ai_manager.get(uuid)
        if not ai_config:
            return ResponseUtil.error(404, f"AI配置 '{uuid}' 不存在")

        return ResponseUtil.success(ai_config)
    except Exception as e:
        logger.error(f"获取AI配置失败: {e}")
        return ResponseUtil.error(500, str(e))


@app.route('/v1/ai/set', methods=['POST'])
@require_api_key
def set_ai():
    """
    设置AI配置
    """
    try:
        data = request.get_json()
        if not data:
            return ResponseUtil.error(400, "请求体不能为空")

        uuid = data.get('uuid')
        config = data.get('config')

        if not uuid or not config:
            return ResponseUtil.error(400, "uuid和config字段不能为空")

        required_fields = ['name', 'api_key', 'provider', 'model']
        for field in required_fields:
            if field not in config:
                return ResponseUtil.error(400, f"config中缺少必要字段: {field}")

        success = ai_manager.set(uuid, config)

        if success:
            return ResponseUtil.success({"message": "AI配置设置成功", "uuid": uuid})
        else:
            return ResponseUtil.error(500, "保存AI配置失败")

    except Exception as e:
        logger.error(f"设置AI配置失败: {e}")
        return ResponseUtil.error(500, str(e))


@app.route('/v1/ai/delete', methods=['POST'])
@require_api_key
def delete_ai():
    """
    删除AI配置
    """
    try:
        data = request.get_json()
        if not data:
            return ResponseUtil.error(400, "请求体不能为空")

        uuid = data.get('uuid')
        if not uuid:
            return ResponseUtil.error(400, "uuid字段不能为空")

        success = ai_manager.delete(uuid)

        if success:
            return ResponseUtil.success({"message": "AI配置删除成功", "uuid": uuid})
        else:
            return ResponseUtil.error(404, f"AI配置 '{uuid}' 不存在或删除失败")

    except Exception as e:
        logger.error(f"删除AI配置失败: {e}")
        return ResponseUtil.error(500, str(e))


# ==================== 聊天对话相关路由 ====================

@app.route('/v1/chat/send', methods=['POST'])
@require_api_key
def send_chat():
    """
    发送聊天消息
    POST /v1/chat/send
    {
        "conversation": "对话UUID",
        "device": "设备标识",
        "message": "用户消息内容",
        "tool_response": {
            "tool_call_id": "call_123",
            "content": "工具执行结果JSON"
        },
        "tools": [...]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return ResponseUtil.error(400, "请求体不能为空")

        # 必需字段验证
        conversation = data.get('conversation')
        device = data.get('device')

        if not conversation or not device:
            return ResponseUtil.error(400, "conversation和device字段不能为空")

        # 调用消息管理器处理
        result = message_manager.process_message(data)

        if result.get('success'):
            return ResponseUtil.success(result.get('response'))
        else:
            return ResponseUtil.error(500, result.get('error', '未知错误'))

    except Exception as e:
        logger.error(f"发送聊天消息失败: {e}")
        return ResponseUtil.error(500, str(e))


@app.route('/v1/chat/list', methods=['GET'])
@require_api_key
def list_chats():
    """
    列出所有聊天会话
    GET /v1/chat/list?device=xxx
    """
    try:
        device_id = request.args.get('device')

        conversations = conversation_manager.list_conversations(device_id)
        return ResponseUtil.success(conversations)

    except Exception as e:
        logger.error(f"列出聊天会话失败: {e}")
        return ResponseUtil.error(500, str(e))


@app.route('/v1/history/get', methods=['GET', 'POST'])
@require_api_key
def get_history():
    """
    获取聊天历史
    GET /v1/history/get?uuid=xxx&tactical=false&lines=20
    POST /v1/history/get
    {
        "uuid": "对话UUID",
        "tactical": false,
        "lines": 20
    }
    """
    try:
        if request.method == 'GET':
            uuid = request.args.get('uuid')
            tactical = request.args.get('tactical', 'false').lower() == 'true'
            lines = request.args.get('lines', type=int)
        else:
            data = request.get_json() or {}
            uuid = data.get('uuid')
            tactical = data.get('tactical', False)
            lines = data.get('lines')

        if not uuid:
            return ResponseUtil.error(400, "uuid参数不能为空")

        # 获取对话上下文
        context_data = conversation_manager.get_conversation_context(uuid)
        if not context_data:
            return ResponseUtil.error(404, f"对话 '{uuid}' 不存在")

        response_data = {
            "metadata": context_data["metadata"],
            "tactical": context_data.get("tactical", []),
            "archive": context_data.get("archive", []),
            "raw_context": context_data.get("raw_context", [])
        }

        # 如果指定了lines，只返回最近lines条
        if lines and lines > 0:
            response_data["tactical"] = response_data["tactical"][-lines:]
            response_data["raw_context"] = response_data["raw_context"][-lines:]

        # 如果只需要tactical
        if tactical:
            return ResponseUtil.success({
                "tactical": response_data["tactical"],
                "message_count": context_data["metadata"].get("message_count", 0)
            })

        return ResponseUtil.success(response_data)

    except Exception as e:
        logger.error(f"获取聊天历史失败: {e}")
        return ResponseUtil.error(500, str(e))


@app.route('/v1/history/memory', methods=['GET'])
@require_api_key
def get_memory():
    """
    获取记忆列表（archive内容）
    GET /v1/history/memory?uuid=xxx
    """
    try:
        uuid = request.args.get('uuid')
        if not uuid:
            return ResponseUtil.error(400, "uuid参数不能为空")

        context_data = conversation_manager.get_conversation_context(uuid)
        if not context_data:
            return ResponseUtil.error(404, f"对话 '{uuid}' 不存在")

        archive = context_data.get("archive", [])

        # 提取压缩记忆的内容
        memories = []
        for item in archive:
            if isinstance(item, dict) and item.get("type") == "compressed":
                memories.append(item.get("content", ""))

        return ResponseUtil.success({
            "memories": memories,
            "count": len(memories)
        })

    except Exception as e:
        logger.error(f"获取记忆列表失败: {e}")
        return ResponseUtil.error(500, str(e))


@app.route('/v1/create', methods=['POST'])
@require_api_key
def create_chat():
    """
    创建新的聊天会话
    POST /v1/create
    {
        "name": "对话名称",
        "prompt": "提示词类型",
        "ai": "AI配置UUID",
        "device": "设备ID"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return ResponseUtil.error(400, "请求体不能为空")

        name = data.get('name')
        prompt_type = data.get('prompt')
        ai_uuid = data.get('ai')
        device_id = data.get('device')

        if not name or not prompt_type or not ai_uuid or not device_id:
            return ResponseUtil.error(400, "name、prompt、ai、device字段不能为空")

        # 验证AI配置存在
        ai_config = ai_manager.get(ai_uuid)
        if not ai_config:
            return ResponseUtil.error(404, f"AI配置 '{ai_uuid}' 不存在")

        # 验证提示词存在
        prompt_value = prompt_manager.get_prompt(prompt_type)
        if not prompt_value:
            return ResponseUtil.error(404, f"提示词 '{prompt_type}' 不存在")

        # 创建对话
        conversation_id = conversation_manager.create_conversation(
            name=name,
            prompt_type=prompt_type,
            ai_uuid=ai_uuid,
            device_id=device_id
        )

        return ResponseUtil.success({
            "conversation_id": conversation_id,
            "name": name,
            "message": "对话创建成功"
        }, 201)

    except Exception as e:
        logger.error(f"创建聊天会话失败: {e}")
        return ResponseUtil.error(500, str(e))


@app.route('/v1/delete', methods=['POST'])
@require_api_key
def delete_chat():
    """
    删除聊天会话
    POST /v1/delete
    {
        "uuid": "对话UUID"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return ResponseUtil.error(400, "请求体不能为空")

        uuid = data.get('uuid')
        if not uuid:
            return ResponseUtil.error(400, "uuid字段不能为空")

        success = conversation_manager.delete_conversation(uuid)

        if success:
            return ResponseUtil.success({"message": "对话删除成功", "uuid": uuid})
        else:
            return ResponseUtil.error(404, f"对话 '{uuid}' 不存在或删除失败")

    except Exception as e:
        logger.error(f"删除聊天会话失败: {e}")
        return ResponseUtil.error(500, str(e))


# ==================== 健康检查 ====================

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "version": "v1.0.0"
    })


if __name__ == '__main__':
    import time

    app.run(debug=True, port=5000)