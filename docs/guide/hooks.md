# 钩子（Hooks）

钩子让你在请求**进入前** / **处理后**自动跑一些代码。常见用途：

- 鉴权
- 记录日志
- 性能监控
- 共享数据

## 三种钩子

| 钩子 | 什么时候跑 |
|------|----------|
| `before_request` | 请求**进入**时（handler 之前） |
| `after_request` | 请求**处理完**时（handler 之后） |
| `after_error_request` | **只有出错时**（4xx / 5xx） |

## before_request

请求进来时第一个跑。可以做：

1. 检查权限
2. 在 `request.g` 上塞数据，handler 里读
3. 直接返回响应（短路）

```python
@app.before_request
async def auth(request):
    # 没带 token → 直接 401，不进 handler
    token = request.headers.get('Authorization', '')
    if not token.startswith('Bearer '):
        return {'error': 'unauthorized'}, 401

    # 把 user 信息塞到 request.g，handler 可以读
    request.g.user = {'name': 'alice'}
```

**关键**：返回响应会**短路**，handler 不会被调用。

## after_request

请求处理完后跑。可以：

1. 加响应头
2. 记录响应时间
3. 统计

```python
import time

@app.after_request
async def add_timing_header(request, response):
    # 计算 handler 耗时
    if hasattr(request, '_start_ms'):
        elapsed = time.ticks_diff(time.ticks_ms(), request._start_ms)
        response.headers['X-Response-Time-Ms'] = str(elapsed)
    return response

@app.before_request
async def record_start(request):
    request._start_ms = time.ticks_ms()
```

**注意**：

- 必须 `return response`
- 错误请求（4xx/5xx）**也**会跑

## after_error_request

只在出错时跑：

```python
@app.after_error_request
async def log_error(request, response):
    # 记录到文件或控制台
    print('[ERR]', request.method, request.path, '→', response.status_code)
    return response
```

## 完整例子：API Key 鉴权

```python
from nova_server import NovaServer

app = NovaServer()

# 假设的 API key 数据库
API_KEYS = {'alice': 'secret-key-1', 'bob': 'secret-key-2'}

@app.before_request
async def check_api_key(request):
    # 根路径和静态文件不要鉴权
    if request.path == '/' or request.path.startswith('/static/'):
        return    # 不返回 = 继续

    # 验证 API Key
    key = request.headers.get('X-API-Key', '')
    for name, valid_key in API_KEYS.items():
        if key == valid_key:
            request.g.user = name
            return    # 鉴权通过

    return {'error': 'invalid API key'}, 401

@app.get('/api/data')
async def data(request):
    return {'data': 'secret stuff', 'user': request.g.user}
```

测试：

## 多个钩子的执行顺序

```
请求进入
  ↓
before_request #1
  ↓
before_request #2
  ↓
URL 匹配
  ↓
handler
  ↓
after_request #2
  ↓
after_request #1
  ↓
响应返回
```

**出错时**：

```
请求进入
  ↓
before_request
  ↓
URL 匹配
  ↓
handler 抛异常
  ↓
errorhandler
  ↓
after_error_request
  ↓
after_request         ← 也会跑！
  ↓
响应返回
```

## 例子：请求日志

```python
import time

@app.before_request
async def start_timer(request):
    request._start_ms = time.ticks_ms()

@app.after_request
async def log_request(request, response):
    elapsed = time.ticks_diff(time.ticks_ms(), request._start_ms)
    print('[{}] {} {} → {} ({} ms)'.format(
        time.time(),                    # 时间戳
        request.method,
        request.path,
        response.status_code,
        elapsed,
    ))
    return response

@app.after_error_request
async def log_error(request, response):
    print('[ERROR] {} {} → {}'.format(
        request.method, request.path, response.status_code))
    return response
```

每次请求都会打日志到控制台。

## request.g 的用法

`request.g` 是 Python 普通对象，可以挂任何属性。请求结束自动清理。

```python
@app.before_request
async def parse_token(request):
    token = request.headers.get('Authorization', '')
    if token:
        request.g.token = token[7:]   # 去掉 "Bearer "
        request.g.user = decode(token)
    else:
        request.g.token = None
        request.g.user = None

@app.get('/profile')
async def profile(request):
    if request.g.user is None:
        return {'error': 'login first'}, 401
    return request.g.user
```

## 钩子本身的错误

如果 `before_request` 自己抛了异常，会被当作普通请求错误处理：

```python
@app.before_request
async def buggy(request):
    raise ValueError('oops')    # → 500
```

要小心。生产环境可以在钩子里加 try/except。

## 小结

| 钩子 | 用途 |
|------|------|
| `before_request` | 鉴权、注入数据、短路 |
| `after_request` | 加响应头、记录耗时 |
| `after_error_request` | 错误日志、告警 |
| `request.g` | 请求级共享数据 |

## 下一步

- [实时推送](/guide/async-streaming)
- [静态文件](/guide/static-files)
- [部署到 ESP32](/guide/deploy-to-esp32)