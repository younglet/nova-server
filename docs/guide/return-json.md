# 返回 JSON

实际接口几乎都返回 JSON。在 nova-server 里，**返回 dict 或 list 就自动转 JSON**。

## 最简例子

```python
from nova_server import NovaServer

app = NovaServer()

@app.get('/api/info')
async def info(request):
    return {
        'name': 'nova-server',
        'version': '0.1.0',
    }

app.run(port=80)
```

返回 dict 框架会**自动**：

1. 调 `json.dumps(...)` 序列化
2. 设 `Content-Type: application/json`
3. 算 `Content-Length`

测试：

输出：

```
HTTP/1.0 200 OK
Content-Type: application/json; charset=UTF-8
Content-Length: 53

{"name": "nova-server", "version": "0.1.0"}
```

## dict 和 list 都行

```python
@app.get('/api/users')
async def users(request):
    return [
        {'id': 1, 'name': 'Alice'},
        {'id': 2, 'name': 'Bob'},
    ]
```

## 支持的类型

| Python | JSON |
|--------|------|
| dict | object `{...}` |
| list | array `[...]` |
| str | string `"..."` |
| int / float | number |
| True / False | true / false |
| None | null |

不支持：bytes、set、自定义对象。

## 中文

直接写就行：

```python
@app.get('/api/info')
async def info(request):
    return {
        'name': '智能家居',
        'author': '小明',
    }
```

## 返回 JSON + 状态码

用元组：`(body, status_code)`。

```python
@app.get('/api/items/<int:id>')
async def get_item(request, id):
    item = db.get(id)
    if item is None:
        return {'error': 'not found'}, 404
    return item, 200
```

也可以加 headers：

```python
return {'data': '...'}, 200, {'X-Custom': 'value'}
```

## 真实例子：传感器 API

```python
from nova_server import NovaServer
from machine import Pin, ADC
import dht

app = NovaServer()

_sensor = dht.DHT22(Pin(4))
_adc = ADC(Pin(34))
_adc.atten(ADC.ATTN_11DB)

@app.get('/api/sensors')
async def sensors(request):
    _sensor.measure()
    return {
        'temperature': _sensor.temperature(),
        'humidity': _sensor.humidity(),
        'light': _adc.read(),
    }
```

## 三种返回方式

```python
# 1. 返回字符串 → Content-Type: text/plain
@app.get('/text')
async def text(request):
    return 'hello'

# 2. 返回 dict / list → Content-Type: application/json
@app.get('/json')
async def json(request):
    return {'k': 'v'}

# 3. 返回 Response 对象 → 高级用法，看 Response 对象章节
@app.get('/custom')
async def custom(request):
    from nova_server import Response
    return Response('hi', status_code=201, headers={'X-Foo': 'bar'})
```

## 返回值转 JSON 的限制

MicroPython 的 `json.dumps` 比 CPython 简单：

- ❌ 不支持 `indent` 参数（不能美化输出）
- ❌ 不支持 `sort_keys` 参数
- ✅ 支持 `ensure_ascii=False`（让中文不被转义）

如果需要美化输出，在 PC 上调试更方便。

## 大 JSON 的注意

返回大 dict 会先**整体序列化到字符串**，再用 heap 内存发出去。

ESP32 启动后只有约 110 KB 可用 heap。如果一次返回 1 MB 数据，会 OOM。

解决方案：

```python
# ❌ 危险：可能 OOM
@app.get('/api/all-logs')
async def all_logs(request):
    return {'logs': read_all_logs()}    # 假设 1MB

# ✅ 用查询字符串分页
@app.get('/api/logs')
async def logs(request):
    page = int(request.args.get('page', '1'))
    return {'logs': read_page(page)}

# ✅ 大数据量用流式响应（不占内存）
@app.get('/api/logs/stream')
async def logs_stream(request):
    async def gen():
        for line in read_logs():
            yield json.dumps(line) + '\n'
    return Response(gen(), headers={'Content-Type': 'application/x-ndjson'})
```

流式响应看 [实时推送](/guide/async-streaming)。

## 小结

| 需求 | 写法 |
|------|------|
| 返回 JSON | `return {...}` 或 `return [...]` |
| JSON + 状态码 | `return {...}, 404` |
| JSON + 自定义头 | `return {...}, 200, {'X-Foo': 'bar'}` |

## 下一步

- [POST 请求](/guide/post-requests) — 客户端发数据
- [错误处理](/guide/errors) — 返回 4xx / 5xx
- [Response 对象](/guide/response-object) — 高级用法