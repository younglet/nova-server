"""
main.py — ESP32 入口模板
========================

这是 ESP32 上跑 nova-server 的最小骨架。

ESP32 文件结构：
  /
  ├── boot.py         ← 启动配置（WiFi 连接），可选
  ├── main.py         ← 这个文件
  └── static/         ← 前端文件（HTML/CSS/JS），可选

部署：
  # 1. 先部署 boot.py（首次需要 WiFi 配置）
  mpremote connect COM3 cp boot.py :boot.py

  # 2. 部署 server
  mpremote connect COM3 cp main.py :main.py
  mpremote reset

  # 3. 部署前端（如果有 static/ 目录）
  mpremote connect COM3 cp -r static :static

  # nova-server 已内置在 NovaMP 固件，无需单独部署
"""

import gc
import time

from nova_server import NovaServer, send_file


# ═══════════════════════════════════════════════════════════
# 配置区（按需修改）
# ═══════════════════════════════════════════════════════════

WIFI_SSID = '你的WiFi名'        # ← 改这里
WIFI_PASSWORD = '你的WiFi密码'   # ← 改这里


# ═══════════════════════════════════════════════════════════
# WiFi 连接
# ═══════════════════════════════════════════════════════════

def connect_wifi():
    """非阻塞连接 WiFi。15 秒超时。"""
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # 如果之前连过，直接复用
    if wlan.isconnected():
        return wlan

    print('[WiFi] connecting to {}...'.format(WIFI_SSID))
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    # 等连接，每 100ms 检查一次（WDT 安全）
    start = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > 15000:
            return None
        time.sleep_ms(100)

    print('[WiFi] OK:', wlan.ifconfig()[0])
    return wlan


# ═══════════════════════════════════════════════════════════
# 路由
# ═══════════════════════════════════════════════════════════

app = NovaServer()
_boot_ms = time.ticks_ms()


@app.get('/')
async def index(request):
    """首页：跳到 static/index.html。"""
    from nova_server import redirect
    return redirect('/static/')


@app.get('/static/')
async def static_index(request):
    return send_file('/static/index.html', max_age=3600)


@app.get('/static/<path:filename>')
async def static_file(request, filename):
    """提供 /static/ 目录下的文件。"""
    if '..' in filename.split('/') or filename.startswith('/'):
        return {'error': 'forbidden'}, 403
    try:
        return send_file('/static/' + filename, max_age=3600)
    except OSError:
        return {'error': 'not found'}, 404


@app.get('/api/info')
async def api_info(request):
    """设备信息。"""
    gc.collect()
    return {
        'server': 'nova-server',
        'platform': 'NovaMP',
        'wifi_ip': network.WLAN(network.STA_IF).ifconfig()[0]
                   if network.WLAN(network.STA_IF).isconnected()
                   else None,
        'uptime_sec': time.ticks_diff(time.ticks_ms(), _boot_ms) // 1000,
    }


# ═══════════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════════

import asyncio


async def main():
    gc.collect()
    print('[boot] free heap: {} KB'.format(gc.mem_free() // 1024))

    # WiFi（失败也不阻止 server 启动 → AP 模式）
    import network
    wlan = connect_wifi()
    if wlan is None:
        print('[boot] WiFi failed, fallback to AP mode')

    gc.collect()
    print('[boot] HTTP server @ 0.0.0.0:80')
    await app.start_server(host='0.0.0.0', port=80, debug=False)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('[boot] stopped')
    except Exception as e:
        print('[boot] error:', e)