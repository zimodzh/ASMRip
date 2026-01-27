# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 zimo <zimo@zmlll.top>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
系统托盘模块
使用 pystray 创建系统托盘图标，提供快速访问菜单。
"""

import webbrowser
import sys
import os
import signal
import threading
import time
import pathlib

import pystray
from PIL import Image, ImageDraw

import config
from shared import GLOBAL_CMD_QUEUE, log_message, save_log


def get_app_icon():
    """获取应用图标"""
    if getattr(sys, 'frozen', False):
        # 打包后的运行环境
        base_path = pathlib.Path(sys._MEIPASS)
    else:
        # 开发环境
        base_path = pathlib.Path(__file__).parent

    icon_path = base_path / "icon.ico"
    if icon_path.exists():
        try:
            return Image.open(icon_path)
        except:
            pass

    # 无图标时返回默认紫色方块
    return Image.new('RGB', (64, 64), color=(79, 70, 229))


def on_open(icon, item):
    """打开 Web 界面"""
    url = f"http://{config.HOST}:{config.PORT}"
    webbrowser.open(url)
    log_message("SYSTEM", "用户打开 Web 界面")


def on_toggle_console(icon, item):
    """显示日志窗口"""
    GLOBAL_CMD_QUEUE.put('show')
    log_message("SYSTEM", "用户显示日志窗口")


def on_exit(icon, item):
    """退出程序"""
    # 停止正在进行的下载
    try:
        import downloader
        downloader.download_stop_signal = True
        log_message("SYSTEM", "正在停止下载任务...")
    except Exception as e:
        print(f"停止下载任务失败: {e}")

    # 保存日志文件
    save_log("自动")
    log_message("SYSTEM", "用户退出程序")

    # 停止托盘图标
    try:
        icon.stop()
    except:
        pass

    # 强制退出进程
    os._exit(0)


def create_tray_icon():
    """创建托盘图标并返回实例"""
    image = get_app_icon()

    menu = pystray.Menu(
        pystray.MenuItem("打开 Web 界面", on_open),
        pystray.MenuItem("显示日志窗口", on_toggle_console),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出程序", on_exit)
    )

    icon = pystray.Icon(
        name="zimo_asmr_downloader",
        icon=image,
        title=f"ASMRip v{config.VERSION}",
        menu=menu
    )

    return icon


def run_tray(icon):
    """运行托盘图标主循环"""
    icon.run()
