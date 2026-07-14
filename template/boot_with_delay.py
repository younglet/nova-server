# boot_with_delay.py — 开发用 boot.py 模板
# ============================================
#
# 与默认 boot.py 的区别：顶部 sleep(5) 留 5 秒传文件窗口。
#
# 为什么需要这个：
#   默认 boot.py 跑完后 MicroPython 自动执行 main.py，
#   而 main.py 里 app.run() 会永久阻塞、占着串口，
#   导致 mpremote cp 无法传新文件。
#
#   顶部加 5 秒 sleep，MicroPython boot 阶段会等 5 秒，
#   在这期间可以用 mpremote cp 传新版的 main.py / boot.py。
#
# 使用场景：
#   - 开发调试时频繁改 main.py，需要快速部署
#   - 默认 boot.py（template/main.py 顶部注释里那个）连 WiFi 后
#     不留窗口，传文件要硬重启 ESP32
#
# 不适用场景：
#   - 生产环境（5 秒延迟让用户感觉"启动慢"）
#   - 有 OTA 升级的项目（用 HTTP 自己传文件即可）
#
# 部署：
#   mpremote connect COM3 cp boot_with_delay.py :boot.py
#   mpremote connect COM3 reset

import time
import gc

# ★ 顶部 sleep：上电后 5 秒内可以 mpremote cp 传文件
time.sleep(5)

try:
    from wifi import WiFi
    wifi = WiFi('Milk_Tea', 'huijia501')    # ★ 改成你的 WiFi 名/密码
    if wifi.connect():
        print('[boot] WiFi OK:', wifi.ip)
    else:
        print('[boot] WiFi failed')
except Exception as e:
    print('[boot] WiFi error:', e)

gc.collect()
print('[boot] done, main.py will run next')