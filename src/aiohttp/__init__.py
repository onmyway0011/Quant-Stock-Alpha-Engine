# Minimal stub of aiohttp to satisfy tests without external dependency
# This stub provides ClientSession and ClientError to be patched/mocked in tests.
# cspell:ignore errmsg errcode

import types
from typing import Any, Dict, Optional


class ClientError(Exception):
    pass


class ClientTimeout:
    """简化的超时配置类"""
    def __init__(self, total: Optional[float] = None, **kwargs):
        self.total = total


class _Response:
    def __init__(self, status: int = 200, payload: Optional[Dict[str, Any]] = None):
        self.status = status
        self._payload = payload or {"errcode": 0, "errmsg": "ok"}

    async def json(self) -> Dict[str, Any]:
        return self._payload

    async def text(self, encoding: str = 'utf-8') -> str:
        """返回文本响应"""
        return str(self._payload)

    async def __aenter__(self) -> "_Response":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class ClientSession:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> "ClientSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, *args, **kwargs) -> _Response:
        # Provide a default successful response; tests will patch this method as needed
        return _Response()

    async def get(self, *args, **kwargs) -> _Response:
        # Provide a default successful response; tests will patch this method as needed
        return _Response()

    async def close(self):
        """关闭会话（空操作）"""
        pass