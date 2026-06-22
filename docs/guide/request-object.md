# Request 对象

每次请求，框架会创建一个 `Request` 对象，传给你的 handler。它包含客户端发的所有信息。

## 怎么拿到

`Request` 对象是 handler 的第一个参数。名字随便起，但用 `request` 最清楚：

```python
@app.get('/')
async def index(request):       # ← 这个 request 就是 Request 对象
    return 'path = ' + request.path
```

## 主要属性

### `request.method`

HTTP 方法（`'GET'`、`'POST'` 等）。

```python
@app.route('/any', methods=['GET', 'POST'])
async def any_method(request):
    if request.method == 'GET':
        return 'read'
    return 'write'
```

### `request.path`

URL 路径（不含 `?` 后面的查询字符串）。

```python
# GET /search?q=hello
request.path            # '/search'   （不是 '/search?q=hello'）
```

### `request.args`

查询字符串（解析成 dict 形式）。

```python
# GET /search?q=hello&page=2
request.args['q']                 # 'hello'
request.args.get('page', '1')    # '2'
request.args.getlist('tag')      # 多值：['a', 'b', 'c']
```

详细用法看 [查询字符串](/guide/query-strings)。

### `request.headers`

HTTP headers（大小写不敏感）。

```python
ua = request.headers['User-Agent']
ct = request.headers['content-type']    # 大小写都行
```

### `request.cookies`

Cookies（自动解析）。

```python
# Cookie: session=abc123; theme=dark
session = request.cookies.get('session', '')
```

### `request.json`

POST/PUT 的 JSON body。如果 Content-Type 是 `application/json`，自动解析成 dict。

```python
# POST /api/users, body: {"name":"Alice"}
data = request.json       # {'name': 'Alice'}
name = data.get('name')   # 'Alice'
```

不是 JSON 时返回 `None`。

### `request.form`

URL-encoded 表单（Content-Type: `application/x-www-form-urlencoded`）。

```python
# POST /login, body: username=alice&password=secret
user = request.form['username']
pwd = request.form['password']
```

### `request.body`

原始 body（bytes）。

```python
raw = request.body    # b'...'
```

### `request.client_addr`

客户端地址。

```python
ip = request.client_addr[0]    # '192.168.1.5'
```

### `request.g`

请求级共享数据（在 before_request 里塞，handler 里读）。看 [钩子](/guide/hooks)。

## 完整例子

```python
@app.post('/api/echo')
async def echo(request):
    return {
        'method': request.method,
        'path': request.path,
        'args': dict(request.args),
        'headers': dict(request.headers),
        'cookies': dict(request.cookies),
        'json': request.json,
        'client_ip': request.client_addr[0],
    }
```

测试：

返回：

```json
{
  "method": "POST",
  "path": "/api/echo",
  "args": {"name": "test"},
  "headers": {"Content-Type": "application/json", "X-Custom": "hello", ...},
  "cookies": {"session": "abc"},
  "json": {"msg": "hi"},
  "client_ip": "192.168.1.5"
}
```

## 请求大小限制

框架默认限制 body 最大 16 KB。超过会返回 413。

可以在创建 app 时改：

```python
# 这种方式暂时不支持，需要继承 Request 类
# class BigRequest(Request):
#     max_content_length = 1024 * 1024  # 1MB
```

## 小结

| 想拿什么 | 写法 |
|---------|------|
| 方法 | `request.method` |
| 路径 | `request.path` |
| 查询参数 | `request.args` |
| Headers | `request.headers` |
| Cookies | `request.cookies` |
| JSON body | `request.json` |
| 表单 body | `request.form` |
| 客户端 IP | `request.client_addr` |

## 下一步

- [Response 对象](/guide/response-object)
- [钩子](/guide/hooks) — before/after request
- [静态文件](/guide/static-files)