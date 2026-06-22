"""
test_response.py — Response 对象构造测试
========================================

覆盖：
  - 字符串 body 自动编码
  - bytes body 直传
  - dict / list body 触发 JSON 序列化
  - status_code 默认 200
  - Content-Length / Content-Type 自动设置
  - redirect / send_file 工厂方法
"""
import pytest
from nova_server import Response, redirect, send_file, abort
from nova_server import NovaServer


class TestBasicConstruction:
    def test_empty_default(self):
        r = Response()
        assert r.status_code == 200
        assert r.body == b''

    def test_str_body(self):
        r = Response('hello')
        assert r.body == b'hello'
        assert r.status_code == 200

    def test_bytes_body(self):
        r = Response(b'\\x00\\x01\\x02')
        assert r.body == b'\\x00\\x01\\x02'

    def test_custom_status(self):
        r = Response('created', status_code=201)
        assert r.status_code == 201


class TestJsonAutoSerialize:
    def test_dict_becomes_json(self):
        r = Response({'key': 'value', 'n': 42})
        assert r.body == b'{"key": "value", "n": 42}'
        assert 'application/json' in r.headers.get('Content-Type', '')

    def test_list_becomes_json(self):
        r = Response([1, 2, 3])
        assert r.body == b'[1, 2, 3]'
        assert 'application/json' in r.headers.get('Content-Type', '')

    def test_nested_dict(self):
        r = Response({'a': {'b': {'c': [1, 2, 3]}}})
        assert b'"c"' in r.body
        assert b'[1, 2, 3]' in r.body


class TestEmptyAndNone:
    def test_none_body_with_200_becomes_204(self):
        """None body + status 200 → 升级为 204 No Content。"""
        r = Response(None, 200)
        assert r.status_code == 204

    def test_none_body_with_other_status_kept(self):
        """None body + status 4xx → 保持原状态码。"""
        r = Response(None, 404)
        assert r.status_code == 404


class TestComplete:
    """complete() 在 write() 时自动调用。"""

    def test_content_length_set_for_bytes(self):
        r = Response('hello world')
        r.complete()
        assert r.headers['Content-Length'] == '11'

    def test_content_type_default_for_str(self):
        r = Response('hello')
        r.complete()
        assert 'text/plain' in r.headers['Content-Type']
        assert 'charset=UTF-8' in r.headers['Content-Type']

    def test_custom_headers_preserved(self):
        r = Response('x', headers={'X-Custom': 'value'})
        r.complete()
        assert r.headers['X-Custom'] == 'value'


class TestCookies:
    def test_set_cookie(self):
        r = Response('ok')
        r.set_cookie('session', 'abc', path='/', max_age=3600)
        cookies = r.headers.get('Set-Cookie')
        # MultiDict 把列表直接存储，set_cookie 应该存为 list
        if isinstance(cookies, list):
            cookie_str = cookies[0]
        else:
            cookie_str = cookies
        assert 'session=abc' in cookie_str
        assert 'Path=/' in cookie_str
        assert 'Max-Age=3600' in cookie_str

    def test_delete_cookie(self):
        r = Response('ok')
        r.delete_cookie('session', path='/')
        cookies = r.headers.get('Set-Cookie')
        cookie_str = cookies[0] if isinstance(cookies, list) else cookies
        assert 'session=' in cookie_str
        assert '1970' in cookie_str  # expires 1970
        assert 'Max-Age=0' in cookie_str


class TestRedirect:
    def test_basic_redirect(self):
        r = redirect('/login')
        assert r.status_code == 302
        assert r.headers['Location'] == '/login'

    def test_custom_status(self):
        r = redirect('/new', status_code=301)
        assert r.status_code == 301

    def test_rejects_newline_injection(self):
        """Location 不能含 CRLF（HTTP header 注入）。"""
        with pytest.raises(ValueError):
            redirect('/foo\r\nSet-Cookie: evil=1')


class TestSendFile:
    def test_send_existing_file(self, tmp_path):
        p = tmp_path / 'test.txt'
        p.write_text('hello file')
        r = send_file(str(p))
        assert r.status_code == 200
        # send_file 用 file object 作为 body
        assert hasattr(r.body, 'read')
        r.body.close()  # 清理

    def test_content_type_from_extension(self, tmp_path):
        p = tmp_path / 'style.css'
        p.write_text('body { color: red; }')
        r = send_file(str(p))
        assert 'text/css' in r.headers['Content-Type']
        r.body.close()

    def test_unknown_extension_octet_stream(self, tmp_path):
        p = tmp_path / 'data.xyz'
        p.write_bytes(b'\\x00\\xff')
        r = send_file(str(p))
        assert 'application/octet-stream' in r.headers['Content-Type']
        r.body.close()

    def test_max_age_sets_cache_header(self, tmp_path):
        p = tmp_path / 'a.html'
        p.write_text('<html/>')
        r = send_file(str(p), max_age=300)
        assert 'max-age=300' in r.headers.get('Cache-Control', '')
        r.body.close()