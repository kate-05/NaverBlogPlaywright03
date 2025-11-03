"""
예외 처리 클래스
"""


class BlogNotFoundError(Exception):
    """블로그를 찾을 수 없음"""
    pass


class TimeoutError(Exception):
    """타임아웃 오류"""
    pass


class ParsingError(Exception):
    """파싱 오류"""
    pass


class NetworkError(Exception):
    """네트워크 오류"""
    pass

