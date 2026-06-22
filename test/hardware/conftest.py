"""
hardware/conftest.py — 让 pytest 跳过 hardware 目录

hardware/test_deploy_esp32.py 是独立脚本，不是 pytest 测试。
"""
collect_ignore_glob = ['*.py']