# 工具函数

nova-server 提供的辅助函数。

## `abort(status_code, reason=None)`

抛出 HTTP 异常：

```python
from nova_server import abort

@app.get('/users/<int:id>')
async def get_user(request, id):
    user = db.get(id)
    if user is None:
        abort(404, 'user {} not found'.format(id))
    return user
```

## `redirect(location, status_code=302)`

重定向响应：

```python
from nova_server import redirect

@app.get('/old')
async def old(request):
    return redirect('/new')
```

## `send_file(filename, **kwargs)`

发送文件：

```python
from nova_server import send_file

@app.get('/<path:filename>')
async def static(request, filename):
    return send_file('/static/' + filename, max_age=3600)
```

参数：

| 参数 | 作用 |
|------|------|
| `content_type` | MIME（默认按扩展名） |
| `max_age` | 缓存秒数 |
| `compressed` | Content-Encoding |

## `URLPattern.register_type(name, pattern, parser=None)`

注册自定义 URL 类型：

```python
from nova_server import URLPattern

URLPattern.register_type(
    'hex',
    '[0-9a-fA-F]+',
    parser=lambda v: int(v, 16),
)
```

## 内置类

### `MultiDict`

多值字典（query string、form）：

```python
from nova_server import MultiDict

d = MultiDict()
d['key'] = 'v1'
d['key'] = 'v2'

d['key']            # 'v1'（第一个）
d.getlist('key')    # ['v1', 'v2']
d.get('missing')    # None
```

### `NoCaseDict`

大小写不敏感的 dict（HTTP headers）：

```python
from nova_server import NoCaseDict

d = NoCaseDict({'Content-Type': 'text/plain'})
d['content-type']    # 'text/plain'
d['CONTENT-TYPE']    # 'text/plain'
```

### `AsyncBytesIO`

异步 bytes IO（流式读 body）。

## 编码工具

### `urldecode(s)`

```python
from nova_server import urldecode

urldecode('hello%20world')    # 'hello world'
urldecode(b'a%2Bb')          # 'a+b'（bytes 也行）
```

### `urlencode(s)`

```python
from nova_server import urlencode

urlencode('hello world')      # 'hello+world'
urlencode('a/b?c=d')          # 'a%2Fb%3Fc%3Dd'
```

## 下一步

- [NovaServer](/api/nova-server)
- [Request](/api/request)
- [Response](/api/response)