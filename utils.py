# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 zimo <zimo@zmlll.top>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
工具函数模块
提供 curl 路径查找、文件名清洗、文件大小格式化等功能。
"""

import sys
import pathlib
import re


def get_curl_path():
    """查找 curl 可执行文件路径

    查找顺序：
    1. 脚本同目录下的 curl.exe
    2. 打包后的资源目录下的 curl.exe
    3. 系统环境变量中的 curl

    Returns:
        curl 可执行文件的完整路径或命令名
    """
    if getattr(sys, 'frozen', False):
        # 打包后的运行环境
        base_path = pathlib.Path(sys._MEIPASS)
    else:
        # 开发环境
        base_path = pathlib.Path(__file__).parent

    # 1. 检查脚本同目录
    local_curl = pathlib.Path(__file__).parent / "curl.exe"
    if local_curl.exists():
        return str(local_curl)

    # 2. 检查打包后的资源目录
    bundled_curl = base_path / "curl.exe"
    if bundled_curl.exists():
        return str(bundled_curl)

    # 3. 使用系统环境变量中的 curl
    return "curl"


def safe_path_part(part: str) -> str:
    """清洗文件名，过滤非法字符

    只保留英文字母、数字、下划线、空格、连字符、点和空格。
    其他字符（包括中文、全角符号、特殊字符）替换为下划线。

    Args:
        part: 原始文件名或路径片段

    Returns:
        清洗后的安全文件名
    """
    # 白名单策略：非允许字符替换为下划线
    part = re.sub(r'[^a-zA-Z0-9_. -]', '_', part)

    # 去除首尾空格和点
    part = part.strip(' .')

    # 限制最大长度
    if len(part) > 100:
        part = part[:100]

    # 避免空字符串
    return part or "_"


def format_size(bytes):
    """将字节数转换为易读的文件大小字符串

    Examples:
        format_size(1024)      -> "1.00 KB"
        format_size(1048576)   -> "1.00 MB"
        format_size(1073741824) -> "1.00 GB"

    Args:
        bytes: 字节数

    Returns:
        格式化后的大小字符串，如 "1.50 MB"
    """
    if bytes == 0:
        return '0 B'

    k = 1024
    sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    import math

    i = int(math.floor(math.log(bytes, k))) if bytes > 0 else 0
    return f"{float(bytes / math.pow(k, i)):.2f} {sizes[i]}"
