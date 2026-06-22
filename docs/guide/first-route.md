# 第 1 步：你的第一个接口

写一个最简单的 nova-server 程序：访问 `/` 返回 `Hello, World!`。

## 完整代码

新建 `main.py`，写这些：

```python
from nova_server import NovaServer

app = NovaServer()

@app.get('/')
async def index(request):
    return 'Hello, World!'

app.run(port=80)
```

一共 7 行。

## 烧到 ESP32

注意 `nova_server` **不用单独装**，NovaMP 固件已经内置了。

## 测试

用电脑或手机的浏览器，访问 `http://你的ESP32的IP/`。

如果你不知道 IP，先在 REPL 里看：

或者

浏览器 / 会显示：

```
Hello, World!
```

---

下面解释每一行在做什么。**如果你只想跑通，可以跳过解释，直接看 [下一步](#下一步)**。

## 逐行解释

### 第 1 行：导入

```python
from nova_server import NovaServer
```

把 `NovaServer` 类从 `nova_server` 模块里拿出来用。

### 第 3 行：创建 app

```python
app = NovaServer()
```

`app` 是你的应用。所有路由（接口）都注册到它上面。

名字随便起，不一定叫 `app`：

```python
myapp = NovaServer()     # 也可以
server = NovaServer()    # 也可以
```

但 `app` 是惯例，所有文档都用这个名。

### 第 5-7 行：注册一个路由

```python
@app.get('/')
async def index(request):
    return 'Hello, World!'
```

这几行代码在告诉框架：**当有人访问 `/` 时，调用 `index` 函数，把结果返回给客户端**。

拆开看：

| 部分 | 含义 |
|------|------|
| `@app.get('/')` | 装饰器：监听 `GET /` 请求 |
| `async def` | 协程函数（**必须有 `async`**） |
| `index` | 函数名（随便起） |
| `(request)` | 框架自动传入的请求对象，包含客户端发的所有信息 |
| `return '...'` | 返回值就是给客户端的响应内容 |

### 第 9 行：启动 server

```python
app.run(port=80)
```

启动 HTTP 服务，监听 80 端口。**这一行会一直阻塞**，后面不会再执行。

80 是 HTTP 默认端口。访问 `http://IP/` 不用加端口；用其他端口要加 `:8000`。

## 常见错误

### ❌ 忘了写 `async`

```python
@app.get('/')              # ← 错误：函数不是 async
def index(request):
    return 'hello'
```

启动会报错。**必须是 `async def`**。

### ❌ 路径忘了加引号或斜杠

```python
@app.get(/)                # ← SyntaxError：缺引号
@app.get('foo')            # ← 不会报错但访问不到：路径必须以 / 开头
```

正确：`@app.get('/foo')`。

### ❌ 函数名打错

```python
@app.get('/')
async def hello(request):  # ← 函数名
    return 'hi'

# 但客户端访问 / 时框架找不到 hello 函数，会 500
```

要保证函数名跟装饰器对应（Python 用名字找函数）。

## 小结

| 概念 | 写法 |
|------|------|
| 创建应用 | `app = NovaServer()` |
| 注册 GET 路由 | `@app.get('/路径')` |
| 写处理函数 | `async def 名字(request):` |
| 返回响应 | `return '字符串'` 或 `return {...}` |
| 启动服务 | `app.run(port=80)` |

## 下一步

- [第 2 步：加更多接口](/guide/more-routes)
- [URL 参数](/guide/url-parameters)
- [返回 JSON](/guide/return-json)