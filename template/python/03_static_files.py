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
  - static_dir='/static' 一行启用静态文件服务
  - 路径穿越防护、404 处理、Cache-Control: max-age=3600 全部框架内置
  - 不需要手写 _is_safe_path() 或 try/except OSError
"""

from nova_server import NovaServer, redirect


# ★ 一行启用：static_dir='/static' → 自动挂载 /static/ 路由
app = NovaServer(static_dir='/static', debug=True)


# ── 路由 ────────────────────────────────────────────────

@app.get('/')
async def index(request):
    """根路径跳到 /static/。"""
    return redirect('/static/')


@app.get('/api/info')
async def info(request):
    """运行时信息：磁盘根目录 + 平台。"""
    import sys
    return {
        'www_root': app.static_dir,
        'platform': 'micropython' if sys.implementation.name == 'micropython'
                   else 'cpython',
    }


# 启动
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)