# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 zimo <zimo@zmlll.top>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
配置文件
包含软件版本、网络设置、路径配置等全局参数。
"""

import sys
import os
import pathlib
from datetime import datetime

# ============================================================
# 软件信息
# ============================================================
VERSION = "1.0.0"  # 版本号
AUTHOR = "zimo"  # 作者名
APP_NAME = "ASMRip"  # 应用名称

# ============================================================
# 网络配置
# ============================================================
HOST = "127.0.0.1"  # Web 服务监听地址
PORT = 4565  # Web 服务端口号
API_ENDPOINT = "https://api.asmr-200.com"  # ASMR API 地址

# ============================================================
# 文件路径配置
# ============================================================
if getattr(sys, 'frozen', False):
    # 打包后的运行环境：使用可执行文件所在目录
    BASE_DIR = pathlib.Path(sys.executable).parent.resolve()
else:
    # 开发环境：使用脚本文件所在目录
    BASE_DIR = pathlib.Path(__file__).parent.resolve()

DEFAULT_DOWNLOAD_DIR = BASE_DIR / "Download"  # 默认下载目录

# ============================================================
# 日志配置
# ============================================================
LOG_LEVEL = "INFO"  # 日志级别
LOG_DIR = BASE_DIR / "log"  # 日志文件目录

# 启动计数器文件路径
STARTUP_COUNT_FILE = LOG_DIR / "startup_count.txt"


def get_startup_count():
    """获取本次启动的序号（用于日志文件名）"""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        if STARTUP_COUNT_FILE.exists():
            with open(STARTUP_COUNT_FILE, 'r') as f:
                count = int(f.read().strip()) + 1
        else:
            count = 1
        with open(STARTUP_COUNT_FILE, 'w') as f:
            f.write(str(count))
        return count
    except:
        return 1


def get_log_filename(save_type="自动"):
    """生成日志文件名

    格式: 2024-01-28_日志_自动保存_第3次启动.log
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    count = get_startup_count()
    return f"{date_str}_日志_{save_type}保存_第{count}次启动.log"
