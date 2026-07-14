# 后台周期任务（@app.task）

> 让不熟悉 asyncio 的同学也能写"循环判断"程序。
> v0.2+ 新功能。

## 一句话总结

```python
@app.task(interval_ms=30)               # 装饰器
def check_button():
    if _btn.is_clicked():
        _led.switch()
```

不用 `async def`、不用 `while True`、不用 `asyncio.create_task`，写普通函数就行。

---

## 三种写法

### 装饰器（推荐）

```python
from nova_server import NovaServer

app = NovaServer()


@app.task(interval_ms=1000)
def heartbeat():
    print('tick')


@app.task(interval_ms=2000)
async def read_sensor():        # 异步函数也行，自动检测
    await sensor.read()
    print(sensor.value)
```

### 函数式（适合 lambda）

```python
def ping():
    print('ping')

app.add_task(ping, interval_ms=500)

app.add_task(lambda: print('anon'), interval_ms=1000, name='anon_tick')
```

### 运行时查看

```python
>>> app.tasks()
[
  {'name': 'heartbeat',   'interval_ms': 1000, 'is_async': False, 'running': True},
  {'name': 'read_sensor', 'interval_ms': 2000, 'is_async': True,  'running': True},
]
```

---

## 完整例子：按钮 → LED

```python
from nova_server import NovaServer
from machine import Pin
from button import Button
from led import LED

app = NovaServer()
_btn = Button(Pin(4))
_led = LED(Pin(2))


@app.task(interval_ms=30)
def check_button():
    if _btn.is_clicked():
        _led.switch()


app.get('/api/led')(lambda req: {'led': _led.is_on})
app.run()
```

---

## 设计细节

### 装饰器参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `interval_ms` | int | `50` | 调用间隔（毫秒）。**建议 ≥ 10** |

### 同步 vs 异步函数

两种都支持，自动检测：

- 装饰 `def f(): pass`（同步）—— nova-server 直接调用，**不能 `await`**。函数必须短小，**不要在里面 `time.sleep()`**，会阻塞整个事件循环。
- 装饰 `async def f(): pass`（异步）—— nova-server 用 `await f()` 调用，**可以 `await asyncio.sleep_ms()`**。

### 错误隔离

一个 task 抛异常会被捕获、打印到 REPL，但**不会**中断 server 或其他 task：

```python
@app.task(interval_ms=100)
def bad():
    raise ValueError('boom')        # REPL 看到 [task] bad error: ...
                                   # 但其他 task 和 server 都正常
```

### 启动时机

`@app.task` 装饰的任务会在 `app.run()` 或 `await app.start_server()` 调用时自动启动，跟 server 同生死，server 关了 task 也结束。

### 重名检测

同名（`__name__` 相同）的 task 重复注册会抛 `ValueError`，引导用户改函数名：

```python
@app.task(interval_ms=100)
def tick():
    pass

@app.task(interval_ms=200)
def tick():        # ValueError: Task 'tick' already registered
    pass
```

---

## 对比：改造前 vs 改造后

### 改造前（用户必须懂 asyncio）

```python
import asyncio
from nova_server import NovaServer

app = NovaServer()


async def button_poll_loop():                    # ❌ 必须 async def
    while True:                                   # ❌ 必须 while True
        if _btn.is_clicked():
            _led.switch()
        await asyncio.sleep_ms(30)                # ❌ 必须 await，不能 time.sleep


async def main():
    asyncio.create_task(button_poll_loop())       # ❌ 必须 create_task
    await app.start_server()


if __name__ == '__main__':
    asyncio.run(main())                           # ❌ 必须 asyncio.run
```

### 改造后（新手 1 行搞定）

```python
from nova_server import NovaServer

app = NovaServer()


@app.task(interval_ms=30)                         # ✅ 一行搞定
def check_button():
    if _btn.is_clicked():
        _led.switch()


app.run()
```

---

## 适用场景 vs 不适用

### ✅ 适合

- 按钮 / 触摸 / 旋钮轮询（< 50Hz）
- 温湿度、光照等慢传感器定期读
- LED 呼吸、心跳、状态指示
- 状态机（短按 / 长按 / 双击检测）

### ❌ 不适合

- 高速采样（>100Hz）→ 用 [`machine.Timer`](https://docs.micropython.org/en/latest/library/machine.Timer.html) 硬件定时器
- 严格周期任务（要求 ±1ms 精度）→ 同上
- 长时间阻塞操作 → 用异步函数 + `await asyncio.sleep_ms()`

---

## 进阶：手动管理 task

如果你需要动态添加 / 移除 task，用函数式 API：

```python
# 注册
app.add_task(some_func, interval_ms=500, name='my_task')

# 列出
print(app.tasks())

# 取消（v0.3+ 计划，目前只能等 server 关闭）
# app.cancel('my_task')
```

> **当前版本**（v0.2）只提供装饰器 + `add_task` + `tasks()` 三个 API。
> `cancel(name)` 在 v0.3 计划加入。

---

## 底层原理（给好奇的同学）

`@app.task` 内部把同步/异步函数包装成 `asyncio` 协程，然后用 `asyncio.create_task` 启动。`start_server()` 在创建 socket 后立即启动所有已注册 task：

```python
# nova_server.py 内部简化版
async def _run_task(self, idx):
    name, func, interval_ms, is_async, _ = self._tasks[idx]
    while True:
        try:
            if is_async:
                await func()
            else:
                func()
        except Exception as e:
            print('[task] {} error: {}'.format(name, e))
        await asyncio.sleep_ms(interval_ms)

async def start_server(self, ...):
    ...
    # 启动所有 task（在 socket 起来之后、serve_forever 之前）
    for i in range(len(self._tasks)):
        self._tasks[i][4] = asyncio.create_task(self._run_task(i))
    ...
```

**关键技术点**：MicroPython 上没有 `inspect.iscoroutinefunction`，nova-server 用本地 helper 检测：

```python
def _iscoroutinefunction(f):
    if type(f).__name__ == 'generator':    # MicroPython 路径
        return True
    try:                                   # CPython 路径
        return bool(f.__code__.co_flags & 0x100)
    except (AttributeError, TypeError):
        return False
```

---

## 下一步

- 按钮示例：[`template/python/06_task_loop.py`](https://github.com/your-repo/template/python/06_task_loop.py)
- 硬件示例：[`template/python/02_sensors_api.py`](https://github.com/your-repo/template/python/02_sensors_api.py)
- nova-server 入门：[`docs/guide/getting-started.md`](/guide/getting-started)