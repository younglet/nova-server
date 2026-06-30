# 内存监控

ESP32 只有 ~110 KB 可用 heap（启动后）。nova-server 内置**自动 GC**，但你最好了解一下内存状态。

## 自动 GC（默认开启）

> **重要：正常开发不需要手动调用 `gc.collect()`。**
> nova-server 在每次请求处理前后自动检查 heap：剩余 < 10 KB 就回收。
> PC 上没有 `gc.mem_free()`，自动跳过。

nova-server 默认就是 `auto_gc=False`（ESP32 友好），如果你的应用场景需要 GC（如内存吃紧），可以显式开启：

```python
app = NovaServer(auto_gc=True, gc_threshold_kb=100)   # 剩余 < 100KB 才回收
```

或者在 handler 里手动调用：

```python
import gc

@app.post('/upload')
async def upload(request):
    gc.collect()
    data = request.json
    return {'size': len(data)}
```

## 看剩余内存

```python
@app.get('/memory')
async def memory(request):
    free = gc.mem_free()
    used = gc.mem_alloc()
    total = free + used

    if free > 50 * 1024:
        health = 'good'
    elif free > 10 * 1024:
        health = 'ok'
    else:
        health = 'low'

    return {
        'free_bytes': free,
        'used_bytes': used,
        'health': health,
    }
```

测试：

## 内存分级

| 剩余 heap | 状态 | 怎么办 |
|----------|------|--------|
| > 50 KB | 🟢 健康 | 不用管 |
| 20-50 KB | 🟡 注意 | 减少大对象 |
| 5-20 KB | 🟠 危险 | 检查泄漏 |
| < 5 KB | 🔴 立即崩溃 | 重启 |

## 内存泄漏常见原因

### 全局列表无界增长

```python
# ❌ 每次请求都加，永远不删
LOGS = []

@app.post('/log')
async def log(request):
    LOGS.append(request.json)   # heap 一直涨
    return {'ok': True}

# ✅ 限制大小
LOGS = []
MAX = 100

@app.post('/log')
async def log(request):
    LOGS.append(request.json)
    if len(LOGS) > MAX:
        LOGS.pop(0)    # 保持最多 100 条
    return {'ok': True}
```

### 大文件读到内存

```python
# ❌ 整个文件读到内存
@app.get('/file')
async def file(request):
    with open('/big.bin', 'rb') as f:
        data = f.read()    # 可能 OOM
    return data

# ✅ 流式读取（一次 4KB）
@app.get('/file')
async def file(request):
    async def gen():
        with open('/big.bin', 'rb') as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                yield chunk
                await asyncio.sleep(0)
    return Response(gen(), headers={'Content-Type': 'application/octet-stream'})
```

### 字符串拼接产生中间对象

```python
# ❌ 慢 + 费内存
result = ''
for item in items:
    result += str(item) + ','

# ✅ 用 join
result = ','.join(str(i) for i in items)
```

## 主动 GC 什么时候调？

| 场景 | 调吗 |
|------|------|
| 启动时 | ✅（nova-server 已自动） |
| 大分配前 | ✅ 建议 |
| 每个请求前 | ❌ 框架已自动 |
| 后台循环里 | ✅ 建议（每分钟一次） |

```python
async def _gc_loop():
    while True:
        await asyncio.sleep(60)
        gc.collect()

asyncio.create_task(_gc_loop())
```

## fragmentation

频繁分配不同大小的对象会让 heap **碎片化**：

```
剩余：30 KB
  ├─ 6 KB 块
  ├─ 5 KB 块
  ├─ 3 KB 块
  ├─ 8 KB 块
  └─ 8 KB 块

申请 20 KB → ❌ 没有连续 20 KB 块
```

`gc.collect()` 会合并碎片。

## 下一步

- [GPIO 安全](/hardware/gpio-safety)
- [WiFi 最佳实践](/hardware/wifi)
- [功耗与重启](/hardware/power-and-reset)