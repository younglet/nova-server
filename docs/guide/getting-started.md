# 快速开始

5 分钟把 nova-server 跑起来。

## 步骤 1：准备 ESP32

1. 一块 ESP32 开发板
2. 已烧 **NovaMP** 固件（包含 MicroPython + nova-server）
3. 用 USB 连上电脑

如果你还没烧 NovaMP 固件，看 [NovaMP 固件](https://code.stemstar.com/novamp)。

## 步骤 2：连接设备

进 REPL：

```
MicroPython v1.28.0 on ESP32
>>>
```

试试：

```python
>>> from nova_server import NovaServer
>>> print(NovaServer)
<class 'NovaServer'>
```

能 import 成功说明固件没问题。

## 步骤 3：写代码

电脑上新建 `main.py`：

```python
from nova_server import NovaServer

app = NovaServer()

@app.get('/')
async def index(request):
    return 'Hello, World!'

app.run(port=80)
```

## 步骤 4：测试

找到 ESP32 的 IP，假设是 `192.168.1.42`，浏览器访问 `http://192.168.1.42/`。

应该看到：

```
Hello, World!
```

🎉 第一个 nova-server 应用跑起来了！

## 下一步

- [你的第一个 GET 路由](/guide/first-route) — 详细解释
- [加更多路由](/guide/more-routes)
- [返回 JSON](/guide/return-json)
- [部署到 ESP32](/guide/deploy-to-esp32) — 完整流程