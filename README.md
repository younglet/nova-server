# NovaServer

> **纯 MicroPython** 异步微型 Web 框架。~42KB 单文件 · 零依赖 · 专为 ESP32 优化。

**nova-server** 是 [nova-frontend](..) 家族的第 5 个成员——唯一一个**后端**。
配合 [novajs](..) / [nova-style](..) / [nova-ui](..) / [nova-chart](../nova-chart) 四件套，
在 ESP32 上提供完整的 IoT 全栈能力：嵌入式 HTTP server 在前，nova-* 前端页面在后。

```python
from nova_server import NovaServer

app = NovaServer()                    # 默认 host='0.0.0.0', port=80

@app.get('/hello/<name>')
async def hello(req, name):
    return f'Hello, {name}!'

if __name__ == '__main__':
    app.run(debug=True)               # 0.0.0.0:80，打印 LAN IP + 每个请求日志
```

烧到 ESP32，手机连 WiFi 访问 `http://192.168.x.x/hello/world` → 看到 "Hello, world!"。
启动信息会显示真实的 LAN IP（如 `http://192.168.1.42:80/`）。

---

## ✨ 特点

- 🪶 **极轻** — 单文件 ~42KB，零外部依赖
- ⚡ **MicroPython 原生** — 重写后**只跑 MicroPython**，砍掉所有 CPython 兼容代码
  - 无 orjson / functools / inspect 兼容、无 Windows socket 错误码、无 CPython UDP 探测分支
- 🎯 **ESP32 验证** — 已在 ESP32-WROVER 4MB 实测通过，MicroPython 1.17+
- ⚡ **单 awrite 优化** — 小响应一次系统调用发送，WiFi 延迟从 5-20ms 降到 2-4ms
- 🚫 **GC 默认关闭** — heap 碎片化卡顿 1-30 秒的情况默认规避
- 🧩 **API 简洁** — `@app.get/post/put/delete` 装饰器、URL 参数、JSON 自动序列化
- 🔌 **零依赖** — 不依赖任何第三方包，纯 MicroPython 内置模块
- 🔋 **电池包含** — 内置静态文件夹服务（含路径穿越防护）、请求日志、Cookie、错误处理、子应用挂载
- 🆙 **无限路由** — 不再有 3 路由限制，可注册任意多个路由和子应用

## 📁 项目结构

```
nova-server/
├── README.md                     ← 本文档（用户向）
├── AGENTS.md                     ← AI 助手指南
├── TESTING.md                    ← 测试指南
│
├── nova_server.py                ← ★ 核心框架（单文件，~980 行）
├── main.py                       ← ESP32 入口模板（WiFi + 路由 + 启动）
│
├── examples/
│   ├── 01_hello.py               ← 最简 hello world（PC 跑）
│   ├── 01_hello_esp32.py         ← ESP32 专属版（WiFi + 80 端口）
│   ├── 02_sensors_api.py         ← 传感器 API + POST 控制指令
│   └── 03_static_files.py        ← 静态文件服务
│
├── test/                         ← 测试套件（96+ 用例）
│   ├── test_*.py                 ← PC 端 pytest
│   └── hardware/                 ← ESP32 硬件测试
│
└── _archive/
    └── miniweb.py                ← 原始文件（保留对比，不删）
```

**核心代码全在 `nova_server.py` 一个文件里**——方便直接复制到 ESP32 flash。

## 🚀 5 分钟上手

### PC 端测试

```bash
# 1. 克隆
git clone <repo> && cd nova-server

# 2. 运行最简例子
python examples/01_hello.py

# 3. 浏览器测试（默认 80 端口）
curl http://localhost/hello/world    # → "Hello, world!"
curl http://localhost/api/version    # → {"server": "nova-server", ...}
```

### 部署到 ESP32

```bash
# 1. 连接 ESP32
mpremote connect COM3

# 2. 拷贝 nova_server（★ 单文件）
mpremote cp nova_server.py :lib/nova_server.py

# 3. 把前端静态文件拷到 /www/static/
mpremote cp -r my-frontend-files :/www/static/

# 4. 重启
mpremote reset

# 5. 手机连 ESP32 WiFi → 浏览器访问 http://192.168.4.1/
```

## 📖 API 速查

### 静态文件服务（★ 内置）

```python
app = NovaServer(static_dir='/static')   # 一行启用静态文件服务

# 自动注册路由：
#   GET /static/              → /static/index.html
#   GET /static/<path:file>   → /static/<file>（含路径穿越防护 + 404 处理）
```

- `static_dir`：磁盘上的目录路径，**必须显式传**才会启用
- `static_path`：URL 前缀，默认 `/static`
- 路径穿越、404、Cache-Control 全部框架内置，**用户无需手写任何代码**

### 请求日志（★ 默认关闭，按需打开）

```python
app = NovaServer(debug=True)   # 或 app.run(debug=True)
```

每个请求完成后自动打印一行：

```
[14:30:21] GET /api/sensors 200 (12ms)
[14:30:21] GET /static/style.css 200 (3ms)
[14:30:22] GET /static/../etc 403 (1ms)
```

格式：`[HH:MM:SS] METHOD 路径 状态码 (耗时ms)`。耗时使用 `time.ticks_ms()` 
单调时钟（MicroPython 原生），无需 RTC 校准。设为 `debug=False` 关闭。

### 路由装饰器

```python
@app.get('/users')               # GET 请求
@app.post('/users')              # POST 请求
@app.put('/users/<int:id>')      # PUT 请求（URL 参数）
@app.delete('/users/<id>')       # DELETE 请求
@app.patch('/users/<id>')        # PATCH 请求
@app.route('/path', methods=['GET', 'POST'])  # 自定义方法列表
```

### URL 参数类型

| 模式 | 匹配 | 解析器 |
|------|------|--------|
| `<name>` | 字符串（默认） | `str` |
| `<int:id>` | 整数 | `int(value)` |
| `<path:path>` | 包含 `/` 的路径 | `str` |
| `<re:[0-9]+:code>` | 正则 | 自定义 |

支持自定义类型：`URLPattern.register_type('hex', '[0-9a-f]+', parser=lambda v: int(v, 16))`

### Request 对象

```python
request.method          # GET / POST / PUT / DELETE / PATCH / HEAD / OPTIONS
request.path            # 路径（不含查询参数）
request.query_string    # 查询参数字符串
request.args            # 查询参数（MultiDict，自动 URL 解码）
request.headers         # HTTP 头（大小写不敏感）
request.cookies         # Cookie 字典
request.json            # JSON body（懒解析）
request.form            # URL-encoded form（懒解析）
request.content_length  # 请求体长度
request.content_type    # 请求体类型
request.client_addr     # 客户端地址
request.url_args        # 路由匹配的 URL 参数（字典）
```

### Response

```python
# 多种返回格式
return 'Hello'                      # str → 200, text/plain
return {'key': 'value'}             # dict/list → 200, application/json
return ('body', 201)                # (body, status_code)
return ('body', 201, {'X-Custom': 'header'})  # (body, status_code, headers)
return ('body', {'X-Custom': 'h'})  # (body, headers) → 200
return 204                          # int → 状态码，空 body
return send_file('index.html', max_age=3600)   # 文件
return redirect('/login')           # 重定向
abort(404, 'Not found')             # 中断请求
```

### 错误处理

```python
@ app.errorhandler(404)
async def not_found(req):
    return '自定义 404 页面', 404

@ app.errorhandler(ValueError)
async def value_error(req, exc):
    return {'error': str(exc)}, 400
```

### 生命周期钩子

```python
@app.before_request
async def before(req):
    req.g.user = await load_user(req)  # 注入到请求

@app.after_request
async def after(req, res):
    res.headers['X-Request-ID'] = generate_id()
    return res

@app.after_error_request
async def after_error(req, res):
    print(f'Error: {res.status_code}')
    return res
```

### 子应用挂载

```python
admin = NovaServer()
# ... 定义路由 ...

app.mount(admin, url_prefix='/admin')
# 所有 /admin/* 路由自动加上前缀
```

## 🔌 与前端生态配套

| 项目 | 职责 | 前端/后端 |
|---|---|---|
| [novajs](../nova-js) | 反应式内核（13KB） | 前端 |
| [nova-style](../nova-style) | 原子 CSS 工具类（12KB） | 前端 |
| [nova-ui](../nova-ui) | IoT 组件库（23KB CSS + 11KB JS） | 前端 |
| [nova-chart](../nova-chart) | 极简图表库（12KB） | 前端 |
| **nova-server** | **异步 Web 框架（10KB）** | **后端** |

典型部署：
```
ESP32 flash
├── main.py              ← NovaServer 入口
├── nova_server.py       ← 核心框架
├── www/
│   ├── index.html       ← 入口页面
│   ├── novajs.min.js    ← 反应式内核
│   ├── nova-style.min.css
│   ├── nova-ui.min.css
│   ├── nova-ui-elements.min.js
│   └── nova-chart.min.js + .css
└── lib/                 ← 其他 MicroPython 库
```

## 🧪 平台策略

**nova-server v0.2 已是纯 MicroPython**：框架代码不再为 CPython 提供兼容分支。
这意味着：

- ✅ 在 ESP32 / NovaMP 固件上：原生最优，每个字节、每条指令都为 MicroPython 设计
- ⚠️ 在 PC (CPython) 上：**仅供 PC 端开发测试用**（pytest 等）。生产请用 MicroPython 设备
- 🔬 唯一保留的 PC 兼容：`sys.print_exception` 在 CPython 上不存在，所以用 `traceback` 兜底（仅便于在 PC 跑测试）

| 路径 | 状态 |
|------|------|
| `network.WLAN` 取 LAN IP | ✅ MicroPython ESP32 |
| `time.ticks_ms()` 计时 | ✅ MicroPython（单调时钟，无需 RTC） |
| `sys.print_exception` | ✅ MicroPython；CPython 自动用 `traceback` 兜底 |
| `asyncio.start_server` | ✅ MicroPython 1.17+ / CPython 3.10+ |

## 📜 License

powered by stemstar
