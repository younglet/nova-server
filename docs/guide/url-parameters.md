# URL 参数

URL 里有一部分可以变成变量。比如 `/user/42` 里的 `42` 就是用户 ID。

## 基本用法

```python
from nova_server import NovaServer

app = NovaServer()

@app.get('/hello/<name>')
async def hello(request, name):
    return 'Hello, {}!'.format(name)

app.run(port=80)
```

`<name>` 是占位符。访问 `/hello/World`，框架把 `World` 传给 `name` 参数。

| 访问 | `name` 的值 |
|------|-----------|
| `/hello/World` | `'World'` |
| `/hello/小明` | `'小明'` |
| `/hello/a/b` | 404（不能含 `/`） |

## 多个参数

```python
@app.get('/user/<int:id>/post/<int:pid>')
async def user_post(request, id, pid):
    return 'user {} post {}'.format(id, pid)
```

访问 `/user/1/post/99` → `'user 1 post 99'`。

参数按 URL 出现顺序传给函数。

## 类型转换

`<name>` 默认是字符串。要自动转 int：

```python
@app.get('/user/<int:id>')
async def user(request, id):
    # id 现在是 int，不是 str
    return {'id': id, 'type': type(id).__name__}
```

| 语法 | 类型 | 示例 |
|------|------|------|
| `<name>` | str | `/foo/bar` → `name='bar'` |
| `<int:id>` | int | `/user/42` → `id=42` |
| `<path:rest>` | str（允许 `/`） | `/files/a/b.txt` → `rest='a/b.txt'` |

`<int:id>` 匹配不上时返回 404：

```
/user/42    → ✅ id=42
/user/abc   → ❌ 404
```

## 真实例子：用户管理

```python
from nova_server import NovaServer, abort

app = NovaServer()

# 模拟数据库
USERS = {
    1: {'name': 'Alice', 'age': 30},
    2: {'name': 'Bob', 'age': 25},
}

@app.get('/users')
async def list_users(request):
    """列出所有用户。"""
    return {'users': list(USERS.values())}

@app.get('/users/<int:id>')
async def get_user(request, id):
    """取单个用户。"""
    if id not in USERS:
        abort(404, 'user {} not found'.format(id))
    return USERS[id]

@app.post('/users/<int:id>')
async def update_user(request, id):
    """更新用户（用 POST 简化示例）。"""
    if id not in USERS:
        abort(404)
    USERS[id].update(request.json)  # JSON body 内容合并进去
    return USERS[id]

app.run(port=80)
```

测试：

## `<path:>` 含 `/` 的路径

如果要匹配含 `/` 的路径（比如文件名带斜杠），用 `<path:>`：

```python
@app.get('/files/<path:filename>')
async def serve_file(request, filename):
    # /files/css/style.css → filename='css/style.css'
    return 'serve ' + filename
```

### ⚠️ 路径穿越风险

`<path:>` **不**拦截 `../`，攻击者可以这样请求：

```
/files/../etc/passwd
```

**必须自己验证**：

```python
@app.get('/files/<path:filename>')
async def serve_file(request, filename):
    if '..' in filename.split('/'):
        return {'error': 'forbidden'}, 403
    return send_file('/static/' + filename)
```

完整示例看 [静态文件服务](/guide/static-files)。

## 自定义类型

可以注册自己的类型，比如 hex 颜色：

```python
from nova_server import URLPattern

URLPattern.register_type('hex', '[0-9a-fA-F]+')

@app.get('/color/<hex:c>')
async def color(request, c):
    return {'color': '#' + c.upper()}
```

| 访问 | 结果 |
|------|------|
| `/color/ff8800` | `{"color": "#FF8800"}` |
| `/color/zzz` | 404 |

还可以加 parser 自动转值：

```python
URLPattern.register_type(
    'hex',
    '[0-9a-fA-F]+',
    parser=lambda v: int(v, 16),  # 转 int
)
```

这样 `c` 直接就是 int。

## 小结

| 需求 | 写法 |
|------|------|
| 字符串参数 | `<name>` |
| 整数参数 | `<int:id>` |
| 含 `/` 的路径 | `<path:rest>` |
| 自定义类型 | `URLPattern.register_type(...)` |

## 下一步

- [查询字符串](/guide/query-strings) — 读 `?key=value`
- [返回 JSON](/guide/return-json)
- [POST 请求](/guide/post-requests)