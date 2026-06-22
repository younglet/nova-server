# 错误处理

Web 接口不总是成功。404（路径不存在）、400（请求格式错）、500（服务器错）这些状态码要会返回。

## abort() — 主动报错

```python
from nova_server import abort

@app.get('/users/<int:id>')
async def get_user(request, id):
    user = db.get(id)
    if user is None:
        abort(404, 'user {} not found'.format(id))
    return user
```

`abort(状态码, 错误说明)` 直接抛出异常，框架捕获后返回对应 HTTP 状态码。

## 状态码速查

| 状态码 | 含义 | 什么时候用 |
|--------|------|----------|
| 200 | OK | 成功 |
| 201 | Created | 创建成功（POST） |
| 400 | Bad Request | 请求格式错（缺字段、JSON 解析失败） |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 没权限 |
| 404 | Not Found | 资源不存在 |
| 405 | Method Not Allowed | 用错 HTTP 方法（GET 接口用 POST 访问） |
| 500 | Internal Server Error | 服务器内部错 |

## 完整的错误处理例子

```python
from nova_server import NovaServer, abort

app = NovaServer()

USERS = {
    1: {'name': 'Alice'},
    2: {'name': 'Bob'},
}

@app.get('/users/<int:id>')
async def get_user(request, id):
    # 用 abort() 报错
    if id not in USERS:
        abort(404, 'user {} not found'.format(id))
    return USERS[id]

@app.post('/users')
async def create_user(request):
    # 没 body
    if request.json is None:
        abort(400, 'need JSON body')

    # 缺字段
    name = request.json.get('name')
    if not name:
        abort(400, 'missing "name" field')

    # 创建
    new_id = max(USERS.keys()) + 1
    USERS[new_id] = {'name': name}
    return {'id': new_id, 'name': name}, 201

@app.delete('/users/<int:id>')
async def delete_user(request, id):
    if id not in USERS:
        abort(404)
    del USERS[id]
    return {'deleted': id}

app.run(port=80)
```

测试：

## 自定义 404 页面

默认 404 返回纯文本 `"Not found"`。可以自定义：

```python
@app.errorhandler(404)
async def not_found(request):
    return {
        'error': 'not found',
        'path': request.path,
        'method': request.method,
    }, 404
```

现在访问 `/nope`：

可以注册任何状态码：

```python
@app.errorhandler(500)
async def server_error(request):
    return {'error': 'something broke'}, 500

@app.errorhandler(405)
async def method_not_allowed(request):
    return {'error': 'use GET, not POST'}, 405
```

## 自定义异常类

可以定义自己的异常类，注册到 errorhandler：

```python
class DeviceOffline(Exception):
    """设备不在线。"""

@app.errorhandler(DeviceOffline)
async def handle_offline(request, exc):
    return {'error': 'device offline', 'detail': str(exc)}, 503

# 用法
@app.get('/api/sensor/<int:channel>')
async def read_sensor(request, channel):
    if channel == 0:
        raise DeviceOffline('channel 0 is disconnected')
    return {'value': read(channel)}
```

## 调试：handler 抛异常

如果 handler 里代码出错了（比如除零），默认会返回 500：

```python
@app.get('/divide/<int:a>/<int:b>')
async def divide(request, a, b):
    return {'result': a / b}    # b=0 会 ZeroDivisionError
```

测试 `/divide/10/0`，会看到 500 错误（控制台打印 traceback）。

要自定义 500 处理：

```python
@app.errorhandler(500)
async def err_500(request):
    return {'error': 'internal error'}, 500
```

## try / except 在 handler 里

也可以在 handler 里自己捕获异常：

```python
@app.get('/api/safe-read')
async def safe_read(request):
    try:
        value = read_sensor()
    except OSError as e:
        return {'error': str(e)}, 503
    return {'value': value}
```

## 钩子里的错误处理

`after_error_request` 钩子**只在出错时**调用：

```python
@app.after_error_request
async def log_error(request, response):
    print('[ERR]', request.method, request.path, '→', response.status_code)
    return response
```

适合做错误日志。

## 小结

| 需求 | 写法 |
|------|------|
| 主动报错 | `abort(404, 'msg')` |
| 返回 JSON + 状态码 | `return {...}, 400` |
| 自定义 404 | `@app.errorhandler(404)` |
| 自定义异常类 | 定义类 + `@app.errorhandler(MyException)` |
| 错误日志 | `@app.after_error_request` |

## 下一步

- [钩子](/guide/hooks) — before/after request
- [Request 对象](/guide/request-object)
- [Response 对象](/guide/response-object)