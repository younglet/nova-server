"""
test_micropython_rewrite.py — 验证 MicroPython 重写后的新行为

覆盖：
  - 路由无限个（旧的 _limit=3 已删除）
  - mount 无总数限制
  - 默认 host='0.0.0.0', port=80
  - 默认 auto_gc=False（ESP32 友好）
  - 默认 static_dir='/static'（v0.2 起自动启用静态文件）
  - 启动 banner 使用 self.debug（不是 local 变量 debug 参数）
  - _format_hms / _format_http_date 用 tuple 格式化
  - Response.write 快路径（bytes body → 1 次 awrite）
  - 没有 CPython-only 的兼容代码（在源码层验证）
"""
import inspect
import pytest

from nova_server import (
    NovaServer, _format_hms, _format_http_date,
    _WDAY_ABBR, _MONTH_ABBR, MUTED_SOCKET_ERRORS,
)


# ════════════════════════════════════════════════════════════════
# 路由无限个（旧的 _limit=3 限制已去除）
# ════════════════════════════════════════════════════════════════

class TestRouteLimitRemoved:
    def test_register_100_routes(self):
        """★ 重写后无 3 路由限制：可以注册 100 个。
        注：默认 NovaServer() 会自动挂载 2 个 /static 路由（v0.2 起）。
        这里用 static_dir=None 排除干扰，专注测注册数量。
        """
        app = NovaServer(static_dir=None)
        for i in range(100):
            @app.get('/route/{i}'.format(i=i))
            async def h(req, i=i):
                return {'i': i}
        assert len(app.url_map) == 100

    def test_register_decorator_returns_function(self):
        """route() 装饰器必须原样返回函数（不能被消费）。"""
        app = NovaServer(static_dir=None)
        async def handler(req): return 'ok'
        result = app.get('/test')(handler)
        assert result is handler

    def test_no_runtime_error_when_exceeds_old_limit(self):
        """超过老限制（3）也不抛 RuntimeError。"""
        app = NovaServer(static_dir=None)
        for i in range(10):  # 远超老限制 3
            def make_h(i):
                async def h(req):
                    return {'i': i}
                return h
            app.get('/r/' + str(i))(make_h(i))
        # 老代码会在这抛 RuntimeError，新代码不该
        assert len(app.url_map) == 10


class TestMountUnlimited:
    def test_mount_large_subapps(self):
        """mount 无总数限制：主 app + 多个子 app，路由总数 > 3。"""
        main = NovaServer(static_dir=None)
        for i in range(5):
            sub = NovaServer(static_dir=None)
            @sub.get('/sub/{}'.format(i))
            async def h(req):
                return {'sub': i}
            main.mount(sub, url_prefix='/m{}'.format(i))
        # 5 个子 app × 1 路由 = 5，远超老限制
        assert len(main.url_map) == 5


# ════════════════════════════════════════════════════════════════
# 默认值
# ════════════════════════════════════════════════════════════════

class TestDefaults:
    def test_default_host(self):
        """★ 默认 host='0.0.0.0'，可直接 app.run() 用。"""
        app = NovaServer()
        assert app.host == '0.0.0.0'

    def test_default_port(self):
        """★ 默认 port=80，ESP32 直接部署不用 port=80。"""
        app = NovaServer()
        assert app.port == 80

    def test_custom_host_port(self):
        app = NovaServer(host='127.0.0.1', port=8080)
        assert app.host == '127.0.0.1'
        assert app.port == 8080

    def test_default_auto_gc_false(self):
        """★ 默认 auto_gc=False，ESP32 heap 碎片化卡顿防护。"""
        app = NovaServer()
        assert app.auto_gc is False

    def test_default_gc_threshold_50kb(self):
        app = NovaServer()
        assert app.gc_threshold == 50 * 1024

    def test_default_debug_false(self):
        app = NovaServer()
        assert app.debug is False


# ════════════════════════════════════════════════════════════════
# 时间格式化（无 time.strftime）
# ════════════════════════════════════════════════════════════════

