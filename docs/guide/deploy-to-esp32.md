# 部署到 ESP32

把 nova-server 应用部署到 ESP32 的完整流程。

## 1. 烧录 NovaMP 固件

nova-server 已内置在 **NovaMP** 固件里。烧录参考地址：

> https://code.stemstar.com/novamp

按网站提示下载 `novamp.bin` 后用 esptool 烧录：

```bash
esptool.py --chip esp32 --port /dev/ttyUSB0 \
    --baud 460800 write_flash \
    --flash_mode dio --flash_size detect \
    0x1000 novamp.bin
```

烧完后第一次上电会进入 AP 模式（`NovaServer-AP` / `12345678`）。

## 2. 连接 WiFi

NovaMP 内置 `wifi` 模块（自动 WDT 安全 + 重连），比手写 `network.WLAN` 简单很多。

```python
from wifi import WiFi

w = WiFi(ssid='你的WiFi名', password='你的WiFi密码')
w.connect()         # 返回 True/False，进度会自动打印
print(w.ip)         # IP 地址
```

**首次连接失败**时可以用 `w.help()` 跑交互式向导（扫网络 → 选 SSID → 输入密码 → 重试）。

连接成功后凭据会保存在 NVS，重启自动重连，**不用每次都 connect**。

## 3. 获取局域网 IP

连上 WiFi 后：

```python
from wifi import WiFi
w = WiFi(ssid='你的WiFi名', password='你的WiFi密码')
if w.connect():
    print(w.ip)         # 例如 '192.168.71.105'
else:
    print('连接失败')
```

也可以在 REPL 里：

```python
>>> import network
>>> network.WLAN(network.STA_IF).ifconfig()[0]
'192.168.71.105'
```

## 4. 简单部署

只有一个文件的应用（最常见）：

```python
# main.py
from nova_server import NovaServer

app = NovaServer()

@app.get('/')
async def index(request):
    return 'Hello, World!'

app.run(host='0.0.0.0', port=80)
```

推送到设备：

```bash
mpremote connect COM3 cp main.py :main.py
mpremote reset
```

重启后 `http://192.168.71.105/` 就能访问。

## 5. 完整部署

有前端文件 + 多个 Python 文件：

```
ESP32
├── main.py        ← server 入口
├── boot.py        ← 启动配置（可选，WiFi 等）
└── static/        ← 前端 HTML/CSS/JS
    ├── index.html
    ├── style.css
    └── app.js
```

部署步骤：

```bash
# 1. 推 server 文件
mpremote connect COM3 cp main.py :main.py

# 2. 推启动脚本（如果需要 WiFi 自动连接）
mpremote connect COM3 cp boot.py :boot.py

# 3. 创建并推前端目录
mpremote connect COM3 mkdir :static
mpremote connect COM3 cp -r static :static

# 4. 重启
mpremote reset
```

### `boot.py` 模板（WiFi 自动连接 + 启动 server）

```python
from wifi import WiFi
from nova_server import NovaServer, send_file, redirect
import time, gc

# 1. 连 WiFi（凭据持久化）
w = WiFi(ssid='你的WiFi名', password='你的WiFi密码')
w.connect()

# 2. 创建 app
app = NovaServer()

@app.get('/')
async def index(request):
    return redirect('/static/')

@app.get('/static/')
async def static_index(request):
    return send_file('/static/index.html', max_age=3600)

@app.get('/static/<path:filename>')
async def static_file(request, filename):
    if '..' in filename.split('/') or filename.startswith('/'):
        return {'error': 'forbidden'}, 403
    try:
        return send_file('/static/' + filename, max_age=3600)
    except OSError:
        return {'error': 'not found'}, 404

@app.get('/api/info')
async def info(request):
    return {'server': 'nova-server', 'ip': w.ip}

# 3. 启动（阻塞）
if w.is_connected:
    app.run(host='0.0.0.0', port=80)
else:
    print('[boot] WiFi 失败，进入 AP 模式')
```

## 6. REPL 调试

不进 main.py 的 REPL 可以手动验证：

```python
# 测 nova-server 是否能 import
from nova_server import NovaServer
print(NovaServer)

# 测 WiFi
from wifi import WiFi
w = WiFi(ssid='你的WiFi名', password='你的WiFi密码')
print(w.ip)
print(w.is_connected)

# 测 HTTP server
import asyncio
from nova_server import NovaServer
app = NovaServer()

@app.get('/test')
async def test(request):
    return 'hello'

# 启动
asyncio.create_task(app.start_server(host='0.0.0.0', port=80))
asyncio.run(asyncio.sleep(60))
```

**常用调试技巧**：

| 想要 | 命令 |
|------|------|
| 看 boot 输出 | `mpremote connect COM3` + Ctrl-D 软重启 |
| 跑一行代码 | `mpremote exec "code here"` |
| 看 WiFi 状态 | `mpremote exec "import network; print(network.WLAN(network.STA_IF).ifconfig())"` |
| 看内存 | `mpremote exec "import gc; print(gc.mem_free())"` |
| 软重启 | `mpremote reset` |
| 删除文件 | `mpremote rm :main.py` |

## 7. 内存问题

ESP32 只有 ~110 KB 可用 heap。nova-server 已内置**自动 GC**（剩余 < 10 KB 时回收），但还是要注意：

### 实时监控

```python
@app.get('/api/memory')
async def memory(request):
    # 不用调 gc.collect()，框架自动
    return {
        'free': gc.mem_free(),
        'used': gc.mem_alloc(),
        'health': 'good' if gc.mem_free() > 50*1024 else 'low',
    }
```

### 内存不够的常见原因

| 原因 | 修复 |
|------|------|
| 全局列表无界增长 | 限制大小（FIFO） |
| 大文件一次读到内存 | 用流式 `Response(gen())` |
| 字符串频繁拼接 | 用 `''.join()` |
| 反复创建对象 | 复用单例 |

### 极端情况：自动重启

如果 heap 持续低于 3 KB，加个保险：

```python
@app.before_request
async def health_check(request):
    if gc.mem_free() < 3 * 1024:
        print('[MEM] 内存过低，重启')
        import machine
        machine.reset()
```

## 常见问题

| 问题 | 原因 | 修复 |
|------|------|------|
| 设备没响应 | 串口错 / 固件没烧 | 查 `mpremote devs`，重烧固件 |
| WiFi 连不上 | 密码错 / 信号差 | 用 `w.help()` 交互配置 |
| HTTP 不通 | server 没起 / 端口冲突 | REPL 看错误，检查 WiFi 状态 |
| `MemoryError` | heap 耗尽 | `/api/memory` 看状态，重启 |
| 周期性重启 | WDT 触发 | `time.sleep()` 改 `time.sleep_ms()` |
| boot.py 卡死 | 死循环 | `mpremote rm :boot.py` |

## 下一步

- [GPIO 安全](/hardware/gpio-safety)
- [WiFi 最佳实践](/hardware/wifi)
- [内存监控](/hardware/memory)