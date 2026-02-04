import logging
import sys
import os

# 创建 logs 目录（如果不存在）
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),  # 输出到控制台
        logging.FileHandler('logs/latest.log', encoding='utf-8')  # 输出到文件
    ]
)

logger = logging.getLogger('prompt_api')