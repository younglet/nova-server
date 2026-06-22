# GPIO 安全

ESP32 不是每个引脚都能随便用。**用错可能烧 flash 或芯片**。

## 三类禁用引脚

### ❌ 完全不能用（会烧 flash）

```
GPIO 6, 7, 8, 9, 10, 11
```

这 6 个引脚连接到内部 SPI flash。用了会导致固件损坏或崩溃。

### ⚠️ 只能输入（不能输出）

```
GPIO 34, 35, 36, 37, 38, 39
```

这 6 个引脚没有输出能力。可以 `Pin.IN` / ADC / 触摸，不能 `Pin.OUT`。

```python
from machine import Pin

# ❌ 报错
led = Pin(34, Pin.OUT)    # ValueError: pin is input-only

# ✅ 正确：做输入
button = Pin(35, Pin.IN)  # 按键（需外接上拉电阻）
```

### ⚠️ UART0（REPL）

```
GPIO 1, 3
```

这两个是 USB 串口，用了会破坏 REPL。除非你知道在做什么。

## 电流限制

| 限制 | 值 |
|------|-----|
| 单 GPIO 最大 | 12 mA |
| 所有 GPIO 总和 | ~100 mA |
| GPIO 输出电压 | 3.3V |

**LED 必须接限流电阻**：

```
ESP32 GPIO ──── [220Ω 电阻] ──── LED(+) ──── LED(-) ──── GND
```

LED 直接接 GPIO（没电阻）会烧 LED 或 GPIO。

**电机 / 舵机不能从 ESP32 取电**，要用外接电源：

```
ESP32 GPIO ──── 信号线（只给指令）
ESP32 GND  ──── 与外接电源共地

外接 5V/12V 电源 ── [电机驱动板] ── 电机
```

## 引脚分配建议

| 外设 | 推荐 GPIO | 备注 |
|------|----------|------|
| 内置 LED | GPIO 2 | 大多数开发板 |
| 用户 LED | GPIO 4 / 13 / 14 | 输出安全 |
| 按钮 | GPIO 35 | 输入专用，加上拉 |
| DHT22 温湿度 | GPIO 4 | 加 10KΩ 上拉 |
| 光敏电阻 | GPIO 34 | ADC 输入 |
| OLED (I2C) | GPIO 21/22 | I2C0 默认 SDA/SCL |
| 舵机 | GPIO 13 / 14 | 外接电源！ |

## 完整引脚速查

```python
@app.get('/api/pins')
async def pins(request):
    return {
        # ✅ 可以输出
        'output_safe': [2, 4, 5, 13, 14, 15, 16, 17, 18, 19,
                        21, 22, 23, 25, 26, 27, 32, 33],
        # ⚠️ 只能输入 / ADC
        'input_only': [34, 35, 36, 37, 38, 39],
        # ❌ 禁止
        'forbidden': [6, 7, 8, 9, 10, 11],
        # ⚠️ UART0（REPL）
        'serial': [1, 3],
    }
```

## 代码示例

### LED（输出）

```python
from machine import Pin

LED_PIN = 2

@app.get('/led/<state>')
async def led(request, state):
    led = Pin(LED_PIN, Pin.OUT)
    if state == 'on':
        led.value(1)
    elif state == 'off':
        led.value(0)
    else:
        return {'error': 'on 或 off'}, 400
    return {'led': state}
```

### 按钮（输入）

```python
from machine import Pin

BUTTON_PIN = 35

@app.get('/button')
async def button(request):
    btn = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    # 内部上拉，按下 = 0
    return {'pressed': btn.value() == 0}
```

### 光敏（ADC）

```python
from machine import Pin, ADC

LIGHT_PIN = 34   # ADC1_CH6（输入专用但 ADC 可用）

@app.get('/light')
async def light(request):
    adc = ADC(Pin(LIGHT_PIN))
    adc.atten(ADC.ATTN_11DB)    # 满量程 ~3.3V
    return {'raw': adc.read(), 'max': 4095}
```

### DHT22（温湿度）

```python
import dht
from machine import Pin

DHT_PIN = 4    # DATA 引脚要加 10KΩ 上拉电阻到 3.3V

_sensor = dht.DHT22(Pin(DHT_PIN))

@app.get('/temperature')
async def temp(request):
    try:
        _sensor.measure()
        return {'temperature': _sensor.temperature()}
    except OSError as e:
        return {'error': str(e)}, 503
```

## 下一步

- [WiFi 最佳实践](/hardware/wifi)
- [内存监控](/hardware/memory)
- [功耗与重启](/hardware/power-and-reset)