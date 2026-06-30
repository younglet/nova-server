"""
test_builtin.py — nova_server 内置特性的单元测试
================================================

覆盖：
  - _is_safe_path：路径穿越防护
  - NovaServer(static_dir=...)：自动挂载静态文件路由
  - NovaServer(debug=True/False)：调试开关（含请求日志）
"""
import json
import pytest

from nova_server import NovaServer, _is_safe_path, send_file
from test.conftest import call, make_request


# ════════════════════════════════════════════════════════════════
# _is_safe_path
# ════════════════════════════════════════════════════════════════

class TestIsSafePath:
    def test_safe_simple(self):
        assert _is_safe_path('foo.html') is True

    def test_safe_nested(self):
        assert _is_safe_path('foo/bar.html') is True

    def test_safe_deep(self):
        assert _is_safe_path('a/b/c/d/e.css') is True

    def test_block_empty(self):
        assert _is_safe_path('') is False
        assert _is_safe_path(None) is False

    def test_block_absolute(self):
        """以 / 开头的绝对路径必须拒绝。"""
        assert _is_safe_path('/etc/passwd') is False

    def test_block_parent_traversal(self):
        """../ 必须拒绝。"""
        assert _is_safe_path('../etc/passwd') is False

    def test_block_nested_parent_traversal(self):
        assert _is_safe_path('a/../../b') is False
        assert _is_safe_path('a/b/../../../c') is False

    def test_block_dotdot_filename(self):
        """.. 单独作为文件名也要拒绝。"""
        assert _is_safe_path('..') is False


# ════════════════════════════════════════════════════════════════
# static_dir 自动挂载
# ════════════════════════════════════════════════════════════════

class TestStaticDirMount:
    def test_no_static_dir_by_default(self):
        """默认 static_dir=None → 不注册静态路由。"""
        app = NovaServer()
        assert app.static_dir is None
        # url_map 应该没有 /static/ 相关路由
        for methods, pattern, *_ in app.url_map:
            assert '/static' not in pattern.url_pattern

    def test_static_dir_registers_routes(self):
        """传 static_dir 后应自动注册 2 个路由（index + file）。"""
        app = NovaServer(static_dir='/static')
        patterns = [p.url_pattern for _, p, *_ in app.url_map]
        assert '/static/' in patterns
        assert '/static/<path:filename>' in patterns

    def test_static_path_customizable(self):
        """URL 前缀可自定义。"""
        app = NovaServer(static_dir='/www', static_path='/assets')
        patterns = [p.url_pattern for _, p, *_ in app.url_map]
        assert '/assets/' in patterns
        assert '/assets/<path:filename>' in patterns
        assert app.static_dir == '/www'
        assert app.static_path == '/assets'

    def test_debug_default_false(self):
        app = NovaServer()
        assert app.debug is False

    def test_auto_gc_default_false(self):
        """★ ESP32 友好默认：auto_gc=False 防止 heap 碎片化卡顿 1-30 秒。"""
        app = NovaServer()
        assert app.auto_gc is False
        assert app.gc_threshold == 50 * 1024

    def test_auto_gc_opt_in(self):
        """用户可以显式打开，但要传更大的阈值。"""
        app = NovaServer(auto_gc=True, gc_threshold_kb=100)
        assert app.auto_gc is True
        assert app.gc_threshold == 100 * 1024

    def test_debug_can_be_enabled(self):
        app = NovaServer(debug=True)
        assert app.debug is True

    def test_static_dir_with_debug(self):
        """两个特性可以同时启用。"""
        app = NovaServer(static_dir='/static', debug=True)
        assert app.static_dir == '/static'
        assert app.debug is True

    @pytest.mark.asyncio
    async def test_path_traversal_returns_403(self):
        """路径穿越 → 403 forbidden。"""
        app = NovaServer(static_dir='/static')

        # 直接调框架内置的 _serve_file handler
        from nova_server import Request
        req = Request(
            app, ('127.0.0.1', 1), 'GET', '/static/../etc/passwd', '1.1',
            {'Content-Length': '0'}, body=b'')
        # 路由匹配 /static/<path:filename>
        # 但 URL 里包含 ../ 在路径里，匹配时 filename='../etc/passwd'
        res = await app.dispatch_request(req)
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_static_file_not_found_returns_404(self):
        """不存在的文件 → 404。"""
        app = NovaServer(static_dir='/static')

        from nova_server import Request
        req = Request(
            app, ('127.0.0.1', 1), 'GET', '/static/nonexistent.html', '1.1',
            {'Content-Length': '0'}, body=b'')
        res = await app.dispatch_request(req)
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_static_index_not_found_returns_404(self):
        """访问 /static/ 但无 index.html → 404。"""
        app = NovaServer(static_dir='/static')

        from nova_server import Request
        req = Request(
            app, ('127.0.0.1', 1), 'GET', '/static/', '1.1',
            {'Content-Length': '0'}, body=b'')
        res = await app.dispatch_request(req)
        assert res.status_code == 404


# ════════════════════════════════════════════════════════════════
# 端到端：使用 send_file 测试真实静态文件
# ════════════════════════════════════════════════════════════════

class TestStaticDirRealFile:
    """用临时目录 + 真实文件测试完整流程。"""

    @pytest.mark.asyncio
    async def test_serve_real_file(self, tmp_path):
        """★ 真实场景：在临时目录放文件，通过框架自动挂载的服务返回。"""
        # 写一个临时文件
        static_dir = tmp_path / 'static'
        static_dir.mkdir()
        (static_dir / 'hello.txt').write_text('Hello, ESP32!')

        app = NovaServer(static_dir=str(static_dir).replace('\\', '/'))

        from nova_server import Request
        req = Request(
            app, ('127.0.0.1', 1), 'GET',
            '/static/hello.txt', '1.1',
            {'Content-Length': '0'}, body=b'')
        res = await app.dispatch_request(req)
        assert res.status_code == 200
        assert b'Hello, ESP32!' in res.body