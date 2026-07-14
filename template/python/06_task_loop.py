"""
06_task_loop.py — @app.task 后台周期任务（按钮 → LED）
=======================================================

用 nova-server 的 @app.task 装饰器做"循环判断"，
让不懂 asyncio 的同学也能用。

v0.2+ 新功能。

硬件接线（ESP32）：
  内置 LED ──── GPIO 2
  按键一脚 ──── GPIO 4
  按键另一脚 ── GND（Button 内部自动上拉）

部署：
  mpremote connect COM3 cp main.py :main.py
  mpremote reset

测试：
  按一下按钮 → LED 翻转
  curl http://<IP>/api/led          → 查询状态
  curl http://<IP>/api/tasks        → 查看后台任务
"""

from nova_server import NovaServer
from machine import Pin
from button import Button        # novamp 驱动
from led import LED              # novamp 驱动


# ═══════════════════════════════════════════════════════════
# 硬件初始化
# ═══════════════════════════════════════════════════════════

_led = LED(Pin(2))
_btn = Button(Pin(4))
_led.off()

_state = {'led_on': False, 'click_count': 0}


# ═══════════════════════════════════════════════════════════
# ★ 核心：@app.task 一行搞定后台循环
# ═══════════════════════════════════════════════════════════
#
# 装饰一个普通函数（不用 async def！），
# nova-server 自动按 interval_ms 毫秒的间隔反复调用它。

@app.task(interval_ms=30)
def check_button():
    """每 30ms 扫一次按钮，按下就翻转 LED。

    30ms 选择理由：
      - > Button 的 debounce_delay（默认 10ms），不会漏检
      - < 人手按键时长（>50ms），响应无延迟
      - CPU 占用极低（<1%）
    """
    if _btn.is_clicked():
        _state['led_on'] = not _state['led_on']
        _state['click_count'] += 1
        _led.on() if _state['led_on'] else _led.off()


# ═══════════════════════════════════════════════════════════
# HTTP 接口（远程查看）
# ═══════════════════════════════════════════════════════════

app = NovaServer()


@app.get('/api/led')
async def get_led(request):
    return {'on': _state['led_on'], 'clicks': _state['click_count']}


@app.get('/api/tasks')
async def list_tasks(request):
    """远程查看后台任务（调试用）。"""
    return {'tasks': app.tasks()}


# ═══════════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════════
# 不需要 asyncio.create_task，不需要 while True，不需要 await，
# 全部由 nova-server 内部搞定。

app.run()