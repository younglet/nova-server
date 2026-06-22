"""
03_static_files.py — 提供前端 HTML / CSS / JS 文件
====================================================

ESP32 文件结构：
  /
  ├── main.py        ← 这个文件
  └── static/        ← 放前端文件
      ├── index.html
      ├── style.css
      └── app.js

部署：
  # 1. 部署 server
  mpremote connect COM3 cp main.py :main.py
  mpremote reset

  # 2. 上传前端文件到 ESP32 的 /static/ 目录
  mpremote connect COM3 mkdir :static
  mpremote connect COM3 cp static/index.html :static/index.html
  mpremote connect COM3 cp static/style.css :static/style.css
  mpremote connect COM3 cp static/app.js :static/app.js

  # 或者一次性拷贝整个目录：
  mpremote connect COM3 cp -r static :static

测试：
  curl http://192.168.1.42/                → /static/index.html
  curl http://192.168.1.42/static/         → /static/index.html
  curl http://192.168.1.42/static/style.css
  curl http://192.168.1.42/static/app.js

注意：
  - /static/ 路径前缀映射到 ESP32 的 /static/ 目录
  - send_file 自动根据扩展名设置 Content-Type
  - max_age=3600 让浏览器缓存 1 小时
"""

from nova_server import NovaServer, send_file


app = NovaServer()


# ── 路径安全检查 ────────────────────────────────────────

def _is_safe(path):
    """拒绝 ../ 路径穿越攻击。"""
    if not path:
        return False
    if path.startswith('/'):
        return False
    if '..' in path.split('/'):
        return False
    return True


# ── 路由 ────────────────────────────────────────────────

@app.get('/')
async def index(request):
    """根路径跳到 /static/。"""
    from nova_server import redirect
    return redirect('/static/')


@app.get('/static/')
async def static_index(request):
    """访问 /static/ 时返回 index.html。"""
    return send_file('/static/index.html', max_age=3600)


@app.get('/static/<path:filename>')
async def serve_file(request, filename):
    """从 /static/ 目录提供文件。

    ★ 关键：先验证路径安全，再 send_file。
    """
    if not _is_safe(filename):
        return {'error': 'forbidden'}, 403
    try:
        return send_file('/static/' + filename, max_age=3600)
    except OSError:
        return {'error': 'not found'}, 404


# 启动
app.run(host='0.0.0.0', port=80)