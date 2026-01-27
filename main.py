# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 zimo <zimo@zmlll.top>
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
import time
import threading
import webbrowser
import logging
import os
from datetime import datetime
from pathlib import Path
import queue

import config
import downloader
import web_server
import system_tray
import console_window
from shared import set_console_window, LOG_MESSAGES, log_message, save_log as shared_save_log

# 日志配置
LOG_MESSAGES = []  # 内存中存储的日志列表
LOG_COLORS = {
    "INFO": "#22c55e",    # 绿色 - 普通信息
    "WARNING": "#eab308", # 黄色 - 警告
    "ERROR": "#ef4444",   # 红色 - 错误
    "DEBUG": "#3b82f6",   # 蓝色 - 调试信息
    "SYSTEM": "#a855f7",  # 紫色 - 系统消息
    "TASK": "#06b6d4",    # 青色 - 任务进度
}


def log_message(level, message):
    """输出日志到内存和界面控制台"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    # 存入内存日志列表
    LOG_MESSAGES.append({
        "timestamp": timestamp,
        "level": level,
        "message": message
    })

    # 输出到界面控制台
    try:
        console_win = getattr(log_message, '_console_win', None)
        if console_win:
            console_win.log(level, f"[{timestamp}] [{level}] {message}")
    except:
        pass


def save_log(save_type="自动"):
    """将日志保存到文件"""
    try:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = config.LOG_DIR / config.get_log_filename(save_type)

        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"ASMRip 日志\n")
            f.write(f"保存类型: {save_type}保存\n")
            f.write(f"保存时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'=' * 60}\n\n")
            for entry in LOG_MESSAGES:
                f.write(f"[{entry['timestamp']}] [{entry['level']}] {entry['message']}\n")

        log_message("SYSTEM", f"日志已保存: {log_file.name}")
        return log_file.name
    except Exception as e:
        print(f"保存日志失败: {e}")
        return None


def setup_logging():
    """清空内存中的日志"""
    global LOG_MESSAGES
    LOG_MESSAGES = []


def main():
    """程序主入口"""
    global console_win

    # 初始化日志控制台窗口
    console_win = console_window.ConsoleWindow()
    log_message._console_win = console_win  # 绑定控制台实例
    set_console_window(console_win)

    # 清空旧日志
    setup_logging()

    # 输出启动信息
    log_message("SYSTEM", f"=== {config.APP_NAME} v{config.VERSION} ===")
    log_message("SYSTEM", f"Author: {config.AUTHOR}")
    log_message("SYSTEM", "[System] 正在初始化服务...")

    # 创建必要的目录
    if not config.DEFAULT_DOWNLOAD_DIR.exists():
        config.DEFAULT_DOWNLOAD_DIR.mkdir(parents=True)
        log_message("SYSTEM", f"创建下载目录: {config.DEFAULT_DOWNLOAD_DIR}")

    # 启动后台下载线程
    downloader.start_worker_thread()
    log_message("SYSTEM", "[System] 下载线程已启动")

    # 启动 Web 服务器
    server_thread = threading.Thread(target=web_server.run_flask, daemon=True)
    server_thread.start()
    log_message("SYSTEM", f"[Server] Web 服务已启动: http://{config.HOST}:{config.PORT}")

    # 延迟打开浏览器
    browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
    browser_thread.start()

    # 启动系统托盘
    icon = system_tray.create_tray_icon()
    tray_thread = threading.Thread(target=system_tray.run_tray, args=(icon,), daemon=True)
    tray_thread.start()
    log_message("SYSTEM", "[System] 系统托盘已启动")

    # 进入主循环（阻塞）
    try:
        console_win.run()
    except KeyboardInterrupt:
        log_message("SYSTEM", "程序已手动终止")
    except Exception as e:
        log_message("ERROR", f"发生未捕获的异常: {e}")
    finally:
        save_log("自动")                  # 保存普通日志
        shared_save_log("自动", detailed=True)  # 保存详细日志
        log_message("SYSTEM", "程序已退出")
        os._exit(0)


def open_browser_delayed():
    """延迟 1.5 秒后自动打开浏览器"""
    time.sleep(1.5)
    url = f"http://{config.HOST}:{config.PORT}"
    try:
        webbrowser.open(url)
        log_message("SYSTEM", f"已打开浏览器: {url}")
    except:
        pass


if __name__ == "__main__":
    main()
