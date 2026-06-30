"""
02_sensors_api.py — 读传感器 + 控制 LED（ESP32 硬件示例）
=============================================================

演示：
  - 读 DHT22 温湿度
  - 读 ADC 光照（10 次采样平均）
  - POST 控制内置 LED

硬件接线（ESP32）：
  DHT22 DATA ────── GPIO 4   （DATA 引脚要加 10KΩ 上拉到 3.3V）
  光敏电阻 AO ──── GPIO 34  （ADC 输入）
  内置 LED  ─────── GPIO 2   （大部分 ESP32 开发板自带）

部署：
  mpremote connect COM3 cp main.py :main.py
  mpremote reset

测试：
  curl http://192.168.1.42/sensors              → 温湿度+光照
  curl -X POST http://192.168.1.42/led \
       -H 'Content-Type: application/json' \
       -d '{"state":"on"}'                     → 打开 LED
"""

from nova_server import NovaServer
from machine import Pin, ADC
import dht


app = NovaServer()


# ── 硬件初始化 ──────────────────────────────────────────

_dht = dht.DHT22(Pin(4))
_led = Pin(2, Pin.OUT)
_adc = ADC(Pin(34))
_adc.atten(ADC.ATTN_11DB)


# ── 路由 ────────────────────────────────────────────────

@app.get('/sensors')
async def sensors(request):
    """一次性读所有传感器，返回 JSON。"""
    try:
        _dht.measure()
        temp = _dht.temperature()
        hum = _dht.humidity()
    except OSError:
        return {'error': 'sensor read failed'}, 503

    # ADC 采样 10 次取平均（去掉噪声）
    samples = [_adc.read() for _ in range(10)]
    light = sum(samples) // len(samples)

    return {
        'temperature': temp,
        'humidity': hum,
        'light': light,
    }


@app.post('/led')
async def led_control(request):
    """控制 LED 开关。

    发送：  {"state": "on"} 或 {"state": "off"}
    """
    data = request.json
    if not data or data.get('state') not in ('on', 'off'):
        return {'error': 'state must be "on" or "off"'}, 400

    state = data['state']
    _led.value(1 if state == 'on' else 0)
    return {'led': state}


# 启动
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)