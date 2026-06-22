# 查询字符串

URL 里 `?` 后面的部分叫**查询字符串**，比如 `/search?q=hello&page=2`。

## 最简例子

```python
from nova_server import NovaServer

app = NovaServer()

@app.get('/search')
async def search(request):
    q = request.args['q']                   # 'hello'
    page = request.args.get('page', '1')    # '2'，默认 '1'
    return {'q': q, 'page': page}

app.run(port=80)
```

`request.args` 类似 Python 字典。

## 怎么取值

```python
request.args['key']                  # 没有这个 key 会报错
request.args.get('key')              # 没有返回 None
request.args.get('key', '默认值')    # 没有返回默认值
```

**注意：值都是字符串**。要数字自己转：

```python
page = int(request.args.get('page', '1'))
```

## 多值

如果 URL 里有 `?tag=red&tag=blue&tag=green`：

```python
tags = request.args.getlist('tag')
# → ['red', 'blue', 'green']
```

## URL 编码

URL 里有中文或特殊字符要编码：

| 字符 | 编码 |
|------|------|
| 空格 | `%20` 或 `+` |
| 中文 | `%E4%B8%AD` 之类 |
| `&` | `%26` |
| `?` | `%3F` |

框架**自动解码**：

```python
# /search?q=hello%20world&name=%E5%B0%8F%E6%98%8E
q = request.args['q']       # 'hello world'
name = request.args['name'] # '小明'
```

## 例子：分页

```python
@app.get('/api/items')
async def list_items(request):
    page = int(request.args.get('page', '1'))
    size = int(request.args.get('size', '20'))

    # 模拟数据
    all_items = [{'id': i, 'name': 'item {}'.format(i)} for i in range(100)]

    # 取这一页
    start = (page - 1) * size
    end = start + size

    return {
        'page': page,
        'size': size,
        'total': len(all_items),
        'items': all_items[start:end],
    }
```

测试：

## URL 参数 vs 查询字符串

| | URL 参数 | 查询字符串 |
|--|---------|----------|
| 位置 | URL 路径里 | URL `?` 后面 |
| 例子 | `/user/42` | `/search?q=hello` |
| 必填 | 是 | 否（可选） |
| 用途 | 资源 ID | 过滤条件、分页 |

```python
# URL 参数（必填）
@app.get('/user/<int:id>')
async def user(request, id):
    return {'id': id}

# 查询字符串（可选）
@app.get('/api/items')
async def items(request):
    tags = request.args.getlist('tag')
    return {'tags': tags}
```

## 小结

| 需求 | 写法 |
|------|------|
| 必填的路径段 | 用 URL 参数 `<int:id>` |
| 可选的过滤/搜索 | 用查询字符串 `request.args.get(...)` |
| 多值 | `request.args.getlist(...)` |

## 下一步

- [返回 JSON](/guide/return-json)
- [POST 请求](/guide/post-requests)
- [Request 对象](/guide/request-object)