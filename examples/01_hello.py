"""
01_hello.py — 最简示例（4 个路由）
==================================

只用 17 行代码就能跑一个 Web 服务。

文件结构：
  ESP32
  ├── main.py        ← 这个文件
  └── (其他任何文件)

烧录：
  mpremote connect COM3 cp main.py :main.py
  mpremote reset

测试（假设 ESP32 IP 是 192.168.1.42）：
  curl http://192.168.1.42/                    → 302 → /hello/world
  curl http://192.168.1.42/hello/Alice         → "Hello, Alice!"
  curl http://192.168.1.42/api/version         → {"server": "nova-server", ...}
  curl http://192.168.1.42/health              → {"status": "ok", ...}
"""

from nova_server import NovaServer, redirect


app = NovaServer()


@app.get('/')
async def index(request):
    """根路径。重定向到 /hello/world。"""
    return redirect('/hello/world')


@app.get('/hello/<name>')
async def hello(request, name):
    """URL 参数示例：捕获 <name>。"""
    return 'Hello, {}!'.format(name)


@app.get('/api/version')
async def api_version(request):
    """返回服务器信息。"""
    import sys
    return {
        'server': 'nova-server',
        'version': '0.1.0',
        'platform': 'micropython' if sys.implementation.name == 'micropython'
                    else 'cpython',
    }


@app.get('/health')
async def health(request):
    """健康检查：状态 + 内存（MicroPython 上有，CPython 上退化）。"""
    import gc
    info = {'platform': sys.platform if (sys := __import__('sys')) else ''}
    try:
        info['free'] = gc.mem_free()
        info['allocated'] = gc.mem_alloc()
    except AttributeError:
        info['free'] = -1
    return {'status': 'ok', 'memory': info}


# 启动 server，监听 80 端口
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)