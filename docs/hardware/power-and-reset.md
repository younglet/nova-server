# 功耗与重启

电池供电时怎么省电、设备卡死时怎么重启。

## 深度睡眠（最省电）

ESP32 深度睡眠时只耗 ~10 µA，但**所有 RAM 内容丢失**。

```python
import machine
machine.deepsleep(60 * 1000)    # 60 秒后唤醒
```

唤醒后**等于重新启动**（boot.py 重新跑）。

### 典型应用：定时上报

```python
import machine, time
from machine import Pin, ADC
from nova_server import NovaServer

adc = ADC(Pin(34))
adc.atten(ADC.ATTN_11DB)
light = adc.read()    # 读一次传感器

# 上报（可选）
try:
    import network, urequests
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect('SSID', 'PWD')
    start = time.ticks_ms()
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), start) < 10000:
        time.sleep_ms(100)
    if wlan.isconnected():
        urequests.post('https://api.example.com/data', json={'light': light})
except Exception:
    pass

# 睡 60 秒
machine.deepsleep(60 * 1000)
```

## 看门狗（WDT）

ESP32 硬件看门狗 5 秒超时。**任何阻塞 5 秒以上会重启**。

### 触发 WDT 的常见情况

| 原因 | 修复 |
|------|------|
| `time.sleep(5)` | 改用 `time.sleep_ms(100)` |
| `wlan.connect()` 阻塞 | 用 [非阻塞循环](/hardware/wifi) |
| 同步 I/O 阻塞 | 改成 async / 加 sleep_ms |
| 死循环没 await | 加 `await asyncio.sleep_ms(10)` |

### 关闭 WDT（不推荐）

```python
import machine
machine.WDT().deinit()
```

只在调试时关，生产环境**不要**关。

## 自动重启

```python
import machine

async def main():
    try:
        await app.start_server(port=80)
    except Exception as e:
        print('[FATAL]', e)
        time.sleep_ms(500)
        machine.reset()    # 软重启

asyncio.run(main())
```

### 内存太低自动重启

```python
@app.before_request
async def health_check(request):
    if gc.mem_free() < 3 * 1024:
        print('[MEM] too low, rebooting')
        time.sleep_ms(500)
        import machine
        machine.reset()
```

## RTC 内存

ESP32 有 8 KB RTC 内存，深度睡眠**保留**。可存关键数据：

```python
import machine
rtc = machine.RTC()

rtc.memory(b'stored data')     # 写
data = rtc.memory()             # 读（深度睡眠后仍可读）
```

适合存：

- 上次唤醒时间
- 累积计数器
- 错误日志

## 电源设计

### USB 供电

- 5V → ESP32 内置 LDO → 3.3V
- 输出电流有限（~500 mA）
- **不能直接驱动电机**

### 电池供电

```
锂电池 3.7V
  │
  ├─→ ESP32 VIN（经过 LDO）
  │
  └─→ 升压到 5V → 电机 / 舵机
```

注意：

- 电池 < 3.0V 时 ESP32 会复位（brownout）
- 加 **100 µF+ 电容**靠近 ESP32 VIN
- 长时间深度睡眠用 18650（3000 mAh 可撑几个月）

## 下一步

- [GPIO 安全](/hardware/gpio-safety)
- [WiFi 最佳实践](/hardware/wifi)
- [内存监控](/hardware/memory)