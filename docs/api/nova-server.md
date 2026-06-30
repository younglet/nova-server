# NovaServer

主类。管理所有路由、钩子、错误处理。

## 导入

```python
from nova_server import NovaServer
```

## 创建

```python
app = NovaServer()
```

参数：

| 参数 | 默认 | 说明 |
|------|------|------|
| `host` | `'0.0.0.0'` | 默认监听地址。`run()` / `start_server()` 不传时使用 |
| `port` | `80` | 默认监听端口（HTTP 标准）。`run()` / `start_server()` 不传时使用 |
| `debug` | `False` | 调试模式：开则打印启动横幅 + 每个请求的访问日志 |
| `auto_gc` | `True` | 请求前后自动 GC（heap 低时） |
| `gc_threshold_kb` | `10` | 剩余 heap 低于此值（KB）触发 GC |

关掉自动 GC：

```python
app = NovaServer(auto_gc=False)
```

PC 端开发想用 5000 端口（避免和系统 80 端口冲突）：

```python
app = NovaServer(port=5000)
```

## 路由装饰器

### `app.get(path)`

注册 GET 路由：

```python
@app.get('/users/<int:id>')
async def handler(request, id):
    return {'id': id}
```

### `app.post(path)`

注册 POST 路由：

```python
@app.post('/users')
async def create_user(request):
    return {'id': 1, **request.json}
```

### `app.put(path)` / `app.patch(path)` / `app.delete(path)`

```python
@app.put('/users/<int:id>')
async def update(request, id):
    ...

@app.delete('/users/<int:id>')
async def delete(request, id):
    ...
```

### `app.route(path, methods=[...])`

一次注册多个方法：

```python
@app.route('/items', methods=['GET', 'POST'])
async def items(request):
    if request.method == 'GET':
        return list_items()
    return create_item(request.json)
```

通常一个方法一个装饰器更清晰。

## 钩子

### `app.before_request(func)`

请求**进入**前调用。可以：

- 检查权限
- 在 `request.g` 塞数据
- 直接返回响应（**短路**）

```python
@app.before_request
async def auth(request):
    token = request.headers.get('Authorization', '')
    if not token:
        return {'error': 'unauthorized'}, 401
    request.g.user = decode(token)
```

### `app.after_request(func)`

请求**处理后**调用（成功失败都跑）：

```python
@app.after_request
async def add_header(request, response):
    response.headers['X-Server'] = 'nova-server'
    return response
```

### `app.after_error_request(func)`

**只有出错时**调用：

```python
@app.after_error_request
async def log_error(request, response):
    print('[ERR]', request.path, '→', response.status_code)
    return response
```

### `app.errorhandler(status_or_exception)`

为状态码或异常注册处理器：

```python
@app.errorhandler(404)
async def not_found(request):
    return {'error': 'not found'}, 404

class MyError(Exception): pass

@app.errorhandler(MyError)
async def handle_my_error(request, exc):
    return {'error': str(exc)}, 400
```

## 启动

### `app.run(host=None, port=None, debug=None)`

阻塞启动（最简单）：

```python
app.run()                              # 用 NovaServer() 设置：0.0.0.0:80, debug=False
app.run(host='0.0.0.0', port=80)       # 显式指定
app.run(debug=True)                    # 调试：每个请求打一行日志
app = NovaServer(debug=True); app.run()  # 也能走 debug=True（不被 start_server 覆盖）
```

参数：

| 参数 | 默认 | 说明 |
|------|------|------|
| `host` | `app.host`（构造时设的） | 监听地址 |
| `port` | `app.port`（构造时设的，默认 80） | 端口 |
| `debug` | `app.debug`（构造时设的，默认 False） | `True` 时启动横幅 + 每个请求日志：`[14:30:21] GET /hello 200 (5ms)`。★ 不传则沿用构造函数设置 |

不传任何参数时使用 `NovaServer()` 构造函数里设的 `host`/`port`，默认是 `0.0.0.0:80`。

**启动后总会打印一行**（不管 `debug` 是否打开），并优先显示 LAN IP（WiFi 已连时）：
```
NovaServer running on http://192.168.1.42:80/ (debug=False)
  (listening on 0.0.0.0:80, reachable from LAN at 192.168.1.42:80)
```

LAN IP 探测原理：
- **MicroPython ESP32**：读 `network.WLAN(network.STA_IF).ifconfig()[0]`
- **CPython**：用 UDP socket 探测连接 8.8.8.8（不发包，读 `getsockname()`）
- 探测失败时回落到 host（如 `0.0.0.0`），不崩溃

### `await app.start_server(host=None, port=None, debug=None)`

异步启动（要用后台任务时）。参数同样回退到构造函数：

```python
import asyncio

async def main():
    asyncio.create_task(background_task())
    await app.start_server()           # 用 NovaServer() 里设的 host/port/debug
    await app.start_server(debug=True) # 启动时打开请求日志

asyncio.run(main())
```

### `app.shutdown()`

关闭 server：

```python
app.shutdown()
```

## 子应用挂载

### `app.mount(subapp, url_prefix='')`

```python
admin = NovaServer()

@admin.get('/dashboard')
async def dashboard(request):
    return 'admin'

main_app = NovaServer()

@main_app.mount(admin, url_prefix='/admin')

# GET /admin/dashboard → 'admin'
```

## 工具函数

### `abort(status_code, reason=None)`

抛 HTTP 异常中断 handler：

```python
from nova_server import abort

@app.get('/users/<int:id>')
async def get_user(request, id):
    user = db.get(id)
    if user is None:
        abort(404, 'user {} not found'.format(id))
    return user
```

## URLPattern 自定义类型

```python
from nova_server import URLPattern

URLPattern.register_type(
    name='hex',
    pattern='[0-9a-fA-F]+',
    parser=lambda v: int(v, 16),   # 可选：转换函数
)

@app.get('/color/<hex:c>')
async def color(request, c):
    return {'color': c}
```

## 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `url_map` | list | 路由列表 |
| `before_request_handlers` | list | before 钩子 |
| `after_request_handlers` | list | after 钩子 |
| `after_error_request_handlers` | list | 错误钩子 |
| `error_handlers` | dict | 错误处理器 |

调试时打印所有路由：

```python
for methods, pattern, handler, _, _ in app.url_map:
    print(methods, pattern.url_pattern, '→', handler.__name__)
```

## 下一步

- [Request 对象](/api/request)
- [Response 对象](/api/response)
- [URLPattern](/api/url-pattern)