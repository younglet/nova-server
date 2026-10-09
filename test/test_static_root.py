"""test_static_root.py — 根路径懒挂载（_mount_root_index）的单元测试。

覆盖：
  1. 应用没写 '/' + 静态目录有 index.html → GET / 返回 200 且是 index.html 内容
  2. 应用自己写了 '/'               → 根路径仍归应用（不被顶掉）
  3. static_dir=None                → 什么都不挂（GET / 404）
  4. 静态目录里没有 index.html      → GET / 404（json 提示 index.html not found）
  5. 重复调用                        → 不会重复挂载（url_map 里 '/' 只有一条）
  6. 老行为不受影响                  → GET /static/ 照旧可用
"""
import asyncio
import os

from nova_server import NovaServer, NoCaseDict, Request


def _make_request(app, path):
    return Request(
        app, ('127.0.0.1', 1), 'GET', path, '1.1',
        NoCaseDict({'Content-Length': '0'}),
        body=b'', stream=None, sock=None,
    )


def _get(app, path):
    """发一次 GET，返回 (status_code, 文本body)。"""
    async def _run():
        res = await app.dispatch_request(_make_request(app, path))
        body = res.body
        if hasattr(body, 'read'):
            data = body.read()
            body.close()
        else:
            data = body
        if isinstance(data, bytes):
            data = data.decode('utf-8', 'replace')
        return res.status_code, str(data)
    return asyncio.run(_run())


def _static_app(tmp_path, with_index=True, name='static'):
    d = tmp_path / name
    d.mkdir()
    if with_index:
        (d / 'index.html').write_text('<h1>ROOT OK</h1>', encoding='utf-8')
    return NovaServer(static_dir=str(d))


def test_root_serves_index_when_app_has_no_root_route(tmp_path):
    app = _static_app(tmp_path)
    app._mount_root_index()
    status, body = _get(app, '/')
    assert status == 200
    assert 'ROOT OK' in body


def test_app_root_route_wins(tmp_path):
    app = _static_app(tmp_path)

    @app.get('/')
    async def mine(request):
        return 'MY OWN ROOT'

    app._mount_root_index()
    status, body = _get(app, '/')
    assert status == 200
    assert 'MY OWN ROOT' in body


def test_no_mount_when_static_dir_is_none(tmp_path):
    app = NovaServer(static_dir=None)
    app._mount_root_index()
    status, _ = _get(app, '/')
    assert status == 404


def test_404_when_index_html_missing(tmp_path):
    app = _static_app(tmp_path, with_index=False, name='empty')
    app._mount_root_index()
    status, body = _get(app, '/')
    assert status == 404
    assert 'index.html not found' in body


def test_mount_is_idempotent(tmp_path):
    app = _static_app(tmp_path)
    app._mount_root_index()
    app._mount_root_index()
    n = sum(1 for _m, p, _h, _u, _s in app.url_map if p.url_pattern == '/')
    assert n == 1


def test_static_prefix_still_works(tmp_path):
    app = _static_app(tmp_path)
    app._mount_root_index()
    status, body = _get(app, '/static/')
    assert status == 200
    assert 'ROOT OK' in body