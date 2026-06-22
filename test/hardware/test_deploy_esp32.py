"""
hardware/test_deploy_esp32.py — ESP32 硬件测试
==============================================

前置：
  1. ESP32 通过 USB 连接到电脑（驱动装好）
  2. MicroPython ≥ 1.17 固件已烧录
  3. ESP32 已连上 WiFi（手动在 REPL 里 connect 一次即可）
  4. mpremote 已安装：pip install mpremote

运行：
  python test/hardware/test_deploy_esp32.py [PORT]
  python test/hardware/test_deploy_esp32.py COM3
  # 不传 PORT → 自动从 mpremote devs 检测

★ 测试流程：
  1. 检测设备
  2. 备份原 /main.py 和 /lib/
  3. 部署 nova_server 到 /lib/nova_server/
  4. 部署 examples/01_hello_esp32.py 到 /main.py
  5. 重启 ESP32
  6. 等待 server 启动
  7. HTTP 测试所有端点
  8. 报告结果
  9. 恢复原 /main.py 和 /lib/
"""
import sys
import os
import subprocess
import time
import json
import urllib.request
import urllib.error
import socket
import shutil
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)


# ════════════════════════════════════════════════════════════════
# 设备检测
# ════════════════════════════════════════════════════════════════

def detect_port(arg_port=None):
    """检测 ESP32 串口。"""
    if arg_port:
        return arg_port
    try:
        result = subprocess.run(
            ['mpremote', 'devs'],
            capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            line = line.strip()
            if line and ('COM' in line or '/dev/' in line):
                parts = line.split()
                if parts:
                    return parts[0]
    except FileNotFoundError:
        pass
    return None


def mpremote_exec(port, code, timeout=10):
    """在 ESP32 上执行 Python 代码，返回 stdout。"""
    result = subprocess.run(
        ['mpremote', 'connect', port, 'exec', code],
        capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip(), result.stderr.strip()


def mpremote_cp(port, src, dst, timeout=15):
    """复制文件到 ESP32。"""
    result = subprocess.run(
        ['mpremote', 'connect', port, 'cp', src, dst],
        capture_output=True, text=True, timeout=timeout)
    return result.returncode == 0, result.stderr


def mpremote_reset(port, timeout=10):
    """软重启 ESP32。"""
    result = subprocess.run(
        ['mpremote', 'connect', port, 'reset'],
        capture_output=True, text=True, timeout=timeout)
    return result.returncode == 0


def wait_for_port(host, port, timeout=5):
    """等待 TCP 端口可连接。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            s = socket.socket()
            s.settimeout(0.5)
            s.connect((host, port))
            s.close()
            return True
        except OSError:
            time.sleep(0.2)
    return False


def http_get(host, port, path, timeout=3):
    """HTTP GET，不自动 follow redirect（保留原始 302 状态码）。"""
    url = 'http://{}:{}{}'.format(host, port, path)
    req = urllib.request.Request(url, method='GET')

    # 自定义 handler：阻止 urllib 自动 follow redirect
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None  # 返回 None 表示不 follow

    opener = urllib.request.build_opener(NoRedirect)
    try:
        resp = opener.open(req, timeout=timeout)
        return resp.status, resp.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')
    except Exception as e:
        return 0, str(e)


# ════════════════════════════════════════════════════════════════
# 备份 / 恢复
# ════════════════════════════════════════════════════════════════

def backup_device(port, backup_dir):
    """备份 ESP32 上的关键文件。"""
    os.makedirs(backup_dir, exist_ok=True)
    # 1. main.py / boot.py：先删除本地残留，避免 mpremote 拒绝覆盖
    for f in ['main.py', 'boot.py']:
        local = os.path.join(backup_dir, f)
        if os.path.exists(local):
            os.remove(local)
        try:
            subprocess.run(
                ['mpremote', 'connect', port, 'cp', ':' + f, local],
                capture_output=True, timeout=5)
        except Exception:
            pass
    # 2. lib / static：目录，递归
    for d in ['lib', 'static']:
        local = os.path.join(backup_dir, d)
        if os.path.exists(local):
            shutil.rmtree(local, ignore_errors=True)
        try:
            subprocess.run(
                ['mpremote', 'connect', port, 'cp', '-r', ':' + d, local],
                capture_output=True, timeout=5)
        except Exception:
            pass


def restore_device(port, backup_dir):
    """恢复 ESP32 上的文件。

    ★ 必须先删除设备上被测的 nova_server 文件，再 cp 回原文件。
    否则 nova_server/__pycache__ 等残留会留在 /lib/ 下。
    """
    # 1. 设备端：先删除被测试写入的文件
    cleanup_code = """
import os
def rmtree(path):
    try:
        for f in os.listdir(path):
            full = path + '/' + f
            try:
                if os.stat(full)[0] == 16384:
                    rmtree(full)
                else:
                    os.remove(full)
            except: pass
        os.rmdir(path)
    except: pass

# 删 nova_server（被测试写入的）
try: rmtree('/lib/nova_server')
except: pass
# 删被测试改写的 main.py
try: os.remove('/main.py')
except: pass
print('cleaned')
"""
    mpremote_exec(port, cleanup_code)
    time.sleep(0.3)

    # 2. 从备份拷回
    for f in ['main.py', 'boot.py']:
        src = os.path.join(backup_dir, f)
        if os.path.exists(src):
            ok_flag, err = mpremote_cp(port, src, ':' + f)
            if not ok_flag:
                print('  [WARN] restore {} failed: {}'.format(f, err))

    for d in ['lib', 'static']:
        src = os.path.join(backup_dir, d)
        if os.path.exists(src) and os.path.isdir(src):
            # 先 mkdir，再逐文件拷贝（mpremote cp -r 要目标目录存在）
            mpremote_exec(port, "import os; os.mkdir('/{}')".format(d))
            for fname in os.listdir(src):
                full = os.path.join(src, fname)
                if os.path.isfile(full):
                    mpremote_cp(port, full, ':{}/{}'.format(d, fname))


# ════════════════════════════════════════════════════════════════
# 部署 / 测试
# ════════════════════════════════════════════════════════════════

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def ok(msg): print('  {} {}'.format(Colors.GREEN + '[OK]' + Colors.END, msg))


def fail(msg): print('  {} {}'.format(Colors.RED + '[FAIL]' + Colors.END, msg))


def info(msg): print('  {} {}'.format(Colors.BLUE + '[INFO]' + Colors.END, msg))


def step(msg): print('\n{}▶ {}{}'.format(Colors.YELLOW, msg, Colors.END))


def deploy(port, app_name='01_hello_esp32'):
    """部署 nova_server + 测试应用到 ESP32。"""
    step('Deploying nova_server + {}...'.format(app_name))

    # 0. 清理本地 __pycache__（nova_server.py 现在是单文件，可能有 pyc 残留）
    import shutil
    for p in [os.path.join(ROOT, '__pycache__')]:
        if os.path.exists(p):
            shutil.rmtree(p, ignore_errors=True)

    # 1. 删旧文件（用 REPL exec，不依赖 shutil）
    # ★ 同时清理：旧版目录 /lib/nova_server/ 和新版单文件 /lib/nova_server.py
    code = """
import os
for f in ['/lib/nova_server', '/lib/nova_server.py']:
    try:
        if os.stat(f)[0] == 16384:
            for root, dirs, files in os.walk(f):
                for x in files:
                    try: os.remove(root + '/' + x)
                    except: pass
                for x in dirs:
                    try: os.rmdir(root + '/' + x)
                    except: pass
            try: os.rmdir(f)
            except: pass
        else:
            os.remove(f)
    except: pass
try: os.remove('/main.py')
except: pass
print('cleaned')
"""
    out, _ = mpremote_exec(port, code)
    info(out)

    # 2. 拷贝 nova_server.py 到 /lib/nova_server.py（★ 单文件部署）
    info('Copying nova_server.py (single-file)...')
    ok_flag, err = mpremote_cp(
        port, os.path.join(ROOT, 'nova_server.py'),
        ':lib/nova_server.py')
    if not ok_flag:
        fail('copy nova_server.py failed: {}'.format(err))
        return False
    ok('nova_server.py copied')

    # 3. 拷贝测试应用
    info('Copying {}...'.format(app_name))
    src = os.path.join(ROOT, 'examples', app_name + '.py')
    if not os.path.exists(src):
        fail('app not found: {}'.format(src))
        return False
    ok_flag, err = mpremote_cp(port, src, ':main.py')
    if not ok_flag:
        fail('copy app failed: {}'.format(err))
        return False
    ok('app copied')

    # 4. 软重启
    info('Resetting ESP32...')
    mpremote_reset(port)
    time.sleep(1)
    return True


def get_esp32_ip(port):
    """获取 ESP32 的 IP（连着的 WiFi）。

    ★ 重置后第一次连可能还在 boot，所以只发一次，不在循环里调。
    """
    code = """
import network
w = network.WLAN(network.STA_IF)
if w.isconnected():
    print(w.ifconfig()[0])
else:
    print('0.0.0.0')
"""
    out, _ = mpremote_exec(port, code)
    return out.strip().splitlines()[-1] if out else '0.0.0.0'


def get_esp32_memory(port):
    """获取 ESP32 当前堆状态。"""
    code = """
import gc
gc.collect()
print(gc.mem_free(), gc.mem_alloc())
"""
    out, _ = mpremote_exec(port, code)
    parts = out.strip().split()
    if len(parts) >= 2:
        return int(parts[0]), int(parts[1])
    return None, None


def scan_for_esp32(network_prefix='192.168.71'):
    """扫描本地子网找 ESP32（IP 在 port 80 监听 nova-server）。"""
    import urllib.request
    import urllib.error
    for i in range(1, 255):
        ip = '{}.{}'.format(network_prefix, i)
        if not wait_for_port(ip, 80, timeout=0.2):
            continue
        try:
            resp = urllib.request.urlopen(
                'http://{}/api/version'.format(ip), timeout=1)
            body = resp.read().decode('utf-8', errors='replace')
            if 'nova-server' in body:
                return ip
        except Exception:
            continue
    return None


def test_endpoints(host, port=80):
    """HTTP 测试所有端点。"""
    step('Testing HTTP endpoints on {}:{}'.format(host, port))

    tests = [
        # (path, expected_status, expected_body_contains)
        ('/', 302, None),
        ('/hello/ESP32', 200, 'ESP32'),
        ('/api/version', 200, 'nova-server'),
        ('/health', 200, 'memory'),
        ('/api/wifi', 200, 'connected'),
        ('/nonexistent', 404, None),
    ]

    passed = 0
    failed = 0
    for path, expected_status, expected_body in tests:
        status, body = http_get(host, port, path)
        if status == expected_status:
            if expected_body is None or expected_body in body:
                ok('{} → {} (body: {})'.format(
                    path, status, body[:60] if body else '(empty)'))
                passed += 1
            else:
                fail('{} → {} but body missing "{}"'.format(
                    path, status, expected_body))
                failed += 1
        else:
            fail('{} → {} (expected {})'.format(path, status, expected_status))
            failed += 1

    return passed, failed


def test_stability(host, port=80, count=30):
    """压力测试：连续 N 次请求，要求无错。"""
    step('Stability test: {} sequential requests'.format(count))
    errors = 0
    durations = []
    for i in range(count):
        start = time.time()
        status, body = http_get(host, port, '/api/version', timeout=5)
        durations.append(time.time() - start)
        if status != 200:
            errors += 1
            print('  request {} failed: {}'.format(i, status))
    avg_ms = sum(durations) / len(durations) * 1000
    if errors == 0:
        ok('{} requests OK, avg {:.1f} ms'.format(count, avg_ms))
    else:
        fail('{}/{} requests failed'.format(errors, count))
    return errors == 0


def test_memory(port, before_free):
    """检查内存泄漏。"""
    step('Memory check')
    free, alloc = get_esp32_memory(port)
    if free is None:
        info('cannot read memory')
        return False
    delta = before_free - free if before_free else 0
    info('free: {} KB, alloc: {} KB, delta: {} B'.format(
        free // 1024, alloc // 1024, delta))
    if delta > 5 * 1024:
        fail('possible memory leak: {} B lost'.format(delta))
        return False
    ok('no significant memory leak')
    return True


# ════════════════════════════════════════════════════════════════
# 主流程
# ════════════════════════════════════════════════════════════════

def main():
    arg_port = sys.argv[1] if len(sys.argv) > 1 else None
    port = detect_port(arg_port)
    if not port:
        fail('No ESP32 detected. Connect via USB or specify PORT.')
        sys.exit(1)
    ok('Detected ESP32 on {}'.format(port))

    # 设备识别
    out, _ = mpremote_exec(port, "import sys; print(sys.implementation[0])")
    if 'micropython' not in out:
        fail('Device is not MicroPython: {}'.format(out))
        sys.exit(1)
    ok('MicroPython confirmed')

    # 备份
    backup_dir = tempfile.mkdtemp(prefix='nova_test_')
    step('Backing up device to {}...'.format(backup_dir))
    backup_device(port, backup_dir)
    ok('backup saved')

    # 部署前的内存
    before_free, _ = get_esp32_memory(port)
    if before_free:
        info('memory before: {} KB free'.format(before_free // 1024))

    # 部署
    if not deploy(port, '01_hello_esp32'):
        fail('deploy failed')
        restore_device(port, backup_dir)
        sys.exit(1)

    # 等 server 起来（不用 mpremote exec 干扰 boot）
    step('Waiting for server to start (no exec to avoid interrupt)...')
    time.sleep(8)  # 给 ESP32 足够时间 boot + 连 WiFi + 起 server

    # 扫描子网找 IP（scan_for_esp32 内部已验证是 nova-server）
    network_prefix = os.environ.get('ESP32_NET_PREFIX', '192.168.71')
    info('scanning {}.1-254 for nova-server...'.format(network_prefix))
    ip = scan_for_esp32(network_prefix)
    if ip:
        ok('nova-server is up at {}'.format(ip))
    else:
        fail('no nova-server found on {}.x'.format(network_prefix))
        fail('check: is ESP32 connected to WiFi? Is main.py correct?')
        _do_cleanup(port, backup_dir)
        sys.exit(1)

    # 测试
    p1, f1 = test_endpoints(ip)
    p2 = test_stability(ip, count=30)
    p3 = test_memory(port, before_free)

    # 总结
    step('Summary')
    total_pass = p1 + (1 if p2 else 0) + (1 if p3 else 0)
    total_fail = f1 + (0 if p2 else 1) + (0 if p3 else 1)
    if total_fail == 0:
        ok('ALL TESTS PASSED ({}/{})'.format(total_pass,
                                              total_pass + total_fail))
    else:
        fail('{} tests failed'.format(total_fail))

    # 恢复
    step('Restoring device...')
    _do_cleanup(port, backup_dir)
    ok('device restored')


def _do_cleanup(port, backup_dir):
    """恢复设备 + 清理临时文件。"""
    restore_device(port, backup_dir)
    _cleanup_nova_server(port)
    shutil.rmtree(backup_dir, ignore_errors=True)


def _cleanup_nova_server(port):
    """清理 /lib/nova_server（如果还在）。"""
    code = """
import os
def rmtree(path):
    try:
        for f in os.listdir(path):
            full = path + '/' + f
            try:
                if os.stat(full)[0] == 16384:
                    rmtree(full)
                else:
                    os.remove(full)
            except: pass
        os.rmdir(path)
    except: pass
try: rmtree('/lib/nova_server')
except: pass
print('cleaned')
"""
    mpremote_exec(port, code)


if __name__ == '__main__':
    main()