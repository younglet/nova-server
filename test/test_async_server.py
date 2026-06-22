"""
test_async_server.py — 端到端异步 HTTP server 测试
=================================================

启动一个真的 socket server（端口随机），用 HTTP 客户端打请求。
覆盖：
  - GET / 字符串
  - GET / 字典 → JSON
  - POST JSON
  - 并发请求
  - 404 / 405
  - before/after request 钩子
  - Content-Length / Content-Type 自动设置

注意：Python 3.14 在 Windows 上的 asyncio + socket 有已知问题（WinError 10106），
      如果跑这个文件失败，请用 Python 3.11/3.12 跑。
"""
import asyncio
import socket
import threading
import time
import json
import urllib.request
import urllib.error
import sys

import pytest

from nova_server import NovaServer, redirect, abort


# ════════════════════════════════════════════════════════════════
# helpers
# ════════════════════════════════════════════════════════════════

def http_get(host, port, path, headers=None, timeout=5):
    url = 'http://{}:{}{}'.format(host, port, path)
    req = urllib.request.Request(url, method='GET')
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers or {})


def http_post(host, port, path, body=b'', headers=None, timeout=5):
    url = 'http://{}:{}{}'.format(host, port, path)
    req = urllib.request.Request(url, method='POST', data=body)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers or {})


async def start_test_server(app):
    """启动一个临时 server，返回 (port, shutdown_coro)。"""
    server = await asyncio.start_server(
        lambda r, w: _handle(app, r, w), '127.0.0.1', 0)
    port = server.sockets[0].getsockname()[1]

    async def shutdown():
        server.close()
        await server.wait_closed()

    return server, port, shutdown


async def _handle(app, reader, writer):
    """app.handle_request 的包装，吞掉异常避免影响其他请求。"""
    try:
        await app.handle_request(reader, writer)
    except Exception:
        try:
            writer.close()
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════
# 跳过：Python 3.14 + Windows asyncio 兼容性 bug
# ════════════════════════════════════════════════════════════════

@pytest.fixture(scope='session', autouse=True)
def skip_on_python_314_windows():
    py_ver = sys.version_info
    if py_ver >= (3, 14) and sys.platform == 'win32':
        pytest.skip('Python 3.14 + Windows asyncio has known socket bug',
                    allow_module_level=False)


# ════════════════════════════════════════════════════════════════
# fixtures
# ════════════════════════════════════════════════════════════════

@pytest.fixture
async def basic_server():
    """最简 server：/text, /json。"""
    app = NovaServer()

    @app.get('/text')
    async def t(req):
        return 'hello'

    @app.get('/json')
    async def j(req):
        return {'a': 1}

    server, port, shutdown = await start_test_server(app)
    serve_task = asyncio.create_task(server.serve_forever())
    try:
        yield port
    finally:
        serve_task.cancel()
        try:
            await serve_task
        except asyncio.CancelledError:
            pass
        await shutdown()


@pytest.fixture
async def full_server():
    """完整 server：含 redirect / POST / abort。"""
    app = NovaServer()

    @app.get('/text')
    async def t(req): return 'plain'

    @app.get('/json')
    async def j(req): return {'k': 'v'}

    @app.get('/redirect')
    async def r(req): return redirect('/dest')

    @app.get('/dest')
    async def d(req): return 'arrived'

    @app.post('/echo')
    async def e(req): return {'got': req.json}

    @app.get('/err404')
    async def e404(req):
        abort(404, 'no such item')

    server, port, shutdown = await start_test_server(app)
    serve_task = asyncio.create_task(server.serve_forever())
    try:
        yield port
    finally:
        serve_task.cancel()
        try:
            await serve_task
        except asyncio.CancelledError:
            pass
        await shutdown()


# ════════════════════════════════════════════════════════════════
# 测试
# ════════════════════════════════════════════════════════════════

class TestBasicServer:
    @pytest.mark.asyncio
    async def test_get_text(self, basic_server):
        port = basic_server
        loop = asyncio.get_event_loop()
        status, body, headers = await loop.run_in_executor(
            None, http_get, '127.0.0.1', port, '/text')
        assert status == 200
        assert body == b'hello'

    @pytest.mark.asyncio
    async def test_get_json(self, basic_server):
        port = basic_server
        loop = asyncio.get_event_loop()
        status, body, headers = await loop.run_in_executor(
            None, http_get, '127.0.0.1', port, '/json')
        assert status == 200
        assert 'application/json' in headers.get('Content-Type', '')
        data = json.loads(body)
        assert data == {'a': 1}

    @pytest.mark.asyncio
    async def test_404_route(self, basic_server):
        port = basic_server
        loop = asyncio.get_event_loop()
        status, body, _ = await loop.run_in_executor(
            None, http_get, '127.0.0.1', port, '/nope')
        assert status == 404


