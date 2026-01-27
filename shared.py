# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 zimo <zimo@zmlll.top>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
共享模块
提供全局队列、日志系统等跨模块共享的功能。
"""

import queue
from datetime import datetime
from pathlib import Path


def get_config():
    """获取配置模块"""
    import config
    return config


# ============================================================
# 全局队列
# ============================================================

GLOBAL_CMD_QUEUE = queue.Queue()  # 用于托盘与窗口间的命令通信

# ============================================================
# 日志系统
# ============================================================

LOG_MESSAGES = []  # 内存中存储的日志列表

# 日志级别对应的颜色（供 UI 显示使用）
LOG_COLORS = {
    "INFO": "#22c55e",  # 绿色
    "WARNING": "#eab308",  # 黄色
    "ERROR": "#ef4444",  # 红色
    "DEBUG": "#3b82f6",  # 蓝色
    "SYSTEM": "#a855f7",  # 紫色
    "TASK": "#06b6d4",  # 青色
}

console_window_ref = None  # 控制台窗口实例引用


def set_console_window(console_win):
    """设置控制台窗口实例"""
    global console_window_ref
    console_window_ref = console_win


def log_message(level, message):
    """输出日志到内存和控制台窗口

    Args:
        level: 日志级别 (INFO/WARNING/ERROR/SYSTEM/TASK/DEBUG)
        message: 日志内容
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    LOG_MESSAGES.append({
        "timestamp": timestamp,
        "level": level,
        "message": message
    })

    if console_window_ref:
        try:
            console_window_ref.log(level, f"[{timestamp}] [{level}] {message}")
        except:
            pass


def save_log(save_type="自动", detailed=False):
    """将日志保存到文件

    Args:
        save_type: 保存类型（自动/手动）
        detailed: 是否保存详细日志（仅包含任务相关记录）

    Returns:
        保存的文件名，失败返回 None
    """
    try:
        cfg = get_config()
        cfg.LOG_DIR.mkdir(parents=True, exist_ok=True)

        # 选择文件名
        if detailed:
            filename = f"{datetime.now().strftime('%Y-%m-%d')}_下载详细日志.log"
        else:
            filename = cfg.get_log_filename(save_type)

        log_file = cfg.LOG_DIR / filename

        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"ASMRip {'详细' if detailed else ''}日志\n")
            f.write(f"保存类型: {save_type}保存\n")
            f.write(f"保存时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'=' * 60}\n\n")

            if detailed:
                # 详细日志：只保留任务相关记录
                f.write("【下载详细记录】\n")
                f.write("-" * 60 + "\n")
                for entry in LOG_MESSAGES:
                    if "[TASK]" in entry["message"] or "完成:" in entry["message"] or "跳过:" in entry["message"]:
                        f.write(f"[{entry['timestamp']}] {entry['message']}\n")
                f.write("\n" + "=" * 60 + "\n\n")

            # 普通日志：输出所有记录
            for entry in LOG_MESSAGES:
                f.write(f"[{entry['timestamp']}] [{entry['level']}] {entry['message']}\n")

        log_message("SYSTEM", f"日志已保存: {log_file.name}")
        return log_file.name
    except Exception as e:
        print(f"保存日志失败: {e}")
        return None
