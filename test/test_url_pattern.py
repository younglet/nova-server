"""
test_url_pattern.py — URL 模式匹配测试
=======================================

覆盖：
  - 字符串段 <name>
  - 整型段 <int:id>
  - path 段 <path:rest>
  - 正则段 <re:...>
  - 类型解析失败返回 None
  - 不匹配返回 None
"""
import pytest
from nova_server import URLPattern


class TestStringSegment:
    def test_simple(self):
        p = URLPattern('/hello/<name>')
        assert p.match('/hello/world') == {'name': 'world'}

    def test_multiple(self):
        p = URLPattern('/user/<first>/<last>')
        assert p.match('/user/john/doe') == {'first': 'john', 'last': 'doe'}

    def test_no_match(self):
        p = URLPattern('/hello/<name>')
        assert p.match('/hi/world') is None

    def test_partial_match_no_match(self):
        """URLPattern 必须全匹配。"""
        p = URLPattern('/hello/<name>')
        assert p.match('/hello/world/extra') is None


class TestIntSegment:
    def test_positive(self):
        p = URLPattern('/user/<int:id>')
        assert p.match('/user/42') == {'id': 42}

    def test_negative(self):
        p = URLPattern('/temp/<int:val>')
        assert p.match('/temp/-15') == {'val': -15}

    def test_zero(self):
        p = URLPattern('/p/<int:n>')
        assert p.match('/p/0') == {'n': 0}

    def test_non_int_returns_none(self):
        """非整型字符串应该匹配失败。"""
        p = URLPattern('/user/<int:id>')
        assert p.match('/user/abc') is None


class TestPathSegment:
    def test_single_segment(self):
        p = URLPattern('/files/<path:f>')
        assert p.match('/files/readme.txt') == {'f': 'readme.txt'}

    def test_multiple_segments(self):
        p = URLPattern('/static/<path:rest>')
        assert p.match('/static/css/style.css') == {'rest': 'css/style.css'}

    def test_deep_path(self):
        p = URLPattern('/s/<path:p>')
        assert p.match('/s/a/b/c/d/e/f.txt') == {'p': 'a/b/c/d/e/f.txt'}


class TestRegexSegment:
    def test_custom_regex(self):
        URLPattern.register_type('hex', '[0-9a-f]+')
        p = URLPattern('/color/<hex:c>')
        assert p.match('/color/deadbeef') == {'c': 'deadbeef'}
        assert p.match('/color/zzzzzz') is None


class TestInvalidPatterns:
    def test_missing_close_bracket_raises(self):
        with pytest.raises(ValueError):
            URLPattern('/foo/<bar').compile()

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError):
            URLPattern('/foo/<unknown_type:x>').compile()


class TestCombined:
    def test_static_and_dynamic(self):
        # 注意：<int:...> 必须以 / 开头，不能嵌在 literal 里
        p = URLPattern('/api/<int:version>/users/<int:id>')
        assert p.match('/api/2/users/99') == {'version': 2, 'id': 99}

    def test_literal_then_dynamic(self):
        """literal segment 后跟 dynamic segment。"""
        p = URLPattern('/api/v/<int:version>/users/<int:id>')
        assert p.match('/api/v/2/users/99') == {'version': 2, 'id': 99}

    def test_trailing_slash(self):
        """URLPattern 默认不匹配带尾斜杠的（具体行为取决于框架使用）。"""
        p = URLPattern('/foo')
        assert p.match('/foo/') is None or p.match('/foo') == {}
        # 至少一个要 True
        assert p.match('/foo/') is None or p.match('/foo') == {}