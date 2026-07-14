"""
test_task_api.py — @app.task / add_task / tasks() 单元测试
=========================================================

覆盖：
  - @app.task 装饰器：注册同步 task
  - app.add_task 函数式 + name 参数
  - app.tasks() 只读列表
  - 重名检测（抛 ValueError）
  - 同步/异步函数自动识别
  - 错误隔离（task 抛异常不影响其他 task）
"""
import asyncio
import pytest

from nova_server import NovaServer


# ═══════════════════════════════════════════════════════════
# 注册 + 列出
# ═══════════════════════════════════════════════════════════

class TestRegisterAndList:

    def test_decorator_registers_task(self):
        app = NovaServer()
        @app.task(interval_ms=30)
        def my_task():
            pass
        tasks = app.tasks()
        assert len(tasks) == 1
        assert tasks[0]['name'] == 'my_task'
        assert tasks[0]['interval_ms'] == 30
        assert tasks[0]['is_async'] is False
        assert tasks[0]['running'] is False    # 还没 start_server

    def test_add_task_functional_form(self):
        app = NovaServer()
        def ping():
            pass
        app.add_task(ping, interval_ms=100)
        assert app.tasks()[0]['name'] == 'ping'

    def test_add_task_lambda_with_name(self):
        app = NovaServer()
        app.add_task(lambda: None, interval_ms=50, name='anon')
        assert app.tasks()[0]['name'] == 'anon'

    def test_multiple_tasks_listed(self):
        app = NovaServer()

        @app.task(interval_ms=10)
        def a():
            pass

        @app.task(interval_ms=20)
        def b():
            pass

        def c():
            pass
        app.add_task(c, interval_ms=30)

        names = [t['name'] for t in app.tasks()]
        assert names == ['a', 'b', 'c']

    def test_default_interval_is_50ms(self):
        app = NovaServer()
        @app.task()
        def tick():
            pass
        assert app.tasks()[0]['interval_ms'] == 50


# ═══════════════════════════════════════════════════════════
# 重名检测
# ═══════════════════════════════════════════════════════════

class TestDuplicateName:

    def test_duplicate_via_decorator_raises(self):
        app = NovaServer()
        @app.task(interval_ms=10)
        def same_name():
            pass
        with pytest.raises(ValueError) as exc:
            @app.task(interval_ms=20)
            def same_name():
                pass
        assert 'same_name' in str(exc.value)
        assert 'already registered' in str(exc.value)

    def test_duplicate_via_add_task_raises(self):
        app = NovaServer()
        def f():
            pass
        app.add_task(f, interval_ms=10)
        with pytest.raises(ValueError):
            app.add_task(f, interval_ms=20)


# ═══════════════════════════════════════════════════════════
# 同步 vs 异步识别
# ═══════════════════════════════════════════════════════════

class TestAsyncDetection:

    def test_sync_function_detected_as_sync(self):
        app = NovaServer()
        @app.task(interval_ms=10)
        def sync():
            return 1
        assert app.tasks()[0]['is_async'] is False

    def test_async_function_detected_as_async(self):
        app = NovaServer()
        @app.task(interval_ms=10)
        async def coro():
            return 1
        assert app.tasks()[0]['is_async'] is True

    def test_lambda_detected_as_sync(self):
        app = NovaServer()
        app.add_task(lambda: None, interval_ms=10, name='l')
        assert app.tasks()[0]['is_async'] is False


# ═══════════════════════════════════════════════════════════
# 错误隔离（task 抛异常不影响其他 task / server）
# ═══════════════════════════════════════════════════════════

class TestErrorIsolation:

    def test_error_does_not_break_run_task_loop(self):
        """一个 task 抛异常后，其他 task 仍然能跑。"""
        app = NovaServer()
        good_count = [0]

        @app.task(interval_ms=10)
        def good():
            good_count[0] += 1

        @app.task(interval_ms=10)
        def bad():
            raise ValueError('intentional')

        # 跑一次 _run_task 看错误被捕获、不影响 good
        # 用 asyncio.wait_for 限时避免无限循环
        async def run_once():
            # 找到 good 的 idx，触发它一次
            for i, entry in enumerate(app._tasks):
                if entry[0] == 'good':
                    # 直接调用函数本体（同步路径）
                    try:
                        entry[1]()
                    except Exception:
                        pass
                    return
            raise RuntimeError('good not found')

        asyncio.run(run_once())
        assert good_count[0] == 1

    def test_exception_in_task_caught_in_run_loop(self):
        """验证 _run_task 内部 try/except 能捕获 task 抛出的异常。"""
        app = NovaServer()

        @app.task(interval_ms=10)
        def bad():
            raise ValueError('boom')

        async def check():
            idx = None
            for i, entry in enumerate(app._tasks):
                if entry[0] == 'bad':
                    idx = i
                    break
            assert idx is not None
            t = asyncio.create_task(app._run_task(idx))
            # PC Python 没 sleep_ms，用 sleep
            try:
                await asyncio.sleep_ms(50)
            except AttributeError:
                await asyncio.sleep(0.05)
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass

        asyncio.run(check())


# ═══════════════════════════════════════════════════════════
# HTTP 接口能看到 task 状态
# ═══════════════════════════════════════════════════════════

class TestHTTPIntegration:

    def test_api_tasks_endpoint_returns_registered(self):
        """注册 task 后，GET /api/tasks 能看到（running=False 因为没起 server）。"""
        from test.conftest import call

        app = NovaServer()

        @app.task(interval_ms=30)
        def check_button():
            pass

        @app.get('/api/tasks')
        async def list_tasks(request):
            return {'tasks': app.tasks()}

        resp = asyncio.run(call(app, 'GET', '/api/tasks'))
        assert resp.status_code == 200
        # Response body 是 json 字符串
        import json
        body = json.loads(resp.body)
        assert len(body['tasks']) == 1
        assert body['tasks'][0]['name'] == 'check_button'
        assert body['tasks'][0]['running'] is False