# 实时推送（流式响应）

普通接口是「一次性」返回 — server 准备好所有数据再发。

流式响应是**边生成边发**。比如：

- 传感器数据每秒推一次
- 日志实时显示
- 长任务进度更新

## 两种流式格式

| 格式 | 用途 | 浏览器端 |
|------|------|---------|
| **SSE** | 浏览器 EventSource | 直接用 |
| **NDJSON** | JS fetch | 解析 JSON |

## 最简 SSE 例子

```python
from nova_server import NovaServer, Response

app = NovaServer()

@app.get('/stream/time')
async def stream_time(request):
    """每秒推一个时间戳。"""
    async def gen():
        for i in range(60):
            yield 'data: {{"i": {}, "ts": {}}}{nl}{nl}'.format(
                i, int(time.time()), nl=chr(10))
            await asyncio.sleep(1)
    return Response(
        gen(),
        headers={'Content-Type': 'text/event-stream'},
    )

import asyncio, time
app.run(port=80)
```

SSE 格式：

```
data: {"i": 0, "ts": 12345}\n\n
data: {"i": 1, "ts": 12346}\n\n
data: {"i": 2, "ts": 12347}\n\n
...
```

每个事件以 `\n\n` 结尾。

## 测试

### 用 

`-N` 是「不要缓冲」，实时显示。

### 用浏览器

```html
<script>
const es = new EventSource('/stream/time');
es.onmessage = e => console.log(JSON.parse(e.data));
</script>
```

## 后台任务 + 流式推送

最常见的场景：**后台任务产生数据 → 推给所有订阅者**。

```python
import asyncio

app = NovaServer()

# 全局订阅者列表
_subscribers = []
# 全局状态
_state = {'counter': 0}

async def _producer():
    """后台任务：每 500ms 增加计数，并通知所有订阅者。"""
    while True:
        await asyncio.sleep_ms(500)
        _state['counter'] += 1

        # 通知所有订阅者
        for queue in list(_subscribers):
            try:
                queue.put_nowait(_state['counter'])
            except Exception:
                pass    # 队列满 → 丢弃

# 启动后台任务
asyncio.create_task(_producer())

@app.get('/counter')
async def get_counter(request):
    """一次性读。"""
    return {'counter': _state['counter']}

@app.get('/stream/counter')
async def stream_counter(request):
    """订阅计数器变化。"""
    queue = asyncio.Queue(maxsize=10)
    _subscribers.append(queue)

    async def gen():
        try:
            while True:
                value = await queue.get()
                yield 'data: {{"counter": {}}}{nl}{nl}'.format(
                    value, nl=chr(10))
        finally:
            _subscribers.remove(queue)    # 客户端断开时取消订阅

    return Response(
        gen(),
        headers={'Content-Type': 'text/event-stream'},
    )

app.run(port=80)
```

测试：

## NDJSON（每行一个 JSON）

适合日志流、批量数据：

```python
@app.get('/stream/logs')
async def stream_logs(request):
    async def gen():
        for i in range(100):
            log = {
                'seq': i,
                'level': 'INFO',
                'msg': 'event {}'.format(i),
            }
            yield json.dumps(log) + '\n'
            await asyncio.sleep_ms(100)
    return Response(
        gen(),
        headers={'Content-Type': 'application/x-ndjson'},
    )
```

测试：

## 客户端断开处理

流式响应最常见的问题：客户端断开后，**async generator 还在跑**，浪费 CPU。

用 `try/finally` 清理：

```python
@app.get('/stream/heavy')
async def heavy(request):
    queue = asyncio.Queue(maxsize=10)
    _subscribers.append(queue)

    async def gen():
        try:
            while True:
                value = await queue.get()
                yield 'data: {}\n\n'.format(value)
        finally:
            # 客户端断开 → 清理
            _subscribers.remove(queue)

    return Response(gen(), headers={'Content-Type': 'text/event-stream'})
```

## 在哪里启动后台任务

`asyncio.create_task(...)` 在 `app.run()` **之前**调用：

```python
import asyncio

async def background_task():
    while True:
        await asyncio.sleep(1)
        # ... 做点啥 ...

# ★ 在 run 之前启动
asyncio.create_task(background_task())

app.run(port=80)
```

如果用 `await app.start_server(...)`（异步版本），后台任务在 `await` 之前启动：

```python
async def main():
    asyncio.create_task(background_task())
    await app.start_server(host='0.0.0.0', port=80)

asyncio.run(main())
```

## 完整例子：温度监控

```python
import asyncio
import dht
from machine import Pin
from nova_server import NovaServer, Response

app = NovaServer()
_sensor = dht.DHT22(Pin(4))

_state = {'temp': 0, 'hum': 0, 'subs': []}

async def _read_sensor():
    """每 2 秒读一次 DHT22。"""
    while True:
        try:
            _sensor.measure()
            _state['temp'] = _sensor.temperature()
            _state['hum'] = _sensor.humidity()
            # 广播
            for q in list(_state['subs']):
                try:
                    q.put_nowait({'temp': _state['temp'], 'hum': _state['hum']})
                except Exception:
                    pass
        except OSError as e:
            print('[sensor]', e)
        await asyncio.sleep(2)

asyncio.create_task(_read_sensor())

@app.get('/api/sensors')
async def read_now(request):
    """一次性读最新数据。"""
    return {'temperature': _state['temp'], 'humidity': _state['hum']}

@app.get('/stream/sensors')
async def stream_sensors(request):
    """订阅传感器变化。"""
    q = asyncio.Queue(maxsize=5)
    _state['subs'].append(q)
    async def gen():
        try:
            while True:
                data = await q.get()
                yield 'data: {}\n\n'.format(json.dumps(data))
        finally:
            _state['subs'].remove(q)
    return Response(gen(), headers={'Content-Type': 'text/event-stream'})

app.run(port=80)
```

## 小结

| 想做 | 怎么做 |
|------|--------|
| 服务器推送 | 返回 `async generator` |
| 浏览器 EventSource | Content-Type: `text/event-stream` |
| 实时日志 / 数据 | Content-Type: `application/x-ndjson` |
| 后台任务 | `asyncio.create_task(...)` |
| 多客户端广播 | 用 `asyncio.Queue` 列表 |
| 客户端断开清理 | `try/finally` |

## 下一步

- [部署到 ESP32](/guide/deploy-to-esp32)
- [静态文件](/guide/static-files)
- [钩子](/guide/hooks)