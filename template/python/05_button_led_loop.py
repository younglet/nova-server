"""
05_button_led_loop.py
=====================

"循环判断"模式：按钮直接控制 LED 开关
--------------------------------------

用 nova-server + asyncio 后台任务做"无限循环"，
每 30ms 轮询一次按钮，按下就切换 LED。
同时保留 HTTP 接口，远程也能覆盖 LED 状态。

硬件接线（ESP32）：
  LED 正极 ──[ 220Ω ]── GPIO 2   (内置 LED 可省电阻)
  LED 负极 ──────────── GND
  按键一脚 ──────────── GPIO 4
  按键另一脚 ────────── GND         (Button 内部自动上拉)

部署：
  mpremote connect COM3 cp main.py :main.py
  mpremote reset

测试：
  按一下按钮 → LED 翻转
  curl http://<ESP32-IP>/api/led        → 查询当前状态
  curl -X POST http://<ESP32-IP>/api/led -d 'state=on'
"""

import asyncio
import time
from machine import Pin
from nova_server import NovaServer
from button import Button        # novamp 驱动（带硬件去抖）
from led import LED             # novamp 驱动（PWM，可做亮度调节）


# ═══════════════════════════════════════════════════════════
# 硬件初始化
# ═══════════════════════════════════════════════════════════

LED_PIN = 2
BTN_PIN = 4

_led = LED(Pin(LED_PIN))
_btn = Button(Pin(BTN_PIN))     # 自动配置为输入上拉，按下 = 低电平
_led.off()


# ═══════════════════════════════════════════════════════════
# ★ 核心：后台"循环判断"协程
# ═══════════════════════════════════════════════════════════
#
# 这就是 nova-server 上的"timer 循环"——
# 把它放进 asyncio.create_task() 里就行，不要写在主循环里
# （主循环是 start_server()，你插不进 while True）。

# 共享状态（后台任务写，HTTP 接口读）
_state = {
    'led_on': False,             # 当前 LED 是否亮
    'click_count': 0,            # 累计按下次数
    'last_toggle_ms': 0,         # 上次翻转时间戳（用于日志）
}


async def button_poll_loop():
    """每 30ms 轮询一次按钮，按下就翻转 LED。

    30ms 远小于人手按键时长（>50ms），
    也大于 Button 的 debounce_delay（默认 10ms），
    是个安全值。
    """
    print('[loop] button poll task started')
    while True:
        # ★ 必须用 asyncio.sleep_ms，不能 time.sleep
        #   time.sleep 会阻塞整个事件循环，把 web server 卡死
        if _btn.is_clicked():                # 一次完整"按下+松开"返回 True
            _state['led_on'] = not _state['led_on']
            _state['click_count'] += 1
            _state['last_toggle_ms'] = time.ticks_ms()

            if _state['led_on']:
                _led.on()
            else:
                _led.off()

            print('[loop] click #{} -> LED {}'.format(
                _state['click_count'],
                'ON' if _state['led_on'] else 'OFF',
            ))

        await asyncio.sleep_ms(30)


# ═══════════════════════════════════════════════════════════
# 远程 API（可选，方便调试 & UI 集成）
# ═══════════════════════════════════════════════════════════

app = NovaServer()


@app.get('/api/led')
async def get_led(request):
    """查询 LED 当前状态。"""
    return {
        'on': _state['led_on'],
        'click_count': _state['click_count'],
        'uptime_ms': time.ticks_diff(
            time.ticks_ms(), _state['last_toggle_ms']
        ) if _state['last_toggle_ms'] else None,
    }


@app.post('/api/led')
async def set_led(request):
    """远程强制控制 LED（按钮逻辑依然并行）。

    Body:  {"state": "on"} 或 {"state": "off"}
    """
    data = request.json or {}
    if data.get('state') not in ('on', 'off'):
        return {'error': 'state must be "on" or "off"'}, 400

    _state['led_on'] = (data['state'] == 'on')
    if _state['led_on']:
        _led.on()
    else:
        _led.off()

    return {'led': 'on' if _state['led_on'] else 'off'}


# ═══════════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════════

async def main():
    # ★ 关键：在 start_server 之前启动后台循环
    asyncio.create_task(button_poll_loop())
    await app.start_server()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('[boot] stopped')
    except Exception as e:
        print('[boot] error:', e)

# ═══════════════════════════════════════════════════════════
# 备选方案 B：machine.Timer 硬件定时器（不推荐给按钮用）
# ═══════════════════════════════════════════════════════════
#
# 用硬件定时器做按钮轮询需要解决三个问题：
#   1. 回调在中断上下文，不能分配内存、不能 await
#   2. 改 LED 状态需要和 asyncio 协程同步（用 Lock）
#   3. 一旦按下要 "延迟一段时间再读" 才能消抖，跨中断不方便
#
# 所以按钮场景请优先用上面的 asyncio 方案。
# 这个示例仅展示 Timer 怎么和 nova-server 并存：

def _on_timer_tick(timer):
    """中断回调：必须短小、不能分配内存。

    ★ 回调签名固定 (timer) 一个参数，否则崩溃。
    """
    if _btn.is_clicked():
        # 不能 await，不能放队列以外的复杂对象
        # 只设置一个简单标志位，让主事件循环看到
        try:
            _state['_pending_toggle'] = True
        except Exception:
            pass


def start_hardware_timer():
    """演示：每 30ms 由硬件定时器扫一次按钮。"""
    from machine import Timer
    from micropython import alloc_emergency_exception_buf

    # 强烈建议：给 timer 中断预留异常缓冲，否则出错你看不到
    alloc_emergency_exception_buf(100)

    tim = Timer(0)
    tim.init(period=30, mode=Timer.PERIODIC, callback=_on_timer_tick)
    return tim


# 如果你想用这个方案，把 main() 换成：

# async def main():
#     start_hardware_timer()
#     asyncio.create_task(led_apply_loop())
#     await app.start_server()
#
# async def led_apply_loop():
#     """在主事件循环里把 timer 设的标志转成 LED 状态。"""
#     while True:
#         if _state.get('_pending_toggle'):
#             _state['_pending_toggle'] = False
#             _led.switch()
#         await asyncio.sleep_ms(10)
