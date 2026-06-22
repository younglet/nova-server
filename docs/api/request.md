# Request

请求对象。每次请求框架创建一个，传给你的 handler。

完整使用看 [Request 对象指南](/guide/request-object)。

## 属性

### `request.method`

HTTP 方法字符串（`'GET'`、`'POST'` 等）。

### `request.path`

URL 路径，不含查询字符串。

```python
# GET /search?q=hello
request.path    # '/search'
```

### `request.args`

查询字符串（MultiDict）。

```python
# GET /search?q=hello&page=2
request.args['q']                  # 'hello'
request.args.get('page', '1')     # '2'
request.args.getlist('tag')       # 多值
```

### `request.headers`

HTTP headers（大小写不敏感）。

### `request.cookies`

Cookies 字典。

### `request.json`

POST/PUT 的 JSON body。如果 Content-Type 是 JSON，自动解析；否则返回 `None`。

```python
# body: {"name":"alice"}
request.json    # {'name': 'alice'}
```

### `request.form`

URL-encoded 表单（`Content-Type: application/x-www-form-urlencoded`）。

### `request.body`

原始 body（bytes）。

### `request.client_addr`

客户端地址 `('ip', port)`。

### `request.g`

请求级共享容器。在 before_request 里塞数据：

```python
@app.before_request
async def auth(request):
    request.g.user = decode(request.headers.get('Authorization'))

@app.get('/me')
async def me(request):
    return request.g.user
```

### `request.content_length` / `request.content_type`

请求 body 信息。

## 限制

| 属性 | 默认值 | 说明 |
|------|--------|------|
| `max_content_length` | 16 KB | body 超过返回 413 |
| `max_body_length` | 16 KB | body 读上限 |
| `max_readline` | 2 KB | header 行最大长度 |

## 下一步

- [Request 对象指南](/guide/request-object)：详细使用
- [NovaServer](/api/nova-server)
- [Response](/api/response)