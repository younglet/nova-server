"""
test_request.py — Request 对象解析测试
======================================

覆盖：
  - URL 路径 + query string 解析
  - Headers (case-insensitive)
  - Cookies
  - JSON body
  - Form body (urlencoded)
  - Content-Length / Content-Type
"""
import pytest
from nova_server import NovaServer
from test.conftest import make_request


@pytest.fixture
def fresh_app():
    return NovaServer()


class TestPathParsing:
    def test_simple_path(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'GET', '/foo')
        assert req.path == '/foo'
        assert req.query_string is None
        assert req.args == {}

    def test_path_with_query(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'GET',
                           '/search?q=hello&page=2')
        assert req.path == '/search'
        # MultiDict 行为：__getitem__ 返回第一个值
        assert req.args['q'] == 'hello'
        assert req.args['page'] == '2'
        # getlist 返回所有值
        assert req.args.getlist('q') == ['hello']

    def test_path_with_empty_query(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'GET', '/foo?')
        assert req.path == '/foo'
        assert req.args == {}

    def test_query_with_url_encoding(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'GET',
                           '/s?q=hello%20world&t=a%2Bb')
        assert req.args['q'] == 'hello world'
        assert req.args['t'] == 'a+b'


class TestHeaders:
    def test_basic(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'GET', '/',
                           headers={'X-Foo': 'bar'})
        assert req.headers['X-Foo'] == 'bar'

    def test_case_insensitive(self, fresh_app):
        """HTTP headers 是大小写不敏感的。"""
        req = make_request(fresh_app, ('127.0.0.1', 1), 'GET', '/',
                           headers={'Content-Type': 'text/plain'})
        assert req.headers['content-type'] == 'text/plain'
        assert req.headers['CONTENT-TYPE'] == 'text/plain'

    def test_content_length(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'POST', '/',
                           body=b'12345')
        assert req.content_length == 5


class TestCookies:
    def test_single(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'GET', '/',
                           headers={'Cookie': 'session=abc123'})
        assert req.cookies == {'session': 'abc123'}

    def test_multiple(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'GET', '/',
                           headers={'Cookie': 'a=1; b=2; c=3'})
        assert req.cookies == {'a': '1', 'b': '2', 'c': '3'}

    def test_empty_value(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'GET', '/',
                           headers={'Cookie': 'flag'})
        assert req.cookies == {'flag': ''}


class TestJsonBody:
    def test_valid_json(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'POST', '/api',
                           body=b'{"x": 1, "y": "z"}',
                           headers={'Content-Type': 'application/json'})
        assert req.json == {'x': 1, 'y': 'z'}

    def test_wrong_content_type_returns_none(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'POST', '/api',
                           body=b'{"x":1}',
                           headers={'Content-Type': 'text/plain'})
        assert req.json is None

    def test_no_content_type_returns_none(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'POST', '/api',
                           body=b'{"x":1}')
        assert req.json is None


class TestFormBody:
    def test_urlencoded(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'POST', '/api',
                           body=b'name=Alice&age=30',
                           headers={'Content-Type':
                                    'application/x-www-form-urlencoded'})
        assert req.form['name'] == 'Alice'
        assert req.form['age'] == '30'

    def test_with_charset(self, fresh_app):
        """Content-Type 带 charset 参数也应该被识别为 form。"""
        req = make_request(fresh_app, ('127.0.0.1', 1), 'POST', '/api',
                           body=b'a=1',
                           headers={'Content-Type':
                                    'application/x-www-form-urlencoded; charset=UTF-8'})
        assert req.form['a'] == '1'


class TestRequestG:
    """req.g 是请求级共享容器（before_request 可注入）。"""

    def test_g_attribute(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'GET', '/')
        req.g.user_id = 42
        assert req.g.user_id == 42

    def test_after_request_handlers_list(self, fresh_app):
        req = make_request(fresh_app, ('127.0.0.1', 1), 'GET', '/')
        assert isinstance(req.after_request_handlers, list)
        assert len(req.after_request_handlers) == 0

        @req.after_request
        def hook(r, response):
            return response

        assert len(req.after_request_handlers) == 1