from flask import jsonify

class ResponseUtil:
    """响应工具类"""

    @staticmethod
    def success(data = None) -> tuple:
        """成功响应

        Args:
            data: 要返回的数据，默认为空dict

        Returns:
            (json_response, 200)
        """
        if data is None:
            data = {}

        response = {
            "success": True,
            "data": data
        }

        return jsonify(response), 200

    @staticmethod
    def error(http_status: int, cause: str = None) -> tuple:
        """错误响应
            400 missing field
            403 invalid API key
            422 malformed parameter

        Args:
            http_status: HTTP状态码:
            cause: 错误原因，如果为None则自动生成

        Returns:
            (json_response, http_status)
        """
        # 如果没有提供原因，根据状态码自动生成
        if cause is None:
            if http_status == 400:
                cause = "Missing one or more fields"
            elif http_status == 403:
                cause = "Invalid API key"
            elif http_status == 422:
                cause = "Malformed parameter"
            else:
                cause = "InternalError"

        response = {
            "success": False,
            "cause": cause
        }

        return jsonify(response), http_status
