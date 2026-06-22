# URLPattern

URL 模式匹配。通常通过 `@app.get('/path/<int:id>')` 装饰器间接使用。

## URL 模式语法

| 语法 | 匹配 | 类型 |
|------|------|------|
| `<name>` | 非 `/` 字符串 | str |
| `<int:id>` | 整数 | int |
| `<path:rest>` | 含 `/` 路径 | str |
| `<re:...>` | 自定义正则 | str |

## 直接使用

```python
from nova_server import URLPattern

p = URLPattern('/users/<int:id>')
p.match('/users/42')         # {'id': 42}
p.match('/users/abc')        # None

p = URLPattern('/files/<path:filename>')
p.match('/files/css/a.css')  # {'filename': 'css/a.css'}
```

## 注册自定义类型

```python
from nova_server import URLPattern

URLPattern.register_type('hex', '[0-9a-fA-F]+')

@app.get('/color/<hex:c>')
async def color(request, c):
    return {'color': '#' + c.upper()}
```

带 parser 自动转值：

```python
URLPattern.register_type(
    'hex',
    '[0-9a-fA-F]+',
    parser=lambda v: int(v, 16),
)
```

`c` 直接就是 int。

## 完整匹配

路径严格匹配，不忽略尾部：

```python
p = URLPattern('/foo')
p.match('/foo')    # 命中
p.match('/foo/')   # None（trailing slash）
```

## 错误

```python
URLPattern('/foo/<bar')        # ValueError（没闭合）
URLPattern('/foo/<unknown:x>') # ValueError（类型不存在）
```

## 下一步

- [URL 参数指南](/guide/url-parameters)
- [NovaServer](/api/nova-server)