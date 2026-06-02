class AppException(Exception):
    """业务异常，对应 Blog 的 BaseException"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
