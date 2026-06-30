# 示例 04：实时数据推送（SSE）

后台任务产生数据，浏览器实时接收。

## 完整代码

```python
import asyncio
import time
import json

from nova_server import NovaServer, Response

app = NovaServer()

# 全局状态：当前计数
_counter = {'value': 0, 'subs': []}

# ── 后台任务：每 500ms 增加计数 ──

async def _producer():
    while True:
        await asyncio.sleep_ms(500)
        _counter['value'] += 1

        # 通知所有订阅者
        for queue in list(_counter['subs']):
            try:
                queue.put_nowait(_counter['value'])
            except Exception:
                pass    # 队列满 → 丢弃

# 启动后台任务（在 app.run 之前）
asyncio.create_task(_producer())

# ── 路由 ──

@app.get('/')
async def index(request):
    return {
        'endpoints': [
            'GET /counter        - 一次性读计数',
            'GET /stream/counter - 订阅计数变化',
        ],
    }

@app.get('/counter')
async def get_counter(request):
    return {'counter': _counter['value']}

@app.get('/stream/counter')
async def stream_counter(request):
    """订阅计数器变化（多个客户端都能收到）。"""
    queue = asyncio.Queue(maxsize=10)
    _counter['subs'].append(queue)

    async def gen():
        try:
            while True:
                value = await queue.get()
                yield 'data: {{"counter": {}}}\n\n'.format(value)
        finally:
            # 客户端断开 → 取消订阅
            _counter['subs'].remove(queue)

    return Response(
        gen(),
        headers={'Content-Type': 'text/event-stream'},
    )

app.run(port=80)
```

## 部署

## 测试

### 一次性读

### 订阅流

### 浏览器

```html
<script>
const es = new EventSource('/stream/counter');
es.onmessage = e => {
    const data = JSON.parse(e.data);
    document.getElementById('out').textContent = data.counter;
};
</script>
```

多个浏览器同时打开，都会收到相同事件。

完整文件：[examples/04_async_streaming.py](https://github.com/younglet/nova-server/blob/main/template/python/04_async_streaming.py)

## 关键点

### 后台任务

```python
asyncio.create_task(_producer())
```

**在 `app.run()` 之前**调用，server 启动后任务就开始跑。

### 多客户端订阅

用 `asyncio.Queue` 列表：

```python
_subs = []    # 每个客户端一个 Queue

# 订阅时
queue = asyncio.Queue()
_subs.append(queue)

# 推送时
for q in _subs:
    q.put_nowait(value)

# 客户端断开时
_subs.remove(queue)
```

### try/finally 清理

```python
async def gen():
    try:
        # ... yield 数据 ...
    finally:
        _subs.remove(queue)    # 客户端断开时一定会执行
```

## 下一步

- [流式响应指南](/guide/async-streaming)：原理和更多模式
- [静态文件](/guide/static-files)：配前端
- [部署到 ESP32](/guide/deploy-to-esp32)