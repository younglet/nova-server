# 第 2 步：加更多接口

一个 `app` 可以注册很多个接口。每个接口用 `@app.get(...)` 单独声明。

## 例：3 个 URL

```python
from nova_server import NovaServer

app = NovaServer()

@app.get('/')
async def index(request):
    return 'Home page'

@app.get('/about')
async def about(request):
    return 'About page'

@app.get('/contact')
async def contact(request):
    return 'Contact: hello@example.com'

app.run(port=80)
```

| 访问 | 显示 |
|------|------|
| `/` | `Home page` |
| `/about` | `About page` |
| `/contact` | `Contact: hello@example.com` |

## 各种 HTTP 方法

| 方法 | 装饰器 | 用途 |
|------|--------|------|
| GET | `@app.get(...)` | 读数据 |
| POST | `@app.post(...)` | 发数据 / 控制 |
| PUT | `@app.put(...)` | 全量更新 |
| PATCH | `@app.patch(...)` | 部分更新 |
| DELETE | `@app.delete(...)` | 删除 |

简单 REST API 例子：

```python
@app.get('/api/users')
async def list_users(request):
    return {'users': [{'id': 1, 'name': 'Alice'}]}

@app.post('/api/users')
async def create_user(request):
    name = request.json.get('name')
    return {'id': 2, 'name': name}

@app.get('/api/users/<int:id>')
async def get_user(request, id):
    return {'id': id, 'name': 'Alice'}

@app.delete('/api/users/<int:id>')
async def delete_user(request, id):
    return {'deleted': id}
```

POST 详细看 [POST 请求](/guide/post-requests)。

## 函数名要唯一

每个 handler 的函数名不能重复，否则**后注册的覆盖前面的**：

```python
@app.get('/a')
async def handler(request):
    return 'A'

@app.get('/b')
async def handler(request):    # ← 覆盖上面那个
    return 'B'
```

**不会报错**，但 `/a` 也会返回 `'B'`。

好习惯是函数名能看出功能：

```python
@app.get('/users')
async def list_users(request):    # 一看是"列出"
    ...

@app.get('/users/<int:id>')
async def get_user(request, id):   # 一看是"取单个"
    ...
```

## 路径匹配规则

严格匹配：

| 你写的 | 请求 | 命中 |
|--------|------|------|
| `/about` | `/about` | ✅ |
| `/about` | `/about/` | ❌ |
| `/about` | `/ABOUT` | ❌ |
| `/about` | `/about/me` | ❌ |

兼容两种写法，注册两个：

```python
@app.get('/about')
@app.get('/about/')
async def about(request):
    return 'about'
```

## 调试：列出所有路由

```python
@app.get('/debug/routes')
async def debug_routes(request):
    return {
        'count': len(app.url_map),
        'routes': [
            {'method': m[0], 'path': p.url_pattern, 'handler': h.__name__}
            for m, p, h, _, _ in app.url_map
        ],
    }
```

访问 `/debug/routes` 能看到所有接口。

## 真实 IoT 应用怎么组织？

实际项目（智能灯、温湿度计、设备控制面板）会有：

- `GET /` — 仪表盘页面
- `GET /api/state` — 读状态
- `POST /api/power` — 控制电源
- `POST /api/settings` — 改设置

完整的智能灯案例看 [示例 02](/examples/02-sensors)。这里只演示怎么**注册多个接口**这个动作。

## 下一步

- [URL 参数](/guide/url-parameters) — 让路径里有变量
- [返回 JSON](/guide/return-json) — 数据接口标准
- [POST 请求](/guide/post-requests) — 收数据
- [示例 02](/examples/02-sensors) — 完整 IoT 案例