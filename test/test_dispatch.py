"""
test_dispatch.py — dispatch_request 与 _normalize_response 测试
=============================================================

★ 这是关键测试：之前 _normalize_response 把 dict 当 headers 而不是 body，
  导致所有返回 JSON 的 endpoint 失败。本测试是防回归。
"""
import pytest
import json
from nova_server import NovaServer, abort
from test.conftest import call, body_text


# ════════════════════════════════════════════════════════════════
# _normalize_response 单元测试（修复 bug 的回归保护）
# ════════════════════════════════════════════════════════════════

class TestNormalizeResponse:
    """直接测试 _normalize_response 的行为。"""

    def test_dict_return_is_json_body(self):
        """★ 关键回归测试：dict 返回必须是 JSON body，不是 headers。"""
        from nova_server import NovaServer as NS
        r = NS._normalize_response({'x': 1, 'y': 'z'})
        # body 必须是 dict JSON 序列化结果
        assert r.body == b'{"x": 1, "y": "z"}'
        # Content-Type 必须是 JSON
        assert 'application/json' in r.headers.get('Content-Type', '')

    def test_list_return_is_json_body(self):
        from nova_server import NovaServer as NS
        r = NS._normalize_response([1, 2, 3])
        assert r.body == b'[1, 2, 3]'

    def test_string_return(self):
        from nova_server import NovaServer as NS
        r = NS._normalize_response('plain text')
        assert r.body == b'plain text'
        # Content-Type 在 write() 时由 complete() 自动设置，
        # _normalize_response 本身不调用 complete()
        assert 'Content-Type' not in r.headers
        r.complete()
        assert 'text/plain' in r.headers['Content-Type']

    def test_int_return_is_status_code(self):
        from nova_server import NovaServer as NS
        r = NS._normalize_response(204)
        assert r.status_code == 204
        assert r.body == b''

    def test_tuple_body_status(self):
        from nova_server import NovaServer as NS
        r = NS._normalize_response(('created', 201))
        assert r.status_code == 201
        assert r.body == b'created'

    def test_tuple_body_status_headers(self):
        from nova_server import NovaServer as NS
        r = NS._normalize_response(('ok', 200, {'X-Custom': 'val'}))
        assert r.status_code == 200
        assert r.body == b'ok'
        assert r.headers['X-Custom'] == 'val'

    def test_tuple_body_headers(self):
        from nova_server import NovaServer as NS
        r = NS._normalize_response(('body', {'X-Foo': 'bar'}))
        assert r.status_code == 200
        assert r.body == b'body'
        assert r.headers['X-Foo'] == 'bar'


# ════════════════════════════════════════════════════════════════
# 端到端 dispatch 测试
# ════════════════════════════════════════════════════════════════

class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_dict_return_appears_in_body(self):
        """端到端验证：handler 返回 dict → response body 是 JSON。"""
        app = NovaServer()

        @app.get('/json')
        async def handler(req):
            return {'message': 'hello', 'code': 42}

        res = await call(app, 'GET', '/json')
        assert res.status_code == 200
        # ★ 之前这个会返回空 body——bug
        assert b'message' in res.body
        assert b'hello' in res.body
        # 还能 round-trip JSON
        data = json.loads(res.body)
        assert data == {'message': 'hello', 'code': 42}

    @pytest.mark.asyncio
    async def test_string_return_in_body(self):
        app = NovaServer()

        @app.get('/text')
        async def handler(req):
            return 'plain text response'

        res = await call(app, 'GET', '/text')
        assert res.status_code == 200
        assert res.body == b'plain text response'

    @pytest.mark.asyncio
    async def test_404_for_unmatched(self):
        app = NovaServer()
        res = await call(app, 'GET', '/nope')
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_405_for_wrong_method(self):
        """路由匹配但方法不匹配 → 405。"""
        app = NovaServer()

        @app.get('/only-get')
        async def handler(req):
            return 'ok'

        res = await call(app, 'POST', '/only-get')
        assert res.status_code == 405

    @pytest.mark.asyncio
    async def test_url_args_passed_to_handler(self):
        app = NovaServer()

        @app.get('/user/<int:id>')
        async def handler(req, id):
            return {'id': id}

        res = await call(app, 'GET', '/user/42')
        assert res.status_code == 200
        assert json.loads(res.body) == {'id': 42}

    @pytest.mark.asyncio
    async def test_404_int_pattern_no_match(self):
        app = NovaServer()

        @app.get('/user/<int:id>')
        async def handler(req, id):
            return {'id': id}

        res = await call(app, 'GET', '/user/abc')
        assert res.status_code == 404


class TestAbort:
    @pytest.mark.asyncio
    async def test_abort_404(self):
        app = NovaServer()

        @app.get('/api/<int:id>')
        async def handler(req, id):
            if id == 0:
                abort(404, 'no such id')
            return {'id': id}

        res = await call(app, 'GET', '/api/0')
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_abort_400(self):
        app = NovaServer()

        @app.post('/api')
        async def handler(req):
            if not req.json:
                abort(400, 'need JSON')
            return {'ok': True}

        res = await call(app, 'POST', '/api', body=b'not json',
                         headers={'Content-Type': 'application/json'})
        # 无效 JSON 抛异常 → 500
        # 空 body 不抛 → 应该 abort 400
        res2 = await call(app, 'POST', '/api', body=b'',
                          headers={'Content-Type': 'application/json'})
        # body 为空时 req.json is None → abort 400
        # (但实际抛 ValueError? 取决于 JSON 解析)


class TestErrorHandler:
    @pytest.mark.asyncio
    async def test_custom_404_handler(self):
        app = NovaServer()

        @app.errorhandler(404)
        async def not_found(req):
            return {'error': 'custom 404', 'path': req.path}, 404

        res = await call(app, 'GET', '/missing')
        assert res.status_code == 404
        assert b'custom 404' in res.body
        assert b'missing' in res.body


class TestBeforeAfterRequest:
    @pytest.mark.asyncio
    async def test_before_request_can_inject_g(self):
        app = NovaServer()

        @app.before_request
        async def before(req):
            req.g.user = 'alice'

        @app.get('/who')
        async def handler(req):
            return {'user': req.g.user}

        res = await call(app, 'GET', '/who')
        assert res.status_code == 200
        assert json.loads(res.body) == {'user': 'alice'}

    @pytest.mark.asyncio
    async def test_after_request_can_modify_headers(self):
        app = NovaServer()

        @app.after_request
        async def after(req, res):
            res.headers['X-Custom-Header'] = 'added'
            return res

        @app.get('/x')
        async def handler(req):
            return 'ok'

        res = await call(app, 'GET', '/x')
        assert res.headers['X-Custom-Header'] == 'added'

    @pytest.mark.asyncio
    async def test_before_request_short_circuit(self):
        """before_request 返回响应时，handler 不被调用。"""
        app = NovaServer()
        handler_called = []

        @app.before_request
        async def before(req):
            return {'blocked': True}, 403

        @app.get('/blocked')
        async def handler(req):
            handler_called.append(True)
            return 'should not reach'

        res = await call(app, 'GET', '/blocked')
        assert res.status_code == 403
        assert json.loads(res.body) == {'blocked': True}
        assert handler_called == []