class TestFullServer:
    @pytest.mark.asyncio
    async def test_redirect(self, full_server):
        port = full_server
        loop = asyncio.get_event_loop()
        status, _, headers = await loop.run_in_executor(
            None, http_get, '127.0.0.1', port, '/redirect')
        assert status == 302
        assert headers.get('Location') == '/dest'

    @pytest.mark.asyncio
    async def test_post_json(self, full_server):
        port = full_server
        loop = asyncio.get_event_loop()
        status, body, _ = await loop.run_in_executor(
            None, http_post, '127.0.0.1', port, '/echo',
            b'{"name":"alice","n":1}', {'Content-Type': 'application/json'})
        assert status == 200
        data = json.loads(body)
        assert data == {'got': {'name': 'alice', 'n': 1}}

    @pytest.mark.asyncio
    async def test_abort(self, full_server):
        port = full_server
        loop = asyncio.get_event_loop()
        status, _, _ = await loop.run_in_executor(
            None, http_get, '127.0.0.1', port, '/err404')
        assert status == 404


@pytest.mark.asyncio
async def test_parallel_requests():
    """10 个并发请求都应成功。"""
    app = NovaServer()

    @app.get('/hello/<name>')
    async def hello(req, name):
        await asyncio.sleep(0.01)
        return {'msg': 'Hello, {}!'.format(name)}

    server, port, shutdown = await start_test_server(app)
    serve_task = asyncio.create_task(server.serve_forever())
    try:
        loop = asyncio.get_event_loop()
        tasks = []
        for i in range(10):
            tasks.append(loop.run_in_executor(
                None, http_get, '127.0.0.1', port,
                '/hello/user{}'.format(i)))
        results = await asyncio.gather(*tasks)
        for i, (status, body, _) in enumerate(results):
            assert status == 200, 'req {} failed'.format(i)
            data = json.loads(body)
            assert data == {'msg': 'Hello, user{}!'.format(i)}
    finally:
        serve_task.cancel()
        try:
            await serve_task
        except asyncio.CancelledError:
            pass
        await shutdown()


@pytest.mark.asyncio
async def test_after_request_hook_adds_header():
    """after_request 钩子可以修改响应头。"""
    app = NovaServer()

    @app.after_request
    async def add_header(req, res):
        res.headers['X-Custom'] = 'yes'
        return res

    @app.get('/x')
    async def h(req):
        return 'ok'

    server, port, shutdown = await start_test_server(app)
    serve_task = asyncio.create_task(server.serve_forever())
    try:
        loop = asyncio.get_event_loop()
        status, body, headers = await loop.run_in_executor(
            None, http_get, '127.0.0.1', port, '/x')
        assert status == 200
        assert headers.get('X-Custom') == 'yes'
    finally:
        serve_task.cancel()
        try:
            await serve_task
        except asyncio.CancelledError:
            pass
        await shutdown()


@pytest.mark.asyncio
async def test_content_length_set():
    """Response 应自动设置 Content-Length。"""
    app = NovaServer()

    @app.get('/sized')
    async def h(req):
        return 'x' * 100

    server, port, shutdown = await start_test_server(app)
    serve_task = asyncio.create_task(server.serve_forever())
    try:
        loop = asyncio.get_event_loop()
        status, body, headers = await loop.run_in_executor(
            None, http_get, '127.0.0.1', port, '/sized')
        assert status == 200
        assert len(body) == 100
        # Content-Length should be set
        cl = headers.get('Content-Length')
        assert cl == '100'
    finally:
        serve_task.cancel()
        try:
            await serve_task
        except asyncio.CancelledError:
            pass
        await shutdown()


@pytest.mark.asyncio
async def test_405_for_wrong_method():
    """路由存在但方法不匹配 → 405。"""
    app = NovaServer()

    @app.get('/only-get')
    async def h(req):
        return 'ok'

    server, port, shutdown = await start_test_server(app)
    serve_task = asyncio.create_task(server.serve_forever())
    try:
        loop = asyncio.get_event_loop()
        status, body, _ = await loop.run_in_executor(
            None, http_post, '127.0.0.1', port, '/only-get', b'')
        assert status == 405
    finally:
        serve_task.cancel()
        try:
            await serve_task
        except asyncio.CancelledError:
            pass
        await shutdown()