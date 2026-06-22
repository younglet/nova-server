# Response 对象

handler 返回什么，框架就返回什么给客户端。多数时候直接返回字符串或 dict 就够了。

## 直接返回（最常用）

```python
@app.get('/text')
async def text(request):
    return 'hello'                  # → Content-Type: text/plain

@app.get('/json')
async def json(request):
    return {'k': 'v'}               # → Content-Type: application/json
```

## 返回 JSON + 状态码

```python
@app.get('/items/<int:id>')
async def get_item(request, id):
    item = db.get(id)
    if item is None:
        return {'error': 'not found'}, 404    # JSON + 404
    return item, 200                          # JSON + 200
```

## 显式 Response 对象

需要更精细控制时（比如设特定 header、状态码、cookie）：

```python
from nova_server import Response

@app.get('/custom')
async def custom(request):
    response = Response(
        body='hi',
        status_code=201,
        headers={'X-Custom': 'value'},
    )
    response.set_cookie('session', 'abc', max_age=3600)
    return response
```

## Response 构造函数

```python
Response(
    body='',                    # 响应内容（str/bytes/async generator）
    status_code=200,            # HTTP 状态码
    headers=None,               # 自定义 headers（dict）
    reason=None,                # 状态 reason（如 'Created'）
)
```

## 常用方法

### `set_cookie(cookie, value, ...)`

```python
response = Response('ok')
response.set_cookie('session', 'abc', max_age=3600)
response.set_cookie('theme', 'dark', path='/', secure=True)
```

常用参数：

| 参数 | 作用 |
|------|------|
| `path` | cookie 路径 |
| `max_age` | 几秒后过期 |
| `expires` | 过期时间（datetime 对象） |
| `secure` | 仅 HTTPS 发 |
| `http_only` | 防 JS 读取（防 XSS） |

### `delete_cookie(cookie, ...)`

```python
response.delete_cookie('session', path='/')
```

实际是设过期时间为 1970 + Max-Age=0，告诉客户端删除。

### `complete()`

自动设 Content-Length 和 Content-Type。**正常不用调**，框架在 write 时自动调。

## 重定向

用工厂函数：

```python
from nova_server import redirect

@app.get('/old')
async def old(request):
    return redirect('/new')              # 302

@app.get('/permanent')
async def permanent(request):
    return redirect('/new', 301)        # 301 永久
```

## 发送文件

```python
from nova_server import send_file

@app.get('/<path:filename>')
async def static(request, filename):
    return send_file('/static/' + filename)
```

自动根据扩展名设 Content-Type：

| 扩展 | MIME |
|------|------|
| `.html` | text/html |
| `.css` | text/css |
| `.js` | application/javascript |
| `.json` | application/json |
| `.png` | image/png |
| `.txt` | text/plain |
| 其他 | application/octet-stream |

加缓存控制：

```python
return send_file('/static/' + filename, max_age=3600)  # 缓存 1 小时
```

## 流式响应

返回 async generator 就是流式：

```python
@app.get('/stream')
async def stream(request):
    async def gen():
        for i in range(60):
            yield 'data: {}\n\n'.format(i)
            await asyncio.sleep(1)
    return Response(gen(), headers={'Content-Type': 'text/event-stream'})
```

完整示例看 [实时推送](/guide/async-streaming)。

## 三种返回值对比

```python
# 1. 字符串
@app.get('/a')
async def a(request):
    return 'hi'                    # 200 + text/plain + Content-Length

# 2. dict / list
@app.get('/b')
async def b(request):
    return {'k': 'v'}              # 200 + application/json + Content-Length

# 3. Response 对象
@app.get('/c')
async def c(request):
    return Response('hi', status_code=201, headers={'X-Foo': 'bar'})
    # ↑ 201 + text/plain + X-Foo 头
```

## 完整例子：带 cookie 的登录

```python
from nova_server import NovaServer, Response

app = NovaServer()

USERS = {'alice': 'secret123'}

@app.post('/login')
async def login(request):
    data = request.json
    if not data:
        return {'error': 'need JSON body'}, 400

    username = data.get('username')
    password = data.get('password')

    if USERS.get(username) != password:
        return {'error': 'invalid'}, 401

    # 登录成功 → 设 cookie
    response = Response({'ok': True})
    response.set_cookie('user', username, max_age=3600, http_only=True)
    return response

@app.get('/me')
async def me(request):
    user = request.cookies.get('user')
    if not user:
        return {'error': 'not logged in'}, 401
    return {'user': user}

@app.post('/logout')
async def logout(request):
    response = Response({'ok': True})
    response.delete_cookie('user', path='/')
    return response
```

测试：

## 小结

| 需求 | 写法 |
|------|------|
| 返回字符串 | `return '...'` |
| 返回 JSON | `return {...}` 或 `return [...]` |
| 返回 + 状态码 | `return {...}, 404` |
| 重定向 | `return redirect('/url')` |
| 文件 | `return send_file('/path')` |
| 自定义 headers / cookie | 用 `Response` 对象 |

## 下一步

- [钩子](/guide/hooks)
- [静态文件](/guide/static-files)
- [实时推送](/guide/async-streaming)