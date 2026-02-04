from flask import Flask, request
from functools import wraps

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

# 设置Prompt - 只返回response code
@app.route('/v1/prompt/set', methods=['POST'])
@require_api_key
def set_prompt():
    pass

# 获取单个Prompt - 支持GET和POST
@app.route('/v1/prompt/get', methods=['GET', 'POST'])
@require_api_key
def get_prompt():
    pass

# 列出所有Prompt - GET方法
@app.route('/v1/prompt/list', methods=['GET'])
@require_api_key
def list_prompts():
    pass

# 创建Prompt - 新建，不允许覆盖
@app.route('/v1/prompt/create', methods=['POST'])
@require_api_key
def create_prompt():
    pass

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
