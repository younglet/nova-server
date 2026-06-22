---
layout: home

hero:
  name: nova-server
  text: ESP32 上的微型 Web 框架
  tagline: 单文件 35 KB · 内置于 NovaMP · 不用懂 Web 也能用
  actions:
    - theme: brand
      text: 5 分钟跑起来
      link: /guide/basics

features:
  - icon: 🟢
    title: 不用懂 Web 也能用
    details: 不假设你会 HTTP / RESTful。会写 async def 就能写接口。
  - icon: 📦
    title: 单文件 35 KB
    details: 整个框架就一个 .py 文件。烧进 ESP32 flash 占不到 1%。
  - icon: ⚡
    title: 异步非阻塞
    details: 长 I/O 不卡其他连接。流式推送（SSE / NDJSON）开箱即用。
  - icon: 🔌
    title: 内置于 NovaMP
    details: 烧 NovaMP 固件后直接 from nova_server import NovaServer。
  - icon: 📊
    title: 自动内存管理
    details: 不用手动调 gc.collect()。框架在 heap 不够时自动回收。
  - icon: 🪶
    title: 零依赖
    details: 不需要装任何第三方包。MicroPython 标准库全搞定。
---

## 一段代码看懂

```python
from nova_server import NovaServer

app = NovaServer()

@app.get('/')
async def index(request):
    return 'Hello, World!'

app.run(port=80)
```

烧到 ESP32，浏览器访问设备的 IP 就能看到 `Hello, World!`。