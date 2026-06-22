# 示例 03：静态文件服务

把 HTML / CSS / JS 放到 ESP32 上。

## 文件结构

```
ESP32
├── main.py
└── static/
    ├── index.html
    ├── style.css
    └── app.js
```

## main.py

```python
from nova_server import NovaServer, send_file, redirect

app = NovaServer()

def _is_safe(path):
    """防路径穿越（../）。"""
    if not path or path.startswith('/'):
        return False
    if '..' in path.split('/'):
        return False
    return True

@app.get('/')
async def index(request):
    return redirect('/static/')

@app.get('/static/')
async def static_index(request):
    return send_file('/static/index.html', max_age=3600)

@app.get('/static/<path:filename>')
async def static_file(request, filename):
    if not _is_safe(filename):
        return {'error': 'forbidden'}, 403
    try:
        return send_file('/static/' + filename, max_age=3600)
    except OSError:
        return {'error': 'not found'}, 404

app.run(port=80)
```

## 准备前端文件

`static/index.html`：

```html
<!DOCTYPE html>
<html>
<head>
    <title>ESP32 Dashboard</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>ESP32 Dashboard</h1>
    <button onclick="loadSensors()">Refresh Sensors</button>
    <pre id="data">loading...</pre>
    <script src="/static/app.js"></script>
</body>
</html>
```

`static/style.css`：

```css
body {
    font-family: sans-serif;
    padding: 20px;
    max-width: 600px;
    margin: 0 auto;
}
button {
    padding: 10px 20px;
    font-size: 16px;
}
pre {
    background: #f0f0f0;
    padding: 10px;
    border-radius: 4px;
}
```

`static/app.js`：

```javascript
async function loadSensors() {
    const r = await fetch('/sensors');
    const data = await r.json();
    document.getElementById('data').textContent = JSON.stringify(data, null, 2);
}

loadSensors();
setInterval(loadSensors, 5000);
```

## 部署

## 测试

浏览器访问 `http://esp32-ip/`：

- 自动跳到 `/static/`
- 加载 `index.html`
- 加载 `style.css` 和 `app.js`
- JS 每 5 秒请求 `/sensors` 更新数据

需要后端配合：

```python
@app.get('/sensors')
async def sensors(request):
    return {'temperature': 24.5, 'humidity': 65.0}
```

## ⚠️ 路径安全

不加防护的攻击：

```
/static/../etc/passwd
```

`..` 让路径上跳，可能读到敏感文件。**必须验证**。

完整文件：[examples/03_static_files.py](https://github.com/)

## 下一步

- [示例 04 — 流式响应](/examples/04-streaming)：实时数据推送
- [静态文件指南](/guide/static-files)：详细解释
- [部署到 ESP32](/guide/deploy-to-esp32)