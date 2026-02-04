import logging
import sys

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