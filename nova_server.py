# NOTE: MicroPython 没有 __future__ 模块，所以这行已移除（CPython 注释风格的类型注解仍能正常工作）。

import asyncio
import io
import re
import time

try:
    import orjson as json
except ImportError:
    import json

# print_exception 跨平台兼容：
# - MicroPython: 内置 sys.print_exception(exc)
# - CPython: 回退到 traceback.print_exception(type, value, tb)
try:
    from sys import print_exception
except ImportError:
    import traceback as _traceback
    def print_exception(exc):
        _traceback.print_exception(type(exc), exc, exc.__traceback__)

try:
    # CPython: 完整功能集
    from inspect import iscoroutinefunction, iscoroutine
    from functools import partial

    async def invoke_handler(handler, *args, **kwargs):
        if iscoroutinefunction(handler):
            ret = await handler(*args, **kwargs)
        else:
            ret = await asyncio.get_running_loop().run_in_executor(
                None, partial(handler, *args, **kwargs))
        return ret
except ImportError:
    # MicroPython: 最小兼容
    def iscoroutine(coro):
        return hasattr(coro, 'send') and hasattr(coro, 'throw')

    async def invoke_handler(handler, *args, **kwargs):
        ret = handler(*args, **kwargs)
        if iscoroutine(ret):
            ret = await ret
        return ret


def _detect_lan_ip():
    """探测本机的局域网 IP，仅用于启动时打印，不影响绑定逻辑。

    优先 MicroPython 风格（network.WLAN），其次 CPython UDP 探测戏法。
    探测不到返回 None，启动打印会回退到 host（通常 0.0.0.0）。
    """
    # 1) MicroPython / ESP32 已连 WiFi 时
    try:
        import network  # noqa: F401
        wlan = network.WLAN(network.STA_IF)  # noqa: F821
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            if ip and ip != '0.0.0.0':
                return ip
    except Exception:
        pass

    # 2) CPython UDP 探测：不发包，仅让内核选路由后获取本地 socket 名
    try:
        import socket as _socket
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            if ip and ip != '0.0.0.0':
                return ip
        finally:
            s.close()
    except Exception:
        pass

    return None


