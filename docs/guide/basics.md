# 必读基础

如果你从没接触过 Web 后端 / HTTP / 服务器，先读这一页。

只要 5 分钟。

## 什么是 HTTP？

HTTP 是一种「**客户端问 → 服务器答**」的协议。

- **客户端**：浏览器、App
- **服务器**：跑在 ESP32 上的 nova-server

每次交互有两步：

```
客户端  ──── "GET /hello" ────►  服务器
客户端  ◄──── "Hello, World!" ──  服务器
```

## 什么是 URL？

URL 就是网址，比如：

```
http://192.168.1.42/hello?name=World
│      │             │      │
│      │             │      └─ 查询字符串（可选，见下）
│      │             └─────── 路径
│      └───────────────────  IP 地址
└────────────────────────── 协议
```

**路径**告诉服务器要访问哪个接口。

| URL | 路径 |
|-----|------|
| `http://esp32/` | `/` |
| `http://esp32/about` | `/about` |
| `http://esp32/users/42` | `/users/42` |

## 什么是「端口」？

一台机器可以跑多个服务（HTTP、SSH、MQTT…）。**端口**用来区分它们。

| 端口 | 通常是 |
|------|--------|
| 80 | HTTP（浏览器默认） |
| 443 | HTTPS |
| 22 | SSH |
| 5000 | nova-server 默认（PC 测试时） |

访问 `http://esp32-ip/` 实际是访问 `http://esp32-ip:80/`（80 是 HTTP 默认）。

如果你用其他端口，要加 `:端口号`：

```
http://esp32-ip:5000/    # 5000 端口
```

## 什么是 HTTP 方法？

最常见的是 `GET` 和 `POST`。

| 方法 | 用途 | 类比 |
|------|------|------|
| **GET** | 读数据 | 你在网页上看文章 |
| **POST** | 发数据 | 你提交表单 |

浏览器地址栏访问网页 = **GET** 请求。

## 什么是「接口」？

接口 = 一个 URL 地址 + 处理函数。

nova-server 里写一个接口：

```python
@app.get('/hello')              # 路径
async def hello(request):        # 处理函数
    return 'Hello!'              # 返回内容
```

只要这样写，访问 `http://esp32-ip/hello` 就会返回 `Hello!`。

## 什么是 JSON？

JSON 是一种数据格式。长得像 Python 的 dict / list：

```json
{
  "name": "Alice",
  "age": 30,
  "hobbies": ["reading", "coding"]
}
```

nova-server 里你返回 dict，**自动**转 JSON：

```python
@app.get('/api/user')
async def user(request):
    return {'name': 'Alice', 'age': 30}
    # ↑ 这个 dict 自动变 JSON
```

客户端拿到的是：

```json
{"name": "Alice", "age": 30}
```

## 什么是 async / await？

nova-server 的 handler 必须是 `async def`，函数里可能用 `await`。

简单理解：

- `async def` = 「这个函数可以**等待**别的事情」
- `await xxx()` = 「先停一下，等 xxx 完成再继续」
- 等待时**不卡**其他客户端

```python
@app.get('/slow')
async def slow(request):
    await asyncio.sleep(1)    # 等 1 秒（不卡 server）
    return 'done'
```

为什么需要？因为 ESP32 单核，没线程。普通 `time.sleep(1)` 会让整个 server 卡 1 秒。

## 什么是 IP 地址？

IP 是设备在网络里的地址。

| 设备 | IP 例子 |
|------|---------|
| 你的电脑 | 192.168.1.10 |
| ESP32 | 192.168.1.42 |
| 路由器 | 192.168.1.1 |

同一 WiFi 下的设备可以互相访问。手机连 ESP32 的热点也能访问。

## 什么是 REPL？

REPL = **R**ead-**E**val-**P**rint **L**oop。就是你能在电脑上打字让 ESP32 立刻执行：

```
>>> 1 + 2
3
>>> import network
>>> w = network.WLAN(network.STA_IF)
>>> w.isconnected()
True
```

非常适合调试。

## 名词对照表

| 名词 | 是什么 |
|------|--------|
| HTTP | 客户端-服务器通信协议 |
| URL | 网址 |
| 路径 | `/about` 这种 |
| 端口 | 一个机器上的多个服务用端口区分 |
| GET | 读数据 |
| POST | 发数据 |
| 接口 / 路由 | URL + 处理函数 |
| JSON | 数据格式（像 Python dict） |
| async / await | Python 异步语法 |
| IP 地址 | 设备在网络里的地址 |
| REPL | 交互式命令行 |
| MicroPython | 跑在微控制器上的 Python |
| NovaMP | nova-frontend 团队的 MicroPython 定制版（含 nova-server） |
| ESP32 | 乐鑫出的微控制器芯片（带 WiFi） |
| GPIO | ESP32 上的引脚，可接 LED / 传感器 |

## 下一步

读完这些，就可以看代码了：

- [第一个 GET 路由](/guide/first-route) — 5 分钟跑通
- [快速开始](/guide/getting-started) — 烧录固件 + 部署