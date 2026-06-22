# 硬件测试 (ESP32)

这个目录里的测试**需要在真实 ESP32 上运行**，不能在 PC 上跑。

## 前置条件

1. ESP32 通过 USB 连接到电脑
2. ESP32 已烧录 **MicroPython ≥ 1.17** 固件
3. 电脑已装 **mpremote**：`pip install mpremote`
4. ESP32 已连上 WiFi（手动在 REPL 里 `wlan.connect('SSID', 'PWD')` 一次即可）

## 运行测试

```bash
# 自动检测串口
python test/hardware/test_deploy_esp32.py

# 指定串口
python test/hardware/test_deploy_esp32.py COM3        # Windows
python test/hardware/test_deploy_esp32.py /dev/ttyUSB0 # Linux
python test/hardware/test_deploy_esp32.py /dev/cu.usbmodem01 # macOS
```

## 测试流程

```
检测 ESP32 → 备份原文件 → 部署 nova_server → 部署测试 app
   ↓
软重启 ESP32 → 等 server 启动 → HTTP 测试所有端点
   ↓
压力测试 (30 次) → 内存泄漏检查 → 恢复原文件
```

## 测试覆盖

| 端点 | 期望状态 | 期望内容 |
|------|---------|---------|
| `GET /` | 302 | redirect 到 /hello/world |
| `GET /hello/<name>` | 200 | 字符串响应 |
| `GET /api/version` | 200 | JSON 含 `server` |
| `GET /health` | 200 | JSON 含 `memory` |
| `GET /api/wifi` | 200 | JSON 含 `wifi` |
| `GET /nonexistent` | 404 | Not found |

## 已知问题 / 注意事项

- **mpremote `exec` 会打断正在运行的 server**：如果要在测试中调试 REPL，要先重启 ESP32 让 main.py 重新跑。
- **WiFi 重连**：ESP32 软重启后 WiFi 可能断开；建议先手动连一次并保存凭据，或在 main.py 里加自动重连逻辑。
- **heap 监控**：`gc.mem_free()` 只在 MicroPython 有，PC 测试里要 guard。
- **路径安全**：测试故意请求 `/static/../etc/passwd` 验证 403 拦截。

## 写新的硬件测试

参考 `test_deploy_esp32.py` 的模板：

```python
def deploy(port, app_name):
    # 1. mpremote connect <port> exec "..."
    # 2. mpremote connect <port> cp <local> :<remote>
    # 3. mpremote connect <port> reset

def http_get(host, port, path):
    # 用 urllib 或 socket 发 HTTP 请求

def test_endpoints(host, port):
    # 跑断言
```