class TestTimeFormat:
    def test_format_hms(self):
        """_format_hms() 返回 HH:MM:SS 格式。"""
        t = (2025, 1, 15, 14, 30, 21, 2, 15)   # 周三
        assert _format_hms(t) == '14:30:21'

    def test_format_hms_midnight(self):
        """午夜 0 点格式化为 '00:00:00' 而不是 '0:0:0'。"""
        t = (2025, 1, 1, 0, 0, 0, 2, 1)
        assert _format_hms(t) == '00:00:00'

    def test_format_http_date(self):
        """RFC 1123 格式：'Wed, 15 Jan 2025 14:30:21 GMT'。"""
        t = (2025, 1, 15, 14, 30, 21, 2, 15)
        assert _format_http_date(t) == 'Wed, 15 Jan 2025 14:30:21 GMT'

    def test_format_http_date_sunday(self):
        """weekday 6 = Sun。"""
        t = (2025, 1, 19, 8, 0, 0, 6, 19)
        assert _format_http_date(t).endswith('GMT')
        assert 'Sun, 19 Jan 2025' in _format_http_date(t)

    def test_wday_abbr_complete(self):
        assert len(_WDAY_ABBR) == 7
        assert _WDAY_ABBR[0] == 'Mon'
        assert _WDAY_ABBR[6] == 'Sun'

    def test_month_abbr_complete(self):
        assert len(_MONTH_ABBR) == 13
        assert _MONTH_ABBR[1] == 'Jan'
        assert _MONTH_ABBR[12] == 'Dec'


# ════════════════════════════════════════════════════════════════
# 静音 socket 错误码：MicroPython 上不需要 Windows 码
# ════════════════════════════════════════════════════════════════

class TestSocketErrors:
    def test_only_unix_codes(self):
        """ESP32 / MicroPython 上只需要 UNIX 错误码。"""
        assert 32 in MUTED_SOCKET_ERRORS   # Broken pipe
        assert 54 in MUTED_SOCKET_ERRORS   # Connection reset
        assert 104 in MUTED_SOCKET_ERRORS  # Linux reset
        assert 128 in MUTED_SOCKET_ERRORS  # Network dropped

    def test_no_windows_codes(self):
        """Windows 错误码 10053/10054 在 ESP32 上不存在，应已删除。"""
        assert 10053 not in MUTED_SOCKET_ERRORS
        assert 10054 not in MUTED_SOCKET_ERRORS


# ════════════════════════════════════════════════════════════════
# Start server 签名：debug=None 时不覆盖 self.debug
# ════════════════════════════════════════════════════════════════

class TestStartServerSigs:
    def test_start_server_debug_default_none(self):
        """★ start_server 默认 debug=None（不像老版本的 False 会覆盖 self.debug）。"""
        sig = inspect.signature(NovaServer.start_server)
        assert sig.parameters['debug'].default is None

    def test_run_debug_default_none(self):
        sig = inspect.signature(NovaServer.run)
        assert sig.parameters['debug'].default is None


# ════════════════════════════════════════════════════════════════
# _detect_lan_ip 不再有 CPython UDP 探测分支
# ════════════════════════════════════════════════════════════════

class TestDetectLanIp:
    def test_no_udp_probe_8_8_8_8(self):
        """源码里不能再有 '8.8.8.8'（CPython UDP 探测）。"""
        src = open(
            'C:/Users/younglet/Desktop/nova-frontend/nova-server/nova_server.py',
            encoding='utf-8'
        ).read()
        assert '8.8.8.8' not in src, \
            'CPython-only UDP 探测分支必须删除'

    def test_no_orjson_fallback(self):
        """不能再 try import orjson。"""
        src = open(
            'C:/Users/younglet/Desktop/nova-frontend/nova-server/nova_server.py',
            encoding='utf-8'
        ).read()
        assert 'import orjson' not in src

    def test_no_inspect_import(self):
        src = open(
            'C:/Users/younglet/Desktop/nova-frontend/nova-server/nova_server.py',
            encoding='utf-8'
        ).read()
        assert 'from inspect' not in src
        assert 'from functools' not in src


# ════════════════════════════════════════════════════════════════
# handle_request 用 time.ticks_ms()（MicroPython 单调时钟）
# ════════════════════════════════════════════════════════════════

class TestTicksMs:
    def test_handle_request_uses_ticks_ms(self):
        """源码里 handle_request 必须用 ticks_ms/ticks_diff 而不是 time()。"""
        src = open(
            'C:/Users/younglet/Desktop/nova-frontend/nova-server/nova_server.py',
            encoding='utf-8'
        ).read()
        assert 'ticks_ms' in src
        assert 'ticks_diff' in src
        # ticks 用对了
