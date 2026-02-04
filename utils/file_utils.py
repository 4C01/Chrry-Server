import json
class FileReadError(Exception):
    """自定义文件读取异常"""
    pass

# ==================== 基础读取 ====================
def read_raw(path) -> bytes:
    """
    读取原始字节
    :param path: FilePath(str/Path)
    :return: rawBytes(bytes)
    """
    try:
        with open(path, 'rb') as f:
            return f.read()
    except OSError as e:
        raise FileReadError(f"无法读取文件 {path}: {e}")

def read_text(path, encoding: str = "utf-8") -> str:
    """
    读取文本文件
    :param path: FilePath(str/Path)
    :param encoding: defaults to utf-8(str)
    :return: textStr(str)
    """
    raw = read_raw(path)
    try:
        return raw.decode(encoding)
    except UnicodeDecodeError as e:
        raise FileReadError(f"解码失败 {path}: {e}")

# ==================== 格式解析 ====================
def read_json(path, encoding: str = "utf-8"):
    """
    读取JSON文件
    :param path: FilePath(str/Path)
    :param encoding: defaults to utf-8(str)
    :return: JSON(Any)
    """
    text = read_text(path, encoding)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise FileReadError(f"JSON解析失败 {path}: {e}")