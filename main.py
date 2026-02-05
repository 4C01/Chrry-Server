from flask import Flask, request
from functools import wraps

from managers.ai_manager import ai_manager
from managers.prompt_manager import prompt_manager
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


@app.route('/v1/prompt/set', methods=['POST'])
@require_api_key
def set_prompt():
    """
    创建或更新提示词
    POST /v1/prompt/set
    {
        "name": "weather",
        "value": "你是一个天气助手..."
    }
    """
    try:
        data = request.get_json()
        if not data:
            return ResponseUtil.error(400, "请求体不能为空")

        name = data.get('name')
        value = data.get('value')

        if not name or not value:
            return ResponseUtil.error(400, "name和value字段不能为空")

        # 调用PromptManager
        success = prompt_manager.set_prompt(name, value)

        if success:
            return ResponseUtil.success({"message": "提示词设置成功", "name": name})
        else:
            return ResponseUtil.error(500, "保存提示词失败")

    except Exception as e:
        logger.error(f"设置提示词失败: {e}")
        return ResponseUtil.error(500, str(e))


# 创建新的Prompt（不允许覆盖）
@app.route('/v1/prompt/create', methods=['POST'])
@require_api_key
def create_prompt():
    """
    创建新的提示词（不允许覆盖已存在的）
    POST /v1/prompt/create
    {
        "name": "weather",
        "value": "你是一个天气助手..."
    }
    """
    try:
        data = request.get_json()
        if not data:
            return ResponseUtil.error(400, "请求体不能为空")

        name = data.get('name')
        value = data.get('value')

        if not name or not value:
            return ResponseUtil.error(400, "name和value字段不能为空")

        # 检查是否已存在
        existing = prompt_manager.get_prompt(name)
        if existing:
            return ResponseUtil.error(400, f"提示词 '{name}' 已存在")

        # 创建新的
        success = prompt_manager.set_prompt(name, value)

        if success:
            return ResponseUtil.success({"message": "提示词创建成功", "name": name}, 201)
        else:
            return ResponseUtil.error(500, "创建提示词失败")

    except Exception as e:
        logger.error(f"创建提示词失败: {e}")
        return ResponseUtil.error(500, str(e))


# 获取单个Prompt
@app.route('/v1/prompt/get', methods=['GET', 'POST'])
@require_api_key
def get_prompt():
    """
    获取提示词
    GET /v1/prompt/get?name=weather
    或
    POST /v1/prompt/get
    {
        "name": "weather"
    }
    """
    try:
        if request.method == 'GET':
            name = request.args.get('name')
        else:
            data = request.get_json() or {}
            name = data.get('name')

        if not name:
            return ResponseUtil.error(400, "name参数不能为空")

        # 获取提示词
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


# 列出所有Prompt
@app.route('/v1/prompt/list', methods=['GET'])
@require_api_key
def list_prompts():
    """
    列出所有提示词
    GET /v1/prompt/list
    """
    try:
        prompts = prompt_manager.list_prompts()

        # 格式化为前端需要的格式
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
    GET /v1/ai/list
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
    GET /v1/ai/get?uuid=xxx
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
    POST /v1/ai/set
    {
        "uuid": "deepseek_config",
        "config": {
            "name": "DeepSeek",
            "api_key": "sk-...",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com"等
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return ResponseUtil.error(400, "请求体不能为空")

        uuid = data.get('uuid')
        config = data.get('config')

        if not uuid or not config:
            return ResponseUtil.error(400, "uuid和config字段不能为空")

        # 必要的字段检查
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
    POST /v1/ai/delete
    {
        "uuid": "deepseek_config"
    }
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


# 发送聊天消息
@app.route('/v1/chat/send', methods=['POST'])
@require_api_key
def send_chat():
    pass

# 列出所有聊天会话
@app.route('/v1/chat/list', methods=['GET'])
@require_api_key
def list_chats():
    pass

# 获取聊天历史 - 支持GET和POST
@app.route('/v1/history/get', methods=['GET', 'POST'])
@require_api_key
def get_history():
    pass

# 获取记忆列表
@app.route('/v1/history/memory', methods=['GET'])
@require_api_key
def get_memory():
    pass

# 创建新聊天会话
@app.route('/v1/create', methods=['POST'])
@require_api_key
def create_chat():
    pass

# 删除聊天会话
@app.route('/v1/delete', methods=['POST'])
@require_api_key
def delete_chat():
    pass


if __name__ == '__main__':
    app.run(debug=True, port=5000)
