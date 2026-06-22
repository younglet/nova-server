"""
conftest.py — nova-server 测试公共 fixtures
==========================================

提供：
  - app 实例 fixture
  - 模拟 Request 构造器
  - dispatch_request 调用包装
  - 临时 www 目录 fixture

用法：
  pytest test/
  pytest test/test_examples.py -v
  pytest test/test_dispatch.py::test_dict_return_is_json_body
"""
import sys
import os
import asyncio
import pytest

# 把项目根加进 path，让 import nova_server 能找到
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from nova_server import (  # noqa: E402
    NovaServer, Request, Response, NoCaseDict,
    HTTPException, URLPattern, abort, redirect, send_file,
)


# ════════════════════════════════════════════════════════════════
# 基础 fixtures
# ════════════════════════════════════════════════════════════════

@pytest.fixture
def app():
    """空 NovaServer 实例。"""
    return NovaServer()


@pytest.fixture
def client_addr():
    return ('127.0.0.1', 12345)


def make_request(app, client_addr, method, path, body=b'', headers=None):
    """构造一个 Request 对象，不经过 socket。

    用法：
        req = make_request(app, ('127.0.0.1', 1), 'GET', '/hello/world')
        res = await app.dispatch_request(req)
    """
    # ★ headers 必须用 NoCaseDict，否则大小写不敏感特性失效
    h = NoCaseDict({'Content-Length': str(len(body))})
    if headers:
        for k, v in headers.items():
            h[k] = v
    return Request(
        app, client_addr, method, path, '1.1', h,
        body=body if body else b'',
        stream=None, sock=None,
    )


async def call(app, method, path, body=b'', headers=None):
    """直接调用 dispatch_request，返回 Response 对象。

    这是单元测试最常用的入口——跳过 socket 层。
    """
    req = make_request(app, ('127.0.0.1', 1), method, path, body, headers)
    return await app.dispatch_request(req)


@pytest.fixture
def http_get():
    """简化的 GET 调用 fixture。"""
    async def _get(app, path, headers=None):
        return await call(app, 'GET', path, b'', headers)
    return _get


@pytest.fixture
def http_post():
    async def _post(app, path, body=b'', headers=None):
        return await call(app, 'POST', path, body, headers)
    return _post


# ════════════════════════════════════════════════════════════════
# 工具函数
# ════════════════════════════════════════════════════════════════

def body_text(res):
    """把 Response.body 统一转字符串。"""
    if isinstance(res.body, bytes):
        return res.body.decode('utf-8', errors='replace')
    return str(res.body)


def is_json_content(res):
    """检查响应 Content-Type 是不是 JSON。"""
    ct = res.headers.get('Content-Type', '')
    return 'application/json' in ct