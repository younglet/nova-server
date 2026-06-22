# AGENTS.md — nova-server

> AI 助手用的项目指南。读这个文件就能上手这个项目。

## 一句话

**nova-server** 是一个 10KB 的 MicroPython + CPython 异步微型 Web 框架，专为 ESP32 IoT 场景设计。单文件、零依赖、已硬件验证。

## 目标平台

烧了 **MicroPython 1.17+** 的 **ESP32（4MB flash）**。之前叫 `miniweb`，现在正式改名 `nova-server` 并纳入 nova-frontend 生态（4 前端 + 1 后端）。

| 约束 | 体现 |
|---|---|
| 小 | 单文件 ~10KB，可直接复制到 ESP32 flash |
| 快 | asyncio 非阻塞 I/O |
| 零依赖 | 不依赖任何第三方包 |
| MicroPython 兼容 | 三段 `try/except ImportError` 做平台降级 |
| 已验证 | ESP32-WROVER 实测跑通 |

**不是** Flask（不依赖 werkzeug/jinja2），**不是** aiohttp（更小 100x）。

## 跑通

```bash
cd nova-server

# PC 端测试
python examples/01_hello.py                        # → localhost:5000

# ESP32 部署
mpremote connect COM3
mpremote cp -r nova_server :                        # 整个包拷到 ESP32
mpremote examples/01_hello.py :main.py              # 例子作为入口
mpremote reset                                      # 重启 → 自动运行
```

## 关键文件

```
nova-server/
├── README.md                   ← 用户向（你正在看）
├── AGENTS.md                   ← AI 向（本文）
│
├── nova_server/
│   ├── __init__.py             ← 包入口：暴露 8 个公共 API
│   ├── nova_server.py          ← 核心框架（单文件 ~950 行）
│   └── main.py                 ← ESP32 入口模板（WiFi + 路由 + 启动）
│
├── examples/
│   ├── 01_hello.py             ← 最简 hello world（4 个路由）
│   ├── 02_sensors_api.py       ← 设备 API + POST 控制
│   └── 03_static_files.py      ← 静态文件服务
│
└── _archive/
    └── miniweb.py              ← 原文件（保留对比）
```

**核心永远在 `nova_server.py` 一个文件里**。不改多文件结构。

## 核心约定

### 1. 路由装饰器是唯一入口

```python
@app.get('/path')
@app.post('/path')
@app.put('/path/<int:id>')
@app.delete('/path/<int:id>')
@app.patch('/path')
@app.route('/path', methods=['GET', 'POST'])
```

没有 `add_url_rule()` / `@app.register()` 等替代 API（保持单入口）。

### 2. Handler 签名为 `async def handler(request, **url_args)`

```python
@app.get('/hello/<name>')
async def hello(req, name):    # req 是 Request 对象，name 是 URL 参数
    return f'Hello, {name}!'
```

### 3. 三种返回格式

```python
# 1) 字符串 → text/plain
return 'ok'

# 2) dict/list → application/json
return {'status': 'ok'}

# 3) Response 对象（send_file / redirect）
return send_file('index.html')
return redirect('/login')
```

### 4. 平台兼容性

所有 CPython→MicroPython 降级在 `nova_server.py` 头部统一处理：

```python
try:
    # CPython 完整功能
    from inspect import iscoroutinefunction, iscoroutine
    from functools import partial
    from sys import print_exception
except ImportError:
    # MicroPython 最小兼容
    def iscoroutine(coro):
        return hasattr(coro, 'send') and hasattr(coro, 'throw')
    def print_exception(exc):
        import traceback; traceback.print_exc()
```

### 5. URL 参数不需要显式声明类型——用 `<int:id>` 语法

```python
@app.get('/user/<int:id>')    # URLPattern 自动转 int
async def get_user(req, id):
    ...
```

### 6. 错误处理链

```
handler → HTTPException → error_handler(status_code) → error_response()
                              ↓
                       Exception → error_handler(class) → mro() 链查找 → error_response()
```

`mro()` 自动沿着异常类的继承链查找匹配的 error handler。

### 7. 静态文件 + 请求日志（★ 框架内置）

```python
app = NovaServer(static_dir='/static', log=True)
```

- `static_dir`：启用静态文件服务（传 None 禁用），自动注册 /static/ 和 /static/<path:file> 两个路由
- `static_path`：URL 前缀，默认 '/static'
- `log`：默认 True，每个请求完成后打印一行 `[HH:MM:SS] METHOD /path STATUS (ms)`
- 路径穿越防护（`_is_safe_path`） + OSError→404 + max_age=3600 全部封装在 `_mount_static()` 里

用户不需要手写 `_is_safe` 、`try/except OSError`、`send_file(max_age=...)`，只需要传 `static_dir`。

## 改动会影响什么

| 改这个 | 也会影响 |
|---|---|
| `nova_server.py` 核心路由 | 所有使用 nova-server 的 ESP32 项目 |
| `NovaServer.__init__` 参数 | 所有示例的 app 初始化代码（static_dir / log / auto_gc） |
| `_mount_static()` | 所有启用 static_dir 的项目 |
| URLPattern | 所有路径参数匹配行为 |
| Response.body_iter | 大文件传输、流式响应 |
| `_normalize_response` | handler 返回值自动包装逻辑 |
| Request JSON/form 解析 | POST/PUT 请求的数据解析 |
| 删除 `try/except` 降级 | MicroPython 兼容性 |

## 提交前 checklist

```bash
cd nova-server

# 1. PC 测试：跑全部 pytest
pytest test/ --ignore=test/hardware -v
# 期望：96 passed, 10 skipped

# 2. ESP32 测试（如有设备）
python test/hardware/test_deploy_esp32.py COM3
# 期望：ALL TESTS PASSED (8/8)

# 3. 例子 import 验证
python -c "
for ex in ['01_hello', '02_sensors_api', '03_static_files']:
    with open(f'examples/{ex}.py', encoding='utf-8') as f:
        exec(f.read().split('if __name__')[0])
    print(f'{ex}: OK')
"
```

## 不要做的事

- ❌ 拆多文件（MicroPython 单文件部署最方便）
- ❌ 引入第三方依赖（保持零依赖，`orjson` 是唯一可选加速）
- ❌ 改 `import` 用 `u` 前缀（必须用 `json` 不是 `ujson`，`re` 不是 `ure`）
- ❌ 在 handler 里做阻塞 I/O（会阻塞所有异步连接）
- ❌ 用 `time.sleep()` 在异步 handler 里（用 `await asyncio.sleep()`）
- ❌ 自动加 `CORS` 头（用户通过 `after_request` 钩子自行控制）
