"""
04_async_streaming.py — 实时数据流（SSE + NDJSON）
====================================================

演示怎么把后台任务产生的数据实时推给浏览器。

什么是 SSE（Server-Sent Events）？
  一种浏览器能直接用的"服务器推送"技术。
  浏览器连一次，服务器就能一直往回推数据。

用法（浏览器端）：
  const es = new EventSource('/stream/counter');
  es.onmessage = e => console.log(JSON.parse(e.data));

用法（curl 端）：
  curl -N http://192.168.1.42/stream/counter

部署：
  mpremote connect COM3 cp main.py :main.py
  mpremote reset

测试：
  curl http://192.168.1.42/                    # 路由表
  curl http://192.168.1.42/counter             # 当前计数
  curl -N http://192.168.1.42/stream/sse       # 时间戳流
  curl -N http://192.168.1.42/stream/counter    # 计数器变化流
"""

import asyncio
import time

from nova_server import NovaServer, Response


app = NovaServer()


# ── 全局状态 ─────────────────────────────────────────
# 计数器当前值；后台任务每秒增加；流接口推送给订阅者。
_counter = {'value': 0, 'subs': []}


# ── 后台任务：每 500ms 增加计数 ─────────────────────

async def _producer():
    """后台不停跑。"""
    while True:
        await asyncio.sleep(0.5)        # 500ms（PC 和 MicroPython 通用）
        _counter['value'] += 1
        # 通知所有订阅者
        for queue in list(_counter['subs']):
            try:
                queue.put_nowait(_counter['value'])
            except Exception:
                pass    # 队列满 → 丢弃


# ── 路由 ────────────────────────────────────────────────

@app.get('/')
async def index(request):
    """首页：列出可用流。"""
    return {
        'endpoints': [
            'GET /counter         - 一次性读计数',
            'GET /stream/sse      - 时间戳流（推 60 次）',
            'GET /stream/counter  - 计数器变化流',
        ],
    }


@app.get('/counter')
async def get_counter(request):
    """一次性读当前计数。"""
    return {'counter': _counter['value']}


@app.get('/stream/sse')
async def stream_sse(request):
    """每 1 秒推一个时间戳，共 60 次。"""
    nl = chr(10)
    async def gen():
        for i in range(60):
            yield 'data: {{"i": {}, "ts": {}}}{nl}{nl}'.format(
                i, int(time.time()), nl=nl)
            await asyncio.sleep(1)
    return Response(
        gen(),
        headers={'Content-Type': 'text/event-stream'},
    )


@app.get('/stream/counter')
async def stream_counter(request):
    """当计数器变化时推送。"""
    nl = chr(10)
    async def gen():
        last = -1
        for _ in range(120):           # 推 60 秒
            current = _counter['value']
            if current != last:
                yield 'data: {{"counter": {}}}{nl}{nl}'.format(
                    current, nl=nl)
                last = current
            await asyncio.sleep(0.2)    # 200ms
    return Response(
        gen(),
        headers={'Content-Type': 'text/event-stream'},
    )


# ── 启动 ────────────────────────────────────────────────

async def main():
    # ★ 关键：后台任务必须在 event loop 里启动
    asyncio.create_task(_producer())
    print('Server starting on 0.0.0.0:80')
    await app.start_server(host='0.0.0.0', port=80)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('stopped')