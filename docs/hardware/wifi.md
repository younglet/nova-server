# WiFi 最佳实践

ESP32 的 WiFi 是最容易出问题的地方。常见症状：连接掉线、设备周期性重启、连不上 WiFi。

## 为什么 WiFi 会断？

ESP32 在以下情况会**静默断线**：

- 路由器重启
- 信号太弱
- 长时间无流量（部分路由器会踢客户端）
- 深度睡眠后

## 为什么周期性重启？

`wlan.connect()` 会**阻塞 1-15 秒**。如果在这个阻塞期间，看门狗（WDT）触发，ESP32 就重启。

WDT 默认 5 秒超时。任何 `time.sleep()` 阻塞超过 5 秒都会触发。

## 错误写法

```python
import network, time

wlan = network.WLAN(network.STA_IF)
wlan.connect('SSID', 'PASSWORD')   # ← 阻塞最多 15 秒
time.sleep(1)                       # ← sleep(1) 在循环里也会触发 WDT
```

## 正确写法

```python
import network, time

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# 之前连过就直接返回（凭据持久化）
if wlan.isconnected():
    pass
else:
    wlan.connect('SSID', 'PASSWORD')

    # ★ 非阻塞等待 + WDT 安全
    start = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > 15000:
            raise OSError('WiFi timeout')
        time.sleep_ms(100)   # ← 每 100ms 喂一次 WDT
```

## 完整 WiFi 管理器

直接放到 `boot.py`：

```python
import network, time

def connect_wifi(ssid, password, timeout_s=15):
    """非阻塞连接。返回 wlan 或 None。"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan

    wlan.connect(ssid, password)

    start = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > timeout_s * 1000:
            return None
        time.sleep_ms(100)

    return wlan

def start_ap_fallback():
    """STA 连不上时开热点。"""
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(
        essid='ESP32-Setup',
        password='12345678',
        authmode=network.AUTH_WPA_WPA2_PSK,
    )
    return ap

# 主流程
wlan = connect_wifi('你的WiFi', '你的密码')
if wlan is None:
    print('STA failed, starting AP')
    start_ap_fallback()
else:
    print('WiFi:', wlan.ifconfig()[0])
```

## 主动重连

ESP32 跑久了 WiFi 可能静默断开。建议**定期检查 + 自动重连**：

```python
import asyncio

async def wifi_watchdog():
    """后台任务：每 30 秒检查 WiFi。"""
    import network
    wlan = network.WLAN(network.STA_IF)

    while True:
        await asyncio.sleep(30)
        if not wlan.isconnected():
            print('[WiFi] reconnecting...')
            wlan.connect()
            # 等连接
            start = time.ticks_ms()
            while not wlan.isconnected():
                if time.ticks_diff(time.ticks_ms(), start) > 15000:
                    break
                time.sleep_ms(100)
            if wlan.isconnected():
                print('[WiFi] reconnected:', wlan.ifconfig()[0])
```

启动：

```python
asyncio.create_task(wifi_watchdog())
```

## 性能参考

| 操作 | 耗时 | 影响 |
|------|------|------|
| `wlan.active(True)` | 200ms | 启用 radio |
| `wlan.scan()` | 2s | 阻塞，**别在 handler 里调** |
| `wlan.connect()` | 1-15s | 阻塞 |
| `wlan.isconnected()` | 10μs | 随便调 |

WiFi 启用后占 ~50KB heap。**别**在 handler 里反复 enable/disable WiFi。

## AP 模式配网

如果用户不会配 WiFi，可以让 ESP32 开热点，让用户连上后输入 WiFi 信息：

```python
def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(
        essid='ESP32-Setup',          # 热点名
        password='12345678',          # 至少 8 位
        authmode=network.AUTH_WPA_WPA2_PSK,
    )
    print('AP:', ap.ifconfig()[0])     # 默认 192.168.4.1
```

手机连上 `ESP32-Setup` 热点，浏览器访问 `http://192.168.4.1/` 即可。

## 下一步

- [内存监控](/hardware/memory)
- [GPIO 安全](/hardware/gpio-safety)
- [功耗与重启](/hardware/power-and-reset)