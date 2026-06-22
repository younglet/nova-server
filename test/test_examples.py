"""
test_examples.py — examples/ 目录下的示例文件测试
=================================================

每个示例：
  1. 能被 exec() 加载（语法正确、import 不冲突）
  2. 注册了预期的路由数量
  3. 每个路由能正确响应
  4. 跨平台兼容（不依赖 CPython 独有特性）
"""
import os
import json
import pytest

EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'examples'
)


def _load_example(name):
    """加载示例文件的非 __main__ 部分，返回 (module_namespace, app)。"""
    path = os.path.join(EXAMPLES_DIR, name + '.py')
    with open(path, encoding='utf-8') as f:
        code = f.read()
    main_split = code.split('if __name__')
    module_code = main_split[0]
    ns = {'__name__': '__test__'}
    exec(compile(module_code, path, 'exec'), ns)
    return ns


# ════════════════════════════════════════════════════════════════
# 01_hello.py
# ════════════════════════════════════════════════════════════════

class TestHelloExample:
    def test_loads(self):
        ns = _load_example('01_hello')
        assert 'app' in ns

    def test_routes_count(self):
        ns = _load_example('01_hello')
        app = ns['app']
        # 4 routes: /, /hello/<name>, /api/version, /health
        assert len(app.url_map) >= 4

    @pytest.mark.asyncio
    async def test_root_redirects(self):
        ns = _load_example('01_hello')
        res = await ns['app'].dispatch_request(
            _make_req(ns['app'], 'GET', '/'))
        assert res.status_code == 302
        assert res.headers.get('Location') == '/hello/world'

    @pytest.mark.asyncio
    async def test_hello_with_name(self):
        ns = _load_example('01_hello')
        res = await ns['app'].dispatch_request(
            _make_req(ns['app'], 'GET', '/hello/Alice'))
        assert res.status_code == 200
        assert b'Alice' in res.body

    @pytest.mark.asyncio
    async def test_api_version(self):
        ns = _load_example('01_hello')
        res = await ns['app'].dispatch_request(
            _make_req(ns['app'], 'GET', '/api/version'))
        assert res.status_code == 200
        data = json.loads(res.body)
        assert data['server'] == 'nova-server'
        assert 'version' in data

    @pytest.mark.asyncio
    async def test_health(self):
        ns = _load_example('01_hello')
        res = await ns['app'].dispatch_request(
            _make_req(ns['app'], 'GET', '/health'))
        assert res.status_code == 200
        data = json.loads(res.body)
        assert data['status'] == 'ok'
        assert 'memory' in data
        # memory.platform 必定存在（mp or cpython）
        assert 'platform' in data['memory']

    @pytest.mark.asyncio
    async def test_404(self):
        ns = _load_example('01_hello')
        res = await ns['app'].dispatch_request(
            _make_req(ns['app'], 'GET', '/no-such-route'))
        assert res.status_code == 404

    def test_no_micro_python_only_imports(self):
        """★ 跨平台：不能 import MicroPython 独有模块。"""
        ns = _load_example('01_hello')
        # gc 必须存在（CPython 也有），但不能调用 mem_free() 直接
        # 这个测试用 exec 加载没报错就算过
        assert 'gc' in ns


# ════════════════════════════════════════════════════════════════
# 02_sensors_api.py
# ════════════════════════════════════════════════════════════════

class TestSensorsExample:
    def test_loads(self):
        ns = _load_example('02_sensors_api')
        assert 'app' in ns
        # 应该能拿到传感器 wrapper
        assert '_temp_sensor' in ns

    def test_routes_count(self):
        ns = _load_example('02_sensors_api')
        app = ns['app']
        # 6 routes: /, /api/sensors, /api/sensors/temperature,
        #           /api/sensors/humidity, /api/sensors/light, POST /api/led
        assert len(app.url_map) >= 6

    @pytest.mark.asyncio
    async def test_all_sensors(self):
        ns = _load_example('02_sensors_api')
        res = await ns['app'].dispatch_request(
            _make_req(ns['app'], 'GET', '/api/sensors'))
        assert res.status_code == 200
        data = json.loads(res.body)
        # 必须有这些字段（即使传感器没读到，结构在）
        for key in ('temperature', 'humidity', 'light_raw', 'fresh'):
            assert key in data

    @pytest.mark.asyncio
    async def test_temperature_endpoint(self):
        ns = _load_example('02_sensors_api')
        res = await ns['app'].dispatch_request(
            _make_req(ns['app'], 'GET', '/api/sensors/temperature'))
        # PC mock 数据一定会成功 → 200
        # 真实硬件可能失败 → 503
        assert res.status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_led_control_on(self):
        ns = _load_example('02_sensors_api')
        res = await ns['app'].dispatch_request(
            _make_req(ns['app'], 'POST', '/api/led',
                      body=b'{"state":"on"}',
                      headers={'Content-Type': 'application/json'}))
        assert res.status_code == 200
        data = json.loads(res.body)
        assert data == {'status': 'ok', 'led': 'on'}

    @pytest.mark.asyncio
    async def test_led_control_off(self):
        ns = _load_example('02_sensors_api')
        res = await ns['app'].dispatch_request(
            _make_req(ns['app'], 'POST', '/api/led',
                      body=b'{"state":"off"}',
                      headers={'Content-Type': 'application/json'}))
        assert res.status_code == 200
        data = json.loads(res.body)
        assert data['led'] == 'off'

    @pytest.mark.asyncio
    async def test_led_invalid_state(self):
        ns = _load_example('02_sensors_api')
        res = await ns['app'].dispatch_request(
            _make_req(ns['app'], 'POST', '/api/led',
                      body=b'{"state":"bogus"}',
                      headers={'Content-Type': 'application/json'}))
        assert res.status_code == 400

    def test_safe_sensor_class_exists(self):
        """SafeSensor 包装类必须存在并工作。"""
        ns = _load_example('02_sensors_api')
        cls = ns['SafeSensor']
        # 测试它能接受函数
        s = cls(lambda: 42, max_age_ms=1000, retries=2)
        assert s.read() == 42


# ════════════════════════════════════════════════════════════════
# 03_static_files.py
# ════════════════════════════════════════════════════════════════

class TestStaticFilesExample:
    def test_loads(self):
        ns = _load_example('03_static_files')
        assert 'app' in ns
        assert 'WWW_ROOT' in ns

    def test_routes_count(self):
        ns = _load_example('03_static_files')
        app = ns['app']
        # 3 routes: /, /static/<path:path>, /api/info
        assert len(app.url_map) >= 3

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self):
        """★ 安全：../ 必须返回 403。"""
        ns = _load_example('03_static_files')
        res = await ns['app'].dispatch_request(
            _make_req(ns['app'], 'GET', '/static/../etc/passwd'))
        assert res.status_code in (403, 404)
        # 不应该返回 200 + 文件内容

    @pytest.mark.asyncio
    async def test_info_endpoint(self):
        ns = _load_example('03_static_files')
        res = await ns['app'].dispatch_request(
            _make_req(ns['app'], 'GET', '/api/info'))
        assert res.status_code == 200
        data = json.loads(res.body)
        assert 'www_root' in data
        assert 'platform' in data

    def test_safe_path_helper(self):
        ns = _load_example('03_static_files')
        safe = ns['_is_safe_path']
        assert safe('foo/bar.html') is True
        assert safe('../etc/passwd') is False
        assert safe('/abs/path') is False
        assert safe('a/../../b') is False

    def test_join_path_helper(self):
        ns = _load_example('03_static_files')
        join = ns['_join_path']
        assert join('a', 'b') == 'a/b'
        assert join('a/', 'b') == 'a/b'
        assert join('a', '/b') == 'a/b'
        assert join('a', '', 'b') == 'a/b'


# ════════════════════════════════════════════════════════════════
# 公共 helper
# ════════════════════════════════════════════════════════════════

def _make_req(app, method, path, body=b'', headers=None):
    """为测试构造 Request。"""
    from nova_server import Request
    h = {'Content-Length': str(len(body))}
    if headers:
        h.update(headers)
    return Request(
        app, ('127.0.0.1', 1), method, path, '1.1', h,
        body=body if body else b'',
        stream=None, sock=None,
    )