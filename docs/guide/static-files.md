# 静态文件

把 HTML / CSS / JS 放到 ESP32 上，通过浏览器访问。

## 文件放在哪

直接把前端文件放到 ESP32 的 `static/` 目录：

```
ESP32
├── main.py
└── static/
    ├── index.html
    ├── style.css
    └── app.js
```

## server 怎么写

```python
from nova_server import NovaServer, send_file

app = NovaServer()

@app.get('/static/')
async def static_index(request):
    return send_file('/static/index.html', max_age=3600)

@app.get('/static/<path:filename>')
async def static_file(request, filename):
    # 防路径穿越（../
    if '..' in filename.split('/') or filename.startswith('/'):
        return {'error': 'forbidden'}, 403

    try:
        return send_file('/static/' + filename, max_age=3600)
    except OSError:
        return {'error': 'not found'}, 404

app.run(port=80)
```

## 部署

## 测试

浏览器访问 `http://esp32-ip/static/index.html` 即可看到页面。

## 一个最小的 HTML

放一个 `static/index.html`：

```html
<!DOCTYPE html>
<html>
<head>
    <title>My ESP32</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Hello from ESP32!</h1>
    <button onclick="fetchData()">Get Sensors</button>
    <pre id="output"></pre>
    <script src="/static/app.js"></script>
</body>
</html>
```

`static/style.css`：

```css
body { font-family: sans-serif; padding: 20px; }
button { padding: 10px 20px; }
pre { background: #f0f0f0; padding: 10px; }
```

`static/app.js`：

```javascript
async function fetchData() {
    const response = await fetch('/api/sensors');
    const data = await response.json();
    document.getElementById('output').textContent = JSON.stringify(data, null, 2);
}
```

## 为什么用 `/static/` 前缀？

路径前缀 `/static/` 让静态文件和动态 API **分开**：

| URL | 来自 |
|-----|------|
| `/` | 你的 handler |
| `/api/...` | 你的 handler |
| `/static/...` | ESP32 上的文件 |

否则访问 `/index.html` 也会被你注册的 handler 处理，可能冲突。

## 自动 Content-Type

`send_file` 根据扩展名自动设置：

| 扩展 | MIME |
|------|------|
| `.html` | text/html |
| `.css` | text/css |
| `.js` | application/javascript |
| `.json` | application/json |
| `.png` | image/png |
| `.jpg` | image/jpeg |
| `.txt` | text/plain |
| 其他 | application/octet-stream |

## 浏览器缓存

`max_age=3600` 让浏览器**缓存 1 小时**：

```python
return send_file('/static/' + filename, max_age=3600)
```

下次访问同一文件，浏览器不发请求，直接用本地缓存。ESP32 压力小很多。

## ⚠️ 路径安全

不加防护的话，攻击者能这样访问：

```
/static/../etc/passwd
```

`..` 让路径上跳一级，可能读到系统敏感文件。

**必须验证**：

```python
@app.get('/static/<path:filename>')
async def static_file(request, filename):
    if '..' in filename.split('/') or filename.startswith('/'):
        return {'error': 'forbidden'}, 403
    # ...
```

## 完整例子

`examples/03_static_files.py` 是一个可直接运行的完整示例：

```python
from nova_server import NovaServer, send_file, redirect

app = NovaServer()

def _is_safe(path):
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

## SPA 单页应用

前端用 Vue/React 时，所有 URL 都返回同一个 index.html：

```python
@app.get('/<path:path>')
async def spa(request, path):
    # 先尝试静态文件
    if _is_safe(path):
        try:
            return send_file('/static/' + path, max_age=3600)
        except OSError:
            pass
    # fallback 到 index.html（前端路由处理）
    return send_file('/static/index.html')
```

## 小结

| 步骤 | 怎么做 |
|------|--------|
| 1. 准备文件 | 放到 ESP32 的 `/static/` |
| 2. 注册路由 | `@app.get('/static/<path:filename>')` |
| 3. 验证路径 | 拒绝 `..` |
| 4. send_file | 自动 Content-Type + 缓存 |

## 下一步

- [钩子](/guide/hooks)
- [实时推送](/guide/async-streaming)
- [部署到 ESP32](/guide/deploy-to-esp32)