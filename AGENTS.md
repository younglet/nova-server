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
python examples/01_hello.py                        # → localhost:80

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
├── nova_server.py              ← ★ 核心框架（单文件 ~1165 行，纯 MicroPython）
├── main.py                     ← ESP32 入口模板（WiFi + 路由 + 启动）
│
├── examples/
│   ├── 01_hello.py             ← 最简 hello world（4 个路由，debug=True 默认）
│   ├── 02_sensors_api.py       ← 设备 API + POST 控制（需要 machine/dht）
│   ├── 03_static_files.py      ← 静态文件服务（debug=True）
│   └── 04_async_streaming.py   ← 异步流式响应
│
├── test/
│   ├── test_*.py               ← PC 端 pytest（仅开发用，框架本身只跑 MP）
│   └── hardware/               ← ESP32 硬件测试
│
└── _archive/
    └── miniweb.py              ← 旧版（保留对比，结构样板来源）
```

**核心永远在 `nova_server.py` 一个文件里**。v0.2 起**纯 MicroPython**，无 CPython 兼容分支。

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

### 4. 平台策略（v0.2 重写后）

**纯 MicroPython**，仅保留一个最小测试用 shim（让 PC 上能跑 pytest）：

```python
# nova_server.py 第 38 行附近（唯一兼容 shim）
try:
    from sys import print_exception    # MicroPython
except ImportError:
    import traceback as _tb
    def print_exception(exc):
        _tb.print_exception(type(exc), exc, exc.__traceback__)
```

**已删除的兼容分支**（v0.2 起）：
- ❌ `import orjson except: import json`
- ❌ `from inspect import iscoroutinefunction, iscoroutine`
- ❌ `from functools import partial`
- ❌ Windows socket 错误码 10053/10054
- ❌ CPython UDP 探测 LAN IP（只剩 `network.WLAN`）
- ❌ 路由 3 个限制 (`_limit = (1 << 1) + 1`)
- ❌ `auto_gc=True` 默认（heap 碎片化卡 1-30s）

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

### 7. 静态文件 + 请求日志（★ 框架内置，v0.2 默认启用）

```python
app = NovaServer()                  # 默认就启用 /static/ 静态文件路由
app = NovaServer(static_dir=None)   # 想要禁用才显式传 None
app = NovaServer(static_dir='/www') # 换磁盘路径
```

- `static_dir`：默认 '/static'（v0.2 起）。ESP32 flash 上的标准文件夹。传 `None` 禁用
- `static_path`：URL 前缀，默认 '/static'
- `debug`：默认 False，传 True 打印每个请求日志 `[HH:MM:SS] METHOD /path STATUS (ms)`
- 路径穿越防护（`_is_safe_path`） + OSError→404 + max_age=3600 全部封装在 `_mount_static()` 里
- `auto_gc`：默认 False（v0.2 防 ESP32 heap 碎片化卡顿）
- `gc_threshold_kb`：默认 50（开了的话阈值更宽松）
- `host`/`port`：默认 `'0.0.0.0'`/`80`（v0.2 ESP32 一键启动不用 port=80）

用户不需要手写 `_is_safe` 、`try/except OSError`、`send_file(max_age=...)`。
直接 `NovaServer()` 就拿到防穿越的静态文件服务。

## 改动会影响什么

| 改这个 | 也会影响 |
|---|---|
| `nova_server.py` 核心路由 | 所有使用 nova-server 的 ESP32 项目 |
| `NovaServer.__init__` 参数 | 所有示例的 app 初始化代码（host/port/debug/auto_gc/static_dir） |
| `_mount_static()` | 所有启用 static_dir 的项目 |
| URLPattern | 所有路径参数匹配行为 |
| `Response._build_head` + `write` 快路径 | 所有响应性能（单 awrite） |
| `_normalize_response` | handler 返回值自动包装逻辑 |
| Request JSON/form 解析 | POST/PUT 请求的数据解析 |
| 默认 `host='0.0.0.0'` / `port=80` | ESP32 部署不再需要 `app.run(port=80)` |
| 默认 `auto_gc=False` | ESP32 性能修复（不再默认触发 1-30s GC） |
| 默认 `debug=False` | 请求日志改成按需打开 |

## 提交前 checklist

```bash
cd nova-server

# 1. PC 测试：跑全部 pytest（仅开发用）
pytest test/ --ignore=test/hardware -v
# 期望：133 passed, 18 skipped（v0.2 起）

# 2. ESP32 测试（如有设备）
python test/hardware/test_deploy_esp32.py COM3
# 期望：ALL TESTS PASSED

# 3. 例子 import 验证
python -c "
for ex in ['01_hello', '03_static_files', '04_async_streaming']:
    with open(f'examples/{ex}.py', encoding='utf-8') as f:
        exec(f.read().split('if __name__')[0])
    print(f'{ex}: OK')
"
# 02_sensors_api 需要 machine/dht 模块，PC 跑不了（仅设备）
```

## 不要做的事

- ❌ 拆多文件（MicroPython 单文件部署最方便）
- ❌ 引入第三方依赖（保持零依赖，没有可选加速选项）
- ❌ 改 `import` 用 `u` 前缀（必须用 `json` 不是 `ujson`，`re` 不是 `ure`）
- ❌ 在 handler 里做阻塞 I/O（会阻塞所有异步连接）
- ❌ 用 `time.sleep()` 在异步 handler 里（用 `await asyncio.sleep()`）
- ❌ 自动加 `CORS` 头（用户通过 `after_request` 钩子自行控制）
- ❌ 调用 `gc.collect()` 在请求热路径上（默认 auto_gc=False，需要时手动开启）
- ❌ 添加 CPython 兼容性 shim（v0.2 起纯 MicroPython）