# ★ MicroPython 时间格式化兼容层
# ★ time.strftime 在 MicroPython 里不存在（完全未实现）
#   替代方案：手动 format time.localtime() 返回的 tuple
#   tuple 格式：(year, month, mday, hour, minute, second, weekday, yearday)
_WDAY_ABBR = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
_MONTH_ABBR = ('', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def _format_hms(t=None):
    """格式化 HH:MM:SS。MicroPython + CPython 都能用。"""
    if t is None:
        t = time.localtime()
    return '{:02d}:{:02d}:{:02d}'.format(t[3], t[4], t[5])


def _format_http_date(t):
    """格式化 RFC 1123 / RFC 7231 HTTP-date：
       'Sun, 06 Nov 1994 08:49:37 GMT'
    （用 GMT 而非 +0000 是 HTTP/1.1 要求的格式）
    """
    return '{wday}, {d:02d} {mon} {y:04d} {h:02d}:{m:02d}:{s:02d} GMT'.format(
        wday=_WDAY_ABBR[t[6]], d=t[2], mon=_MONTH_ABBR[t[1]],
        y=t[0], h=t[3], m=t[4], s=t[5])

MUTED_SOCKET_ERRORS = [
    32,    # Broken pipe (UNIX)
    54,    # Connection reset by peer (UNIX)
    104,   # Connection reset by peer (Linux)
    128,   # Network dropped connection (Linux)
    10053, # Software caused connection abort (Windows)
    10054, # Connection reset by peer (Windows)
]


def urldecode(s):
    if isinstance(s, str):
        s = s.encode()
    s = s.replace(b'+', b' ')
    parts = s.split(b'%')
    if len(parts) == 1:
        return s.decode()
    result = [parts[0]]
    for item in parts[1:]:
        if item == b'':
            result.append(b'%')
        else:
            code = item[:2]
            result.append(bytes([int(code, 16)]))
            result.append(item[2:])
    return b''.join(result).decode()


def urlencode(s):
    return s.replace('+', '%2B').replace(' ', '+').replace(
        '%', '%25').replace('?', '%3F').replace('#', '%23').replace(
            '&', '%26').replace('=', '%3D')


def _is_safe_path(path):
    """防路径穿越攻击（../）。

    静态文件路由内部使用，外部不应直接调用。
    """
    if not path or path.startswith('/'):
        return False
    if '..' in path.split('/'):
        return False
    return True


class NoCaseDict(dict):
    def __init__(self, initial_dict=None):
        super().__init__(initial_dict or {})
        self.keymap = {k.lower(): k for k in self.keys() if k.lower() != k}

    def __setitem__(self, key, value):
        kl = key.lower()
        key = self.keymap.get(kl, key)
        if kl != key:
            self.keymap[kl] = key
        super().__setitem__(key, value)

    def __getitem__(self, key):
        kl = key.lower()
        return super().__getitem__(self.keymap.get(kl, kl))

    def __delitem__(self, key):
        kl = key.lower()
        super().__delitem__(self.keymap.get(kl, kl))

    def __contains__(self, key):
        kl = key.lower()
        return self.keymap.get(kl, kl) in self.keys()

    def get(self, key, default=None):
        kl = key.lower()
        return super().get(self.keymap.get(kl, kl), default)

    def update(self, other_dict):
        for key, value in other_dict.items():
            self[key] = value


def mro(cls):
    """
    获取类的 MRO（Method Resolution Order）。
    MicroPython 1.17+ 和 CPython 都支持 cls.__mro__。
    返回列表，兼容旧版 MicroPython。
    """
    return cls.__mro__ if hasattr(cls, '__mro__') else [cls]


class MultiDict(dict):
    def __init__(self, initial_dict=None):
        super().__init__()
        if initial_dict:
            for key, value in initial_dict.items():
                self[key] = value

    def __setitem__(self, key, value):
        if key not in self:
            super().__setitem__(key, [])
        super().__getitem__(key).append(value)

    def __getitem__(self, key):
        return super().__getitem__(key)[0]

    def get(self, key, default=None, type=None):
        if key not in self:
            return default
        value = self[key]
        if type is not None:
            value = type(value)
        return value

    def getlist(self, key, type=None):
        if key not in self:
            return []
        values = super().__getitem__(key)
        if type is not None:
            values = [type(value) for value in values]
        return values


class AsyncBytesIO:
    def __init__(self, data):
        self.stream = io.BytesIO(data)

    async def read(self, n=-1):
        return self.stream.read(n)

    async def readline(self):  
        return self.stream.readline()

    async def readexactly(self, n):  
        return self.stream.read(n)

    async def readuntil(self, separator=b'\n'):  
        return self.stream.readuntil(separator=separator)

    async def awrite(self, data):  
        return self.stream.write(data)

    async def aclose(self):  
        pass


class Request:
    """HTTP 请求对象。自动解析 URL、查询参数、headers、cookies、JSON body、表单。"""
    max_content_length = 16 * 1024
    max_body_length = 16 * 1024
    max_readline = 2 * 1024

    class G:
        """请求级全局对象容器，可在 before_request 中注入共享数据。"""
        pass

    def __init__(self, app, client_addr, method, url, http_version, headers,
                 body=None, stream=None, sock=None, url_prefix='',
                 subapp=None):
        self.app = app
        self.client_addr = client_addr
        self.method = method
        self.url = url
        self.url_prefix = url_prefix
        self.subapp = subapp
        self.path = url
        self.query_string = None
        self.args = {}
        self.headers = headers
        self.cookies = {}
        self.content_length = 0
        self.content_type = None
        self.g = Request.G()

        self.http_version = http_version
        if '?' in self.path:
            self.path, self.query_string = self.path.split('?', 1)
            self.args = self._parse_urlencoded(self.query_string)

        if 'Content-Length' in self.headers:
            self.content_length = int(self.headers['Content-Length'])
        if 'Content-Type' in self.headers:
            self.content_type = self.headers['Content-Type']
        if 'Cookie' in self.headers:
            for cookie in self.headers['Cookie'].split(';'):
                c = cookie.strip().split('=', 1)
                self.cookies[c[0]] = c[1] if len(c) > 1 else ''

        self._body = body
        self.body_used = False
        self._stream = stream
        self.sock = sock
        self._json = None
        self._form = None
        self._files = None
        self.after_request_handlers = []

    @staticmethod
    async def create(app, client_reader, client_writer, client_addr):
        
        line = (await Request._safe_readline(client_reader)).strip().decode()
        if not line:  
            return None
        method, url, http_version = line.split()
        http_version = http_version.split('/', 1)[1]

        
        headers = NoCaseDict()
        content_length = 0
        while True:
            line = (await Request._safe_readline(
                client_reader)).strip().decode()
            if line == '':
                break
            header, value = line.split(':', 1)
            value = value.strip()
            headers[header] = value
            if header.lower() == 'content-length':
                content_length = int(value)

        
        body = b''
        if content_length and content_length <= Request.max_body_length:
            body = await client_reader.readexactly(content_length)
            stream = None
        else:
            body = b''
            stream = client_reader

        return Request(app, client_addr, method, url, http_version, headers,
                       body=body, stream=stream,
                       sock=(client_reader, client_writer))

    def _parse_urlencoded(self, urlencoded):
        data = MultiDict()
        if len(urlencoded) > 0:  
            if isinstance(urlencoded, str):
                for kv in [pair.split('=', 1)
                           for pair in urlencoded.split('&') if pair]:
                    data[urldecode(kv[0])] = urldecode(kv[1]) \
                        if len(kv) > 1 else ''
            elif isinstance(urlencoded, bytes):  
                for kv in [pair.split(b'=', 1)
                           for pair in urlencoded.split(b'&') if pair]:
                    data[urldecode(kv[0])] = urldecode(kv[1]) \
                        if len(kv) > 1 else b''
        return data

    @property
    def body(self):
        return self._body

    @property
    def stream(self):
        if self._stream is None:
            self._stream = AsyncBytesIO(self._body)
        return self._stream

    @property
    def json(self):
        if self._json is None:
            if self.content_type is None:
                return None
            mime_type = self.content_type.split(';')[0]
            if mime_type != 'application/json':
                return None
            self._json = json.loads(self.body.decode())
        return self._json

    @property
    def form(self):
        if self._form is None:
            if self.content_type is None:
                return None
            mime_type = self.content_type.split(';')[0]
            if mime_type != 'application/x-www-form-urlencoded':
                return None
            self._form = self._parse_urlencoded(self.body)
        return self._form

    @property
    def files(self):
        return self._files

    def after_request(self, f):
        self.after_request_handlers.append(f)
        return f

    @staticmethod
    async def _safe_readline(stream):
        line = (await stream.readline())
        if len(line) > Request.max_readline:
            raise ValueError('line too long')
        return line


class Response:
    """HTTP 响应对象。支持字符串/bytes/异步生成器/file 对象作为 body。
    构造时自动判断类型：dict/list 转为 JSON，str 转为 UTF-8 bytes。"""
    types_map = {
        'css': 'text/css',
        'gif': 'image/gif',
        'html': 'text/html',
        'jpg': 'image/jpeg',
        'js': 'application/javascript',
        'json': 'application/json',
        'png': 'image/png',
        'txt': 'text/plain',
        'svg': 'image/svg+xml',
    }

    send_file_buffer_size = 1024

    
    
    default_content_type = 'text/plain'

    
    
    default_send_file_max_age = None

    
    
    already_handled = None

    def __init__(self, body='', status_code=200, headers=None, reason=None):
        if body is None and status_code == 200:
            body = ''
            status_code = 204
        self.status_code = status_code
        self.headers = NoCaseDict(headers or {})
        self.reason = reason
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
            self.headers['Content-Type'] = 'application/json; charset=UTF-8'
        if isinstance(body, str):
            self.body = body.encode()
        else:
            
            self.body = body
        self.is_head = False

    def set_cookie(self, cookie, value, path=None, domain=None, expires=None,
                   max_age=None, secure=False, http_only=False,
                   partitioned=False):
        http_cookie = '{cookie}={value}'.format(cookie=cookie, value=value)
        if path:
            http_cookie += '; Path=' + path
        if domain:
            http_cookie += '; Domain=' + domain
        if expires:
            if isinstance(expires, str):
                http_cookie += '; Expires=' + expires
            else:
                # ★ MicroPython 无 time.strftime，用 _format_http_date 手动 format
                http_cookie += '; Expires=' + _format_http_date(expires.timetuple())
        if max_age is not None:
            http_cookie += '; Max-Age=' + str(max_age)
        if secure:
            http_cookie += '; Secure'
        if http_only:
            http_cookie += '; HttpOnly'
        if partitioned:
            http_cookie += '; Partitioned'
        if 'Set-Cookie' in self.headers:
            self.headers['Set-Cookie'].append(http_cookie)
        else:
            self.headers['Set-Cookie'] = [http_cookie]

    def delete_cookie(self, cookie, **kwargs):
        kwargs.pop('expires', None)
        kwargs.pop('max_age', None)
        self.set_cookie(cookie, '', expires='Thu, 01 Jan 1970 00:00:01 GMT',
                        max_age=0, **kwargs)

    def complete(self):
        if isinstance(self.body, bytes) and \
                'Content-Length' not in self.headers:
            self.headers['Content-Length'] = str(len(self.body))
        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = self.default_content_type
            if 'charset=' not in self.headers['Content-Type']:
                self.headers['Content-Type'] += '; charset=UTF-8'

    def _build_head(self):
        """把状态行 + headers + 空行合成一个 bytes，单次发送。

        优化点（ESP32 上重要）：
          · 避免每行 header 都 str.format().encode() + awrite
          · 一次 awrite 取代多次 syscalls，WiFi 下能省每行 1-5ms
        """
        reason = self.reason if self.reason is not None else \
            ('OK' if self.status_code == 200 else 'N/A')
        parts = ['HTTP/1.0 {code} {reason}\r\n'.format(
            code=self.status_code, reason=reason).encode()]
        for header, value in self.headers.items():
            values = value if isinstance(value, list) else [value]
            for v in values:
                parts.append('{h}: {v}\r\n'.format(
                    h=header, v=v).encode())
        parts.append(b'\r\n')
        return b''.join(parts)

    async def write(self, stream):
        self.complete()

        try:
            head = self._build_head()
            body = self.body

            # ★ 快路径（最常见）：手头已有 bytes/str body
            #   直接一次 awrite 拼 head + body。microPython StreamWriter.drain()
            #   会等发送缓冲区空，所以不用我们自己手动 chunk + 反压控制。
            fast = (
                not self.is_head
                and isinstance(body, (bytes, bytearray))
                and not hasattr(body, '__anext__')   # 不是 async gen
                and not hasattr(body, 'read')         # 不是 file-like
                and not hasattr(body, '__next__')      # 不是 sync gen
            )
            if fast:
                total = len(head) + len(body)
                if total <= 16 * 1024:   # ≤16KB → 一次 send
                    await stream.awrite(head + body)
                else:
                    # 大块但仍是内存里的字节 → 分两次，避免 VFS 紧张
                    await stream.awrite(head)
                    await stream.awrite(body)
            else:
                await stream.awrite(head)
                if not self.is_head:
                    # 慢路径：file / generator / async iter，保持原 chunked 逻辑
                    iter_obj = self.body_iter()
                    async for chunk in iter_obj:
                        if isinstance(chunk, str):
                            chunk = chunk.encode()
                        try:
                            await stream.awrite(chunk)
                        except OSError as exc:
                            if exc.errno in MUTED_SOCKET_ERRORS or \
                                    exc.args[0] == 'Connection lost':
                                if hasattr(iter_obj, 'aclose'):
                                    await iter_obj.aclose()
                            raise
                    if hasattr(iter_obj, 'aclose'):
                        await iter_obj.aclose()

        except OSError as exc:  
            if exc.errno in MUTED_SOCKET_ERRORS or \
                    exc.args[0] == 'Connection lost':
                pass
            else:
                raise

    def body_iter(self):
        if hasattr(self.body, '__anext__'):
            
            return self.body

        response = self

        class iter:
            ITER_UNKNOWN = 0
            ITER_SYNC_GEN = 1
            ITER_FILE_OBJ = 2
            ITER_NO_BODY = -1

            def __aiter__(self):
                if response.body:
                    self.i = self.ITER_UNKNOWN  
                else:
                    self.i = self.ITER_NO_BODY
                return self

            async def __anext__(self):
                if self.i == self.ITER_NO_BODY:
                    await self.aclose()
                    raise StopAsyncIteration
                if self.i == self.ITER_UNKNOWN:
                    if hasattr(response.body, 'read'):
                        self.i = self.ITER_FILE_OBJ
                    elif hasattr(response.body, '__next__'):
                        self.i = self.ITER_SYNC_GEN
                        return next(response.body)
                    else:
                        self.i = self.ITER_NO_BODY
                        return response.body
                elif self.i == self.ITER_SYNC_GEN:
                    try:
                        return next(response.body)
                    except StopIteration:
                        await self.aclose()
                        raise StopAsyncIteration
                buf = response.body.read(response.send_file_buffer_size)
                if iscoroutine(buf):  
                    buf = await buf
                if len(buf) < response.send_file_buffer_size:
                    self.i = self.ITER_NO_BODY
                return buf

            async def aclose(self):
                if hasattr(response.body, 'close'):
                    result = response.body.close()
                    if iscoroutine(result):  
                        await result

        return iter()

    @classmethod
    def redirect(cls, location, status_code=302):
        if '\x0d' in location or '\x0a' in location:
            raise ValueError('invalid redirect URL')
        return cls(status_code=status_code, headers={'Location': location})

    @classmethod
    def send_file(cls, filename, status_code=200, content_type=None,
                  stream=None, max_age=None, compressed=False,
                  file_extension=''):
        if content_type is None:
            if compressed and filename.endswith('.gz'):
                ext = filename[:-3].split('.')[-1]
            else:
                ext = filename.split('.')[-1]
            if ext in Response.types_map:
                content_type = Response.types_map[ext]
            else:
                content_type = 'application/octet-stream'
        headers = {'Content-Type': content_type}

        if max_age is None:
            max_age = cls.default_send_file_max_age
        if max_age is not None:
            headers['Cache-Control'] = 'max-age={}'.format(max_age)

        if compressed:
            headers['Content-Encoding'] = compressed \
                if isinstance(compressed, str) else 'gzip'

        f = stream or open(filename + file_extension, 'rb')
        return cls(body=f, status_code=status_code, headers=headers)


class URLPattern():
    """URL 模式匹配器。支持 <name>, <int:name>, <path:name>, <re:...> 语法。"""
    segment_patterns = {
        'string': '/([^/]+)',
        'int': '/(-?\\d+)',
        'path': '/(.+)',
    }
    segment_parsers = {
        'int': lambda value: int(value),
    }

    @classmethod
    def register_type(cls, type_name, pattern='[^/]+', parser=None):
        cls.segment_patterns[type_name] = '/({})'.format(pattern)
        cls.segment_parsers[type_name] = parser

    def __init__(self, url_pattern):
        self.url_pattern = url_pattern
        self.segments = []
        self.regex = None

    def compile(self):
        pattern = ''
        for segment in self.url_pattern.lstrip('/').split('/'):
            if segment and segment[0] == '<':
                if segment[-1] != '>':
                    raise ValueError('invalid URL pattern')
                segment = segment[1:-1]
                if ':' in segment:
                    type_, name = segment.rsplit(':', 1)
                else:
                    type_ = 'string'
                    name = segment
                parser = None
                if type_.startswith('re:'):
                    pattern += '/({pattern})'.format(pattern=type_[3:])
                else:
                    if type_ not in self.segment_patterns:
                        raise ValueError('invalid URL segment type')
                    pattern += self.segment_patterns[type_]
                    parser = self.segment_parsers.get(type_)
                self.segments.append({'parser': parser, 'name': name,
                                      'type': type_})
            else:
                pattern += '/' + segment
                self.segments.append({'parser': None})
        self.regex = re.compile('^' + pattern + '$')
        return self.regex

    def match(self, path):
        args = {}
        g = (self.regex or self.compile()).match(path)
        if not g:
            return
        i = 1
        for segment in self.segments:
            if 'name' not in segment:
                continue
            arg = g.group(i)
            if segment['parser']:
                arg = self.segment_parsers[segment['type']](arg)
                if arg is None:
                    return
            args[segment['name']] = arg
            i += 1
        return args

    def __repr__(self):  
        return 'URLPattern: {}'.format(self.url_pattern)


class HTTPException(Exception):
    """可中断请求处理流程并返回指定 HTTP 状态码的异常。
    配合 abort() 使用，会被 dispatch_request 捕获并转为错误响应。"""
    def __init__(self, status_code, reason=None):
        self.status_code = status_code
        self.reason = reason or str(status_code) + ' error'

    def __repr__(self):  
        return 'HTTPException: {}'.format(self.status_code)


class NovaServer:
    """NovaServer - 面向 ESP32+MicroPython 的异步微型 Web 框架"""
    def __init__(self, static_dir=None, static_path='/static',
                 debug=False, auto_gc=True, gc_threshold_kb=10,
                 host='0.0.0.0', port=80):
        """
        参数：
          host:              默认监听地址（默认 '0.0.0.0'）。
                            传给 run() / start_server() 时如不显式指定则使用此值。
          port:              默认监听端口（默认 80，对应 HTTP 标准端口）。
                            传给 run() / start_server() 时如不显式指定则使用此值。
          static_dir:       静态文件目录（如 '/www'、'/static'）。
                            传 None 禁用内置静态服务（默认 None）。
                            启用后自动注册：
                              GET {static_path}/             → index.html
                              GET {static_path}/<path:file>  → 文件（含路径穿越防护）
          static_path:      静态文件 URL 前缀（默认 '/static'）。
                            仅在 static_dir 不为 None 时生效。
          debug:            是否启用调试模式（默认 False）：
                              · 在 start_server 前打印 'Starting async server on ...'
                              · 每个请求完成后打印一行访问日志：
                                [14:30:21] GET /api/sensors 200 (12ms)
          auto_gc:          是否在请求处理前后自动回收内存（默认 True）
          gc_threshold_kb:   剩余 heap 低于此值时触发回收（默认 10 KB）
                            设为 0 禁用；只在 MicroPython 上有效（PC 上自动跳过）
        """
        self.url_map = []
        self.before_request_handlers = []
        self.after_request_handlers = []
        self.after_error_request_handlers = []
        self.error_handlers = {}
        self.options_handler = self.default_options_handler
        self.debug = bool(debug)
        self.server = None
        self.auto_gc = auto_gc
        self.gc_threshold = gc_threshold_kb * 1024
        self.static_dir = static_dir
        self.static_path = static_path
        self.host = host
        self.port = port
        if static_dir:
            self._mount_static(static_dir, static_path)

    def _mount_static(self, directory, url_prefix):
        """自动注册静态文件路由。

        注册：
          GET {url_prefix}/            → {directory}/index.html
          GET {url_prefix}/<path:file> → {directory}/{file}（含 _is_safe_path 防护 + OSError → 404）

        用户无需手写 _is_safe_path / send_file / OSError 处理。
        """
        static_root = directory.rstrip('/') + '/'
        url_prefix = url_prefix.rstrip('/')

        async def _serve_index(req):
            try:
                return send_file(static_root + 'index.html', max_age=3600)
            except OSError:
                return {'error': 'index.html not found'}, 404

        async def _serve_file(req, filename):
            if not _is_safe_path(filename):
                return {'error': 'forbidden'}, 403
            try:
                return send_file(static_root + filename, max_age=3600)
            except OSError:
                return {'error': 'not found'}, 404

        self.url_map.append(
            (['GET'], URLPattern(url_prefix + '/<path:filename>'),
             _serve_file, '', None))
        self.url_map.append(
            (['GET'], URLPattern(url_prefix + '/'),
             _serve_index, '', None))

    def _maybe_gc(self):
        """在请求前后自动调用，剩余 heap 不足时回收。
        PC 上 gc.mem_free() 不存在，自动跳过。"""
        if not self.auto_gc or self.gc_threshold <= 0:
            return
        try:
            import gc
            if gc.mem_free() < self.gc_threshold:
                gc.collect()
        except (AttributeError, ImportError):
            pass

    def route(self, url_pattern, methods=None):
        def decorated(f):
            self.url_map.append(
                ([m.upper() for m in (methods or ['GET'])],
                 URLPattern(url_pattern), f, '', None))
            return f
        return decorated

    def get(self, url_pattern):return self.route(url_pattern, methods=['GET'])

    def post(self, url_pattern):return self.route(url_pattern, methods=['POST'])

    def put(self, url_pattern):return self.route(url_pattern, methods=['PUT'])

    def patch(self, url_pattern):return self.route(url_pattern, methods=['PATCH'])

    def delete(self, url_pattern):return self.route(url_pattern, methods=['DELETE'])

    def before_request(self, f):
        self.before_request_handlers.append(f)
        return f

    def after_request(self, f):
        self.after_request_handlers.append(f)
        return f

    def after_error_request(self, f):
        self.after_error_request_handlers.append(f)
        return f

    def errorhandler(self, status_code_or_exception_class):
        def decorated(f):
            self.error_handlers[status_code_or_exception_class] = f
            return f
        return decorated

    def mount(self, subapp, url_prefix='', local=False):
        for methods, pattern, handler, _prefix, _subapp in subapp.url_map:
            self.url_map.append(
                (methods, URLPattern(url_prefix + pattern.url_pattern),
                 handler, url_prefix + _prefix, _subapp or subapp))
        if not local:
            for handler in subapp.before_request_handlers:
                self.before_request_handlers.append(handler)
            subapp.before_request_handlers = []
            for handler in subapp.after_request_handlers:
                self.after_request_handlers.append(handler)
            subapp.after_request_handlers = []
            for handler in subapp.after_error_request_handlers:
                self.after_error_request_handlers.append(handler)
            subapp.after_error_request_handlers = []
            for status_code, handler in subapp.error_handlers.items():
                self.error_handlers[status_code] = handler
            subapp.error_handlers = {}

    @staticmethod
    def abort(status_code, reason=None):
        
        raise HTTPException(status_code, reason)

    async def start_server(self, host=None, port=None, debug=None,
                           ssl=None):
        """异步启动。
        host/port/debug 不传时回退到 __init__ 设置的 self.host/self.port/debug。
        ★ 关键：debug 默认是 None 也不是 False，以免覆盖 NovaServer(debug=...) 的设置。
        """
        if host is None:
            host = self.host
        if port is None:
            port = self.port
        if debug is not None:   # 只在显式传时才覆盖
            self.debug = bool(debug)

        async def serve(reader, writer):
            if not hasattr(writer, 'awrite'):  
                
                async def awrite(self, data):
                    self.write(data)
                    await self.drain()

                async def aclose(self):
                    self.close()
                    await self.wait_closed()

                from types import MethodType
                writer.awrite = MethodType(awrite, writer)
                writer.aclose = MethodType(aclose, writer)

            await self.handle_request(reader, writer)

        if self.debug:  
            print('Starting async server on {host}:{port}...'.format(
                host=host, port=port))

        try:
            self.server = await asyncio.start_server(serve, host, port,
                                                     ssl=ssl)
        except TypeError:  
            self.server = await asyncio.start_server(serve, host, port)

        # ★ 启动地址提示：server 起来后总打印，让用户立刻确认程序在线
        #   优先展示 LAN IP（ESP32 连 WiFi 后是 192.168.1.x），
        #   这样手机/电脑可以直接打开这个 URL，不需要反查设备 IP。
        #   注意：banner 用 self.debug 而不是本地参数 debug，反映真实生效的开关
        lan_ip = _detect_lan_ip()
        if lan_ip and lan_ip != host:
            print('NovaServer running on http://{lan_ip}:{port}/ (debug={debug})'.format(
                lan_ip=lan_ip, port=port, debug=self.debug))
            print('  (listening on {host}:{port}, reachable from LAN at {lan_ip}:{port})'.format(
                host=host, port=port, lan_ip=lan_ip))
        else:
            print('NovaServer running on http://{host}:{port}/ (debug={debug})'.format(
                host=host, port=port, debug=self.debug))

        while True:
            try:
                if hasattr(self.server, 'serve_forever'):  
                    try:
                        await self.server.serve_forever()
                    except asyncio.CancelledError:
                        pass
                await self.server.wait_closed()
                break
            except AttributeError:  
                
                
                await asyncio.sleep(0.1)

    def run(self, host=None, port=None, debug=None, ssl=None):
        """同步入口。参数不传时使用 __init__ 设置的 self.host / self.port / self.debug。

        debug=None（默认）→ 用 NovaServer(debug=...) 的设置；
                True    → 明确打开请求日志；
                False   → 明确关闭请求日志。
        """
        asyncio.run(self.start_server(host=host, port=port, debug=debug,
                                      ssl=ssl))

    def shutdown(self):
        self.server.close()

    def find_route(self, req):
        method = req.method.upper()
        if method == 'OPTIONS' and self.options_handler:
            return self.options_handler(req), '', None
        if method == 'HEAD':
            method = 'GET'
        f = 404
        p = ''
        s = None
        for route_methods, route_pattern, route_handler, url_prefix, subapp \
                in self.url_map:
            req.url_args = route_pattern.match(req.path)
            if req.url_args is not None:
                p = url_prefix
                s = subapp
                if method in route_methods:
                    f = route_handler
                    break
                else:
                    f = 405
        return f, p, s

    def default_options_handler(self, req):
        allow = []
        for route_methods, route_pattern, _, _, _ in self.url_map:
            if route_pattern.match(req.path) is not None:
                allow.extend(route_methods)
        if 'GET' in allow:
            allow.append('HEAD')
        allow.append('OPTIONS')
        return {'Allow': ', '.join(allow)}

    async def handle_request(self, reader, writer):
        # ★ 请求处理完后自动回收（释放临时变量）
        self._maybe_gc()
        start_time = time.time()
        req = None
        try:
            req = await Request.create(self, reader, writer,
                                       writer.get_extra_info('peername'))
        except OSError as exc:
            if exc.errno in MUTED_SOCKET_ERRORS:
                pass
            else:
                raise
        except Exception as exc:
            print_exception(exc)

        res = await self.dispatch_request(req)
        try:
            if res != Response.already_handled:
                await res.write(writer)
            await writer.aclose()
        except OSError as exc:
            if exc.errno in MUTED_SOCKET_ERRORS:
                pass
            else:
                raise
        if req and self.debug:
            try:
                # ★ MicroPython 无 time.strftime，用 _format_hms 手动 format
                elapsed_ms = int((time.time() - start_time) * 1000)
                ts = _format_hms()
                print('[{}] {} {} {} ({}ms)'.format(
                    ts, req.method, req.path,
                    res.status_code, elapsed_ms))
            except Exception as exc:
                # 别静默吞掉：MicroPython 不兼容时打印出来方便调试
                print('[nova-server debug log error]', exc)

    def get_request_handlers(self, req, attr, local_first=True):
        handlers = getattr(self, attr + '_handlers')
        local_handlers = getattr(req.subapp, attr + '_handlers') \
            if req and req.subapp else []
        return local_handlers + handlers if local_first \
            else handlers + local_handlers

    async def error_response(self, req, status_code, reason=None):
        if req and req.subapp and status_code in req.subapp.error_handlers:
            return await invoke_handler(
                req.subapp.error_handlers[status_code], req)
        elif status_code in self.error_handlers:
            return await invoke_handler(self.error_handlers[status_code], req)
        return reason or 'N/A', status_code

    @staticmethod
    def _normalize_response(res):
        """
        将 handler 返回值统一转为 Response 对象。
        支持多种返回格式：
          - Response 对象：直接返回
          - (body, status_code) 元组：自动包装
          - (body, status_code, headers) 元组
          - (body, headers) 元组：status_code 默认为 200
          - 整数：视为状态码，空 body
          - dict / list：作为 body 传给 Response，触发 JSON 自动序列化
          - 其他（str/bytes）：作为 body 传给 Response

        ★ 注意：之前 dict 被当作 headers 是错的（dict-as-headers 仅用于 OPTIONS
          处理器，那个分支由 dispatch_request 单独处理，这里不应再吃 dict）。
        """
        if isinstance(res, Response):
            return res
        if isinstance(res, int):
            return Response('', res)
        if isinstance(res, tuple):
            # 判断格式：(status,), (body, status), (body, status, headers) 或 (body, headers)
            if len(res) == 1 and isinstance(res[0], int):
                return Response('', res[0])
            if len(res) >= 2:
                if isinstance(res[0], int):
                    # (status, headers) 或 (status,)
                    return Response('', res[0], res[1] if len(res) > 1 else {})
                if isinstance(res[1], int):
                    # (body, status) 或 (body, status, headers)
                    return Response(res[0], res[1], res[2] if len(res) > 2 else {})
                # (body, headers)
                return Response(res[0], 200, res[1])
        # ★ 修复：dict/list 现在正确地作为 body 传入 → Response 会自动 JSON 序列化
        return Response(res)

    async def dispatch_request(self, req):
        # ★ 自动 GC：进请求前 heap 低则回收，避免中途 MemoryError
        self._maybe_gc()
        after_request_handled = False
        if req:
            if req.content_length > req.max_content_length:
                res = await self.error_response(req, 413, 'Payload too large')
            else:
                f, req.url_prefix, req.subapp = self.find_route(req)
                try:
                    res = None
                    if callable(f):
                        for handler in self.get_request_handlers(
                                req, 'before_request', False):
                            res = await invoke_handler(handler, req)
                            if res:
                                break
                        if res is None:
                            res = await invoke_handler(f, req, **req.url_args)
                        res = self._normalize_response(res)
                        for handler in self.get_request_handlers(
                                req, 'after_request', True):
                            res = await invoke_handler(
                                handler, req, res) or res
                        for handler in req.after_request_handlers:
                            res = await invoke_handler(
                                handler, req, res) or res
                        after_request_handled = True
                    elif isinstance(f, dict):
                        res = Response(headers=f)
                    else:
                        res = await self.error_response(req, f, 'Not found')
                except HTTPException as exc:
                    res = await self.error_response(req, exc.status_code,
                                                    exc.reason)
                except Exception as exc:
                    print_exception(exc)
                    handler = None
                    res = None
                    if req.subapp and exc.__class__ in \
                            req.subapp.error_handlers:
                        handler = req.subapp.error_handlers[exc.__class__]
                    elif exc.__class__ in self.error_handlers:
                        handler = self.error_handlers[exc.__class__]
                    else:
                        for c in mro(exc.__class__)[1:]:
                            if req.subapp and c in req.subapp.error_handlers:
                                handler = req.subapp.error_handlers[c]
                                break
                            elif c in self.error_handlers:
                                handler = self.error_handlers[c]
                                break
                    if handler:
                        try:
                            res = await invoke_handler(handler, req, exc)
                        except Exception as exc2:
                            print_exception(exc2)
                    if res is None:
                        res = await self.error_response(
                            req, 500, 'Internal server error')
        else:
            res = await self.error_response(req, 400, 'Bad request')
        res = self._normalize_response(res)
        if not after_request_handled:
            for handler in self.get_request_handlers(
                    req, 'after_error_request', True):
                res = await invoke_handler(
                    handler, req, res) or res
        res.is_head = (req and req.method == 'HEAD')
        return res

    def help(self):
        print("""
【NovaServer - ESP32+MicroPython 异步微型 Web 框架】
----------------------------------------------------
[使用]:
    from nova_server import NovaServer, send_file

    app = NovaServer()

    # 静态网页
    @app.get('/index')
    async def func(request):
        return send_file('index.html', max_age=3600)

    # 带参数的 GET 请求
    @app.get('/hello/<name>')
    async def func(request, name):
        return 'Hello, ' + name

    # 处理 POST 请求的 JSON 数据
    @app.post('/data')
    async def func(request):
        json_data = request.json
        return {'received': json_data}

    if __name__ == '__main__':
        app.run(port=80, debug=True)
""")

Response.already_handled = Response()

abort = NovaServer.abort
redirect = Response.redirect
send_file = Response.send_file


# ══════════════════════════════════════════════════════════════
# 单文件部署：版本 + 公开 API
# ══════════════════════════════════════════════════════════════

__version__ = '0.1.0'
__all__ = [
    'NovaServer',
    'Request',
    'Response',
    'HTTPException',
    'URLPattern',
    'abort',
    'redirect',
    'send_file',
    'NoCaseDict',  # 内部用，但作为公开 API 暴露
    'MultiDict',
    'AsyncBytesIO',
    'urldecode',
    'urlencode',
]

