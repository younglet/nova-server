# nova-server Testing Guide

> 给 AI 用的测试指南。读完这个文件就能上手测试 nova-server。

## 一句话

nova-server 有**两层测试**：
1. **PC 端**：`pytest test/ --ignore=test/hardware`（96+ 个单元/集成测试，~0.4s）
2. **ESP32 硬件端**：`python test/hardware/test_deploy_esp32.py`（部署 + 真实 HTTP 测试 + 稳定性 + 内存）

## 测试结构

```
nova-server/
├── test/                          ← 所有测试
│   ├── __init__.py
│   ├── conftest.py                # pytest 共享 fixtures
│   ├── pytest.ini                 # pytest 配置
│   ├── test_url_pattern.py        # URL 路由匹配
│   ├── test_request.py            # Request 解析（headers/cookies/JSON/form）
│   ├── test_response.py           # Response 构造 + JSON 序列化
│   ├── test_dispatch.py           # dispatch + _normalize_response（防回归）
│   ├── test_examples.py           # examples/ 下的示例文件
│   ├── test_async_server.py       # 端到端 async socket server
│   └── hardware/                  # 硬件测试（独立脚本，不走 pytest）
│       ├── conftest.py            # 让 pytest 跳过此目录
│       ├── README.md
│       └── test_deploy_esp32.py   # 部署 + 真实 HTTP 测试
│
└── TESTING.md                     ← 你正在看
```

## 快速上手

### 1. 跑全部 PC 测试

```bash
cd nova-server
pip install pytest pytest-asyncio
pytest test/ --ignore=test/hardware -v
```

**期望结果**：`96 passed, 10 skipped`（10 skipped 是 Python 3.14 + Windows 的 asyncio bug，硬件测试会覆盖）。

### 2. 跑单个测试文件

```bash
pytest test/test_dispatch.py -v
pytest test/test_examples.py::TestHelloExample -v
pytest test/test_dispatch.py::TestNormalizeResponse::test_dict_return_is_json_body -v
```

### 3. 跑 ESP32 硬件测试

前置：
- ESP32 通过 USB 连接到电脑
- ESP32 已烧 **MicroPython ≥ 1.17**
- 电脑装 `mpremote`：`pip install mpremote`
- ESP32 已连上你家的 WiFi（手动 `wlan.connect('SSID', 'PWD')` 一次即可）

```bash
# 自动检测串口
python test/hardware/test_deploy_esp32.py

# 指定串口
python test/hardware/test_deploy_esp32.py COM3           # Windows
python test/hardware/test_deploy_esp32.py /dev/ttyUSB0  # Linux
python test/hardware/test_deploy_esp32.py /dev/cu.usbmodem01  # macOS

# 指定扫描的子网前缀（如果 ESP32 不在 192.168.71.x）
ESP32_NET_PREFIX=192.168.1 python test/hardware/test_deploy_esp32.py
```

**期望结果**：

```
[OK] Detected ESP32 on COM3
[OK] MicroPython confirmed
[OK] backup saved
[OK] nova-server copied (3 files)
[OK] app copied
[OK] nova-server is up at 192.168.71.105
[OK] / → 302
[OK] /hello/ESP32 → 200
[OK] /api/version → 200
[OK] /health → 200
[OK] /api/wifi → 200
[OK] /nonexistent → 404
[OK] 30 requests OK, avg 200 ms
[OK] no significant memory leak
[OK] ALL TESTS PASSED (8/8)
[OK] device restored
```

## 关键测试覆盖

### 框架核心（PC pytest）

| 文件 | 覆盖 |
|------|------|
| `test_url_pattern.py` | URL 路由：`<name>`, `<int:id>`, `<path:rest>`, `<re:...>` |
| `test_request.py` | Request 解析：URL/headers/cookies/JSON/form |
| `test_response.py` | Response：str/bytes/dict/list → 自动 Content-Type/Length |
| `test_dispatch.py` | **dispatch + _normalize_response**（之前的 bug 就在这里） |
| `test_examples.py` | 三个示例文件：能加载、路由数量、每个 endpoint |
| `test_async_server.py` | 真实 socket server + 并发请求（Python 3.14 + Windows 跳过） |

### 硬件测试（ESP32）

| 阶段 | 检查 |
|------|------|
| 设备识别 | MicroPython 版本、串口 |
| 部署 | 文件复制、清理 `__pycache__` |
| 启动 | 扫描子网找 nova-server（不是其他机器） |
| 端点 | 6 个 HTTP 端点的状态码 + body |
| 稳定性 | 30 次顺序请求，全部成功 |
| 内存 | 部署前后 heap free 差异（应 < 5KB） |
| 恢复 | 把设备文件还原到测试前状态 |

## 关键测试（必须保留）

### ★ `_normalize_response` 防回归

文件：`test/test_dispatch.py::TestNormalizeResponse::test_dict_return_is_json_body`

```python
def test_dict_return_is_json_body(self):
    """★ 关键回归测试：dict 返回必须是 JSON body，不是 headers。"""
    from nova_server.nova_server import NovaServer as NS
    r = NS._normalize_response({'x': 1, 'y': 'z'})
    assert r.body == b'{"x": 1, "y": "z"}'
    assert 'application/json' in r.headers.get('Content-Type', '')
```

这个测试保护了一个**真实 bug**：早期版本 `_normalize_response` 把 dict 当作 headers，导致所有 JSON endpoint 返回空 body。我们已经修复了它，但这个测试确保它不会再回来。

### ★ 跨平台兼容

文件：`test/test_examples.py` 里每个 example 都有 `test_loads` / `test_no_micro_python_only_imports`，验证：
- 文件能被 `exec()` 加载（语法正确）
- 不依赖 CPython 独有特性

### ★ 路径安全

文件：`test/test_examples.py::TestStaticFilesExample::test_path_traversal_blocked`

```python
res = await ns['app'].dispatch_request(
    _make_req(ns['app'], 'GET', '/static/../etc/passwd'))
assert res.status_code in (403, 404)
```

### ★ 内存监控

文件：`test/hardware/test_deploy_esp32.py::test_memory`

部署前后各读一次 `gc.mem_free()`，差异 > 5KB 报"possible memory leak"。

## 写新测试

### 写 PC 测试

```python
# test/test_my_thing.py
from nova_server import NovaServer, abort
from test.conftest import call  # 公共 fixture


@pytest.mark.asyncio
async def test_my_route():
    app = NovaServer()

    @app.get('/foo')
    async def foo(req):
        return {'hello': 'world'}

    res = await call(app, 'GET', '/foo')
    assert res.status_code == 200
    assert b'hello' in res.body
```

要点：
- `@pytest.mark.asyncio` 让 async 函数能跑
- 用 `call(app, method, path)` 跳过 socket 层
- Response.body 总是 bytes，用 `b'...'` 比较

### 写硬件测试

参考 `test/hardware/test_deploy_esp32.py`：
- `mpremote_exec(port, "code")` 在设备上跑 Python
- `mpremote_cp(port, local, ':remote')` 复制文件
- `mpremote_reset(port)` 软重启
- `http_get(host, port, path)` 通过 WiFi 测 HTTP

## 常见错误

| 错误 | 原因 | 修复 |
|------|------|------|
| `mpremote: Permission denied` | `mpremote cp -r` 要目标目录存在 | 先 `os.mkdir('/lib/xxx')` 再 cp |
| `OSError: [Errno 110] ETIMEDOUT` | DHT 传感器没接或坏了 | 用 `SafeSensor` 包装（已有） |
| `MemoryError: ...` | heap 耗尽 | 减少全局变量、及时 `gc.collect()` |
| HTTP 测了别的机器 | 子网里其他设备开了 80 | 测试只接受 `/api/version` 含 `nova-server` 的 |
| `ImportError: no module named '__future__'` | 用了 CPython 特性 | 删掉（MicroPython 不支持） |
| `ImportError: no module named 'ujson'` | 用了 `u` 前缀 | 改用 `json`（MicroPython 已标准化） |

## 调试清单（AI 写完代码后）

```bash
# 1. 跑全部 PC 测试
pytest test/ --ignore=test/hardware -v

# 2. 如果有 esp32，部署测试
python test/hardware/test_deploy_esp32.py COM3

# 3. 看哪些测试失败
pytest test/ --ignore=test/hardware -v --tb=short | grep -E "(FAIL|ERROR)"
```

## 新增功能时的 checklist

- [ ] 在 `test/test_xxx.py` 加单元测试
- [ ] 如果是 handler，在 `test/test_examples.py` 加路由测试
- [ ] 如果涉及新硬件，在 `test/hardware/test_deploy_esp32.py` 加 HTTP 测试
- [ ] 跑 `pytest` 全绿
- [ ] 跑硬件测试（如有设备）
- [ ] 文档同步更新（README.md）

## 关键文件位置速查

| 文件 | 用途 |
|------|------|
| `nova_server.py` | ★ 框架核心（单文件） |
| `main.py` | ESP32 入口模板（WiFi + server） |
| `examples/01_hello.py` | PC 端 hello（80 端口，与 ESP32 一致） |
| `examples/01_hello_esp32.py` | ESP32 端 hello（WiFi + 80 端口） |
| `examples/02_sensors_api.py` | 传感器 API（DHT22 + ADC + LED） |
| `examples/03_static_files.py` | 静态文件服务 |
| `test/conftest.py` | pytest 公共 fixtures |
| `test/hardware/test_deploy_esp32.py` | ESP32 部署 + 真实测试 |