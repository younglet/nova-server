# 什么是 nova-server

**nova-server** 是一个给 ESP32 用的微型 Web 框架。整个框架就**一个 35 KB 的 .py 文件**，已经内置在 NovaMP 固件里。

它做的事情很简单：**让你的 ESP32 能响应 HTTP 请求**。

## 解决什么问题？

ESP32 通常跑裸 MicroPython（`main.py` 里 `while True`）。如果想让手机或电脑通过浏览器访问 ESP32 拿数据（比如温度、传感器读数、控制 LED），就需要 HTTP 服务。

自己写 HTTP 服务要处理：

- 解析 HTTP 报文（请求行、headers、body）
- 路由匹配（`/users/42` → 哪个函数处理？）
- 拼装响应（状态码、headers、body）
- 并发处理多个客户端

这些加一起 ~200 行样板代码。**nova-server 帮你写好了，你只写业务逻辑**。

## 一段代码理解

```python
from nova_server import NovaServer

app = NovaServer()

@app.get('/temperature')
async def temperature(request):
    return {'celsius': 24.5}

@app.post('/led')
async def led(request):
    state = request.json.get('state')
    return {'ok': True, 'led': state}

app.run(port=80)
```

浏览器访问：
- `http://esp32-ip/temperature` → `{"celsius": 24.5}`
- `POST http://esp32-ip/led` body `{"state":"on"}` → `{"ok":true,"led":"on"}`

## 谁需要它？

- 📱 移动 App 想调 ESP32 传感器
- 🌐 网页前端想拉 ESP32 数据
- 📊 想做设备状态面板
- 🎛️ 想远程控制 ESP32（开关、参数）

## 定位

| 你需要… | 用什么 |
|---------|--------|
| ESP32 提供 REST API | ✅ nova-server |
| 实时数据推送（传感器、状态） | ✅ nova-server（流式响应） |
| 复杂业务、数据库、用户认证 | ❌ 用 FastAPI / Flask（跑 PC） |
| HTML 模板渲染 | ❌ 用前端 JS 框架 |
| WebSocket | ❌ 暂未支持（路线图） |

## 跟 PC 框架的区别

| 特性 | nova-server | FastAPI / Flask |
|------|-----------|-----------------|
| 跑在哪 | ESP32 / MicroPython | PC / Linux |
| 大小 | 35 KB | 1-500 MB |
| 异步 | asyncio 单线程 | asyncio / 多线程 |
| 数据库 | 用文件或外部 API | SQLAlchemy / ORM |
| 模板 | 不需要（前端 JS） | Jinja2 |
| 部署 | 

## 关键特性

- 🎯 **35 KB 单文件** — 烧进 ESP32 flash 占不到 1%
- ⚡ **全 async** — handler 必须是 `async def`
- 📊 **自动内存回收** — heap 不够时框架自动 `gc.collect()`
- 🔌 **内置 NovaMP** — 不用单独装
- 🪶 **零依赖** — 不需要 mip install

## 下一步

- [第 1 步：写第一个 GET](/guide/first-route) — 5 分钟跑通
- [快速开始](/guide/getting-started) — 烧录固件 + 部署
- [什么是 NovaMP](https://code.stemstar.com/novamp)