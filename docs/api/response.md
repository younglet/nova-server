# Response

响应对象。多数时候直接返回字符串/dict 就够了，需要精细控制时显式构造。

完整使用看 [Response 对象指南](/guide/response-object)。

## 构造

```python
from nova_server import Response

response = Response(
    body='hello',                # 响应内容
    status_code=200,             # 状态码
    headers={'X-Foo': 'bar'},    # 自定义头
    reason=None,                 # 状态 reason
)
```

## 自动返回

handler 直接返回值（多数情况）：

```python
# 字符串 → text/plain
return 'hello'

# dict / list → application/json
return {'k': 'v'}
```

## 元组返回

```python
# (body, status_code)
return {'error': 'not found'}, 404

# (body, status_code, headers)
return {'data': '...'}, 200, {'X-Custom': 'value'}
```

## 方法

### `response.set_cookie(name, value, **kwargs)`

```python
response.set_cookie('session', 'abc', max_age=3600, http_only=True)
```

参数：

| 参数 | 作用 |
|------|------|
| `path` | cookie 路径 |
| `domain` | cookie 域 |
| `expires` | 过期时间（datetime 对象） |
| `max_age` | 几秒后过期 |
| `secure` | 仅 HTTPS 发 |
| `http_only` | 防 JS 读取 |
| `partitioned` | CHIPS（第三方 cookie 隔离） |

### `response.delete_cookie(name, **kwargs)`

```python
response.delete_cookie('session', path='/')
```

实际是设过期时间为 1970 + Max-Age=0，告诉客户端删除。

## 工厂函数

### `redirect(location, status_code=302)`

```python
from nova_server import redirect

return redirect('/new')            # 302
return redirect('/new', 301)      # 301 永久
```

### `send_file(filename, **kwargs)`

```python
from nova_server import send_file

return send_file('/static/index.html')
return send_file('/static/style.css', max_age=3600)
```

支持的扩展名（自动 Content-Type）：

| 扩展 | MIME |
|------|------|
| `.html`, `.htm` | text/html |
| `.css` | text/css |
| `.js` | application/javascript |
| `.json` | application/json |
| `.png` | image/png |
| `.jpg`, `.jpeg` | image/jpeg |
| `.gif` | image/gif |
| `.svg` | image/svg+xml |
| `.txt` | text/plain |
| 其他 | application/octet-stream |

## 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `body` | bytes 或 generator | 响应 body |
| `status_code` | int | HTTP 状态码 |
| `headers` | NoCaseDict | 响应头 |
| `reason` | str | 状态 reason |

## 流式响应

传入 async generator：

```python
@app.get('/stream')
async def stream(request):
    async def gen():
        for i in range(60):
            yield 'data: {}\n\n'.format(i)
            await asyncio.sleep(1)
    return Response(
        gen(),
        headers={'Content-Type': 'text/event-stream'},
    )
```

## 下一步

- [Response 对象指南](/guide/response-object)：详细使用
- [NovaServer](/api/nova-server)
- [Request](/api/request)