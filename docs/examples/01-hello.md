# 示例 01：Hello World

最小 nova-server 应用。3 个路由。

## 完整代码

```python
from nova_server import NovaServer

app = NovaServer()

@app.get('/')
async def index(request):
    return 'Hello, World!'

@app.get('/info')
async def info(request):
    return {'server': 'nova-server', 'version': '0.1.0'}

@app.get('/time')
async def time(request):
    import time
    if hasattr(time, 'ticks_ms'):
        return {'uptime_sec': time.ticks_ms() // 1000}
    return {'uptime_sec': 0}

app.run(port=80)
```

## 路由

| 路径 | 返回 |
|------|------|
| `/` | `Hello, World!` |
| `/info` | JSON |
| `/time` | JSON，启动后秒数 |

## 部署

## 测试

完整文件：[examples/01_hello.py](https://github.com/younglet/nova-server/blob/main/template/python/01_hello.py)

## 下一步

- [示例 02 — 传感器 API](/examples/02-sensors)：读真实硬件
- [第一个 GET 路由](/guide/first-route)：从零开始
- [返回 JSON](/guide/return-json)