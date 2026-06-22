# POST 请求

POST 用来**让客户端发送数据**给服务器。比如前端表单、App 注册、控制命令。

## GET vs POST

| | GET | POST |
|--|-----|-----|
| 用途 | 读数据 | 发数据 |
| 数据放哪 | URL `?` 后 | 请求 body |
| 适合 | 查东西 | 创建 / 更新 / 命令 |
| 浏览器能直接发 | ✅ 地址栏 | ❌ 要 fetch / form |

## 一个例子：控制 LED

```python
from nova_server import NovaServer
from machine import Pin

app = NovaServer()
_led = Pin(2, Pin.OUT)

@app.post('/led')
async def led_control(request):
    """客户端发 {"state": "on"} 或 {"state": "off"} 来控制 LED。"""
    data = request.json
    if not data or data.get('state') not in ('on', 'off'):
        return {'error': 'state must be "on" or "off"'}, 400

    state = data['state']
    _led.value(1 if state == 'on' else 0)
    return {'led': state}

app.run(port=80)
```

## 怎么测试 POST

的 `-X POST`：

| 参数 | 含义 |
|------|------|
| `-X POST` | 用 POST 方法 |
| `-H 'Content-Type: application/json'` | 告诉服务器 body 是 JSON |
| `-d '{...}'` | body 内容 |

不带 `-H` 也行，nova-server 看 body 是 JSON 就当 JSON 处理。

服务器返回：

```json
{"led": "on"}
```

## 读 POST 的数据

`request.json` 自动解析 body 成 dict：

```python
@app.post('/api/users')
async def create_user(request):
    data = request.json       # body 解析成 dict
    name = data.get('name')    # 取字段
    age = data.get('age', 0)   # 不存在用 0

    # ... 保存到数据库 ...

    return {'id': 1, 'name': name, 'age': age}
```

客户端发：

服务器返回：

```json
{"id": 1, "name": "Alice", "age": 30}
```

## 没发 JSON body 怎么办？

`request.json` 在没 body 或 body 不是 JSON 时返回 `None`：

```python
@app.post('/api/users')
async def create_user(request):
    if request.json is None:
        return {'error': 'need JSON body'}, 400
    # ...
```

## 表单（HTML form）

如果前端用 `<form>` 提交，会发 `application/x-www-form-urlencoded` 格式：

```python
@app.post('/login')
async def login(request):
    username = request.form.get('username')
    password = request.form.get('password')

    if check_password(username, password):
        return {'ok': True}
    return {'error': 'invalid'}, 401
```

HTML：

```html
<form method="POST" action="/login">
    <input name="username">
    <input name="password" type="password">
    <button type="submit">登录</button>
</form>
```

**JSON 更常用**，但表单在浏览器原生提交时还是有用。

## 真实例子：保存配置

```python
@app.post('/api/config')
async def save_config(request):
    data = request.json
    if not data:
        return {'error': 'need JSON body'}, 400

    # 保存到文件
    with open('/config.json', 'w') as f:
        f.write(json.dumps(data))

    return {'saved': True}

@app.get('/api/config')
async def get_config(request):
    """读刚才保存的配置。"""
    try:
        with open('/config.json') as f:
            return json.loads(f.read())
    except OSError:
        return {}
```

## 一个接口两个方法

同一个路径，GET 读、POST 写：

```python
@app.get('/counter')
async def get_counter(request):
    """读当前计数。"""
    return {'value': _counter['value']}

@app.post('/counter')
async def increment_counter(request):
    """加 1。"""
    _counter['value'] += 1
    return {'value': _counter['value']}
```

测试：

## 不同 HTTP 方法的用法

| 方法 | 典型场景 | 例子 |
|------|---------|------|
| GET | 读 | `/users` |
| POST | 创建 | `/users`（提交新用户数据） |
| PUT | 全量替换 | `/users/1`（替换整个用户） |
| PATCH | 部分更新 | `/users/1`（只更新 age） |
| DELETE | 删除 | `/users/1` |

实际项目 GET 和 POST 用得最多，其他三个较少。

## 小结

| 概念 | 写法 |
|------|------|
| 注册 POST | `@app.post('/路径')` |
| 读 JSON body | `data = request.json` |
| body 不是 JSON | `request.json` 是 `None` |
| 读 form body | `data = request.form` |

## 下一步

- [错误处理](/guide/errors) — 返回 4xx / 5xx
- [Request 对象](/guide/request-object)
- [Response 对象](/guide/response-object)