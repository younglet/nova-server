"""
01_hello.py — 最简示例（3 个路由）
===================================

只用 17 行代码就能跑一个 Web 服务。

文件结构：
  ESP32
  ├── main.py        ← 这个文件
  └── (其他任何文件)

烧录：
  mpremote connect COM3 cp main.py :main.py
  mpremote reset

测试（假设 ESP32 IP 是 192.168.1.42）：
  curl http://192.168.1.42/              → Hello, World!
  curl http://192.168.1.42/info          → {"server": "nova-server"}
  curl http://192.168.1.42/time          → {"uptime_sec": 42}
"""

from nova_server import NovaServer


app = NovaServer()
_start = 0


@app.get('/')
async def index(request):
    """根路径。返回纯文本。"""
    return 'Hello, World!'


@app.get('/info')
async def info(request):
    """返回 JSON。dict 自动转 JSON。"""
    return {
        'server': 'nova-server',
        'platform': 'NovaMP',
    }


@app.get('/time')
async def time(request):
    """读启动后经过的秒数。"""
    import time
    if hasattr(time, 'ticks_ms'):
        now = time.ticks_ms()
        sec = now // 1000
    else:
        sec = 0
    return {'uptime_sec': sec}


# 启动 server，监听 80 端口
app.run(host='0.0.0.0', port=80)