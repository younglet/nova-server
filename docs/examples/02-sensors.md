# 示例 02：传感器 + LED 控制

读 DHT22 温湿度和光敏电阻，POST 控制 LED。

## 硬件接线

```
DHT22 DATA ───── GPIO 4  （加 10KΩ 上拉到 3.3V）
光敏电阻 AO ──── GPIO 34 （ADC 输入）
内置 LED   ───── GPIO 2  （大部分开发板自带）
```

## 完整代码

```python
from nova_server import NovaServer

app = NovaServer()

# 硬件初始化
from machine import Pin, ADC
import dht

_dht = dht.DHT22(Pin(4))
_led = Pin(2, Pin.OUT)
_adc = ADC(Pin(34))
_adc.atten(ADC.ATTN_11DB)

@app.get('/sensors')
async def sensors(request):
    """读所有传感器。"""
    try:
        _dht.measure()
        temp = _dht.temperature()
        hum = _dht.humidity()
    except OSError:
        return {'error': 'sensor read failed'}, 503

    # ADC 采样 10 次取平均
    samples = [_adc.read() for _ in range(10)]
    light = sum(samples) // len(samples)

    return {
        'temperature': temp,
        'humidity': hum,
        'light': light,
    }

@app.post('/led')
async def led_control(request):
    """控制 LED 开关。"""
    data = request.json
    if not data or data.get('state') not in ('on', 'off'):
        return {'error': 'state must be "on" or "off"'}, 400

    _led.value(1 if data['state'] == 'on' else 0)
    return {'led': data['state']}

app.run(port=80)
```

## 部署

## 测试

完整文件：[examples/02_sensors_api.py](https://github.com/)

## 关键点

### 引脚选型

- GPIO 4：安全输出，做 DHT22 数据线
- GPIO 2：内置 LED
- GPIO 34：输入专用，但 ADC 可用

不要用 GPIO 6-11（会烧 flash），详见 [GPIO 安全](/hardware/gpio-safety)。

### DHT22 注意

DHT22 每 2 秒最多读一次。频繁调用可能失败。SafeSensor 包装（重试 + 超时）能解决，但这里简化了。

### ADC 平均

光敏电阻直接读噪声大。10 次采样平均更稳定。

## 下一步

- [示例 03 — 静态文件](/examples/03-static-files)：提供前端
- [示例 04 — 流式响应](/examples/04-streaming)：实时数据推送
- [POST 请求](/guide/post-requests)