# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 zimo <zimo@zmlll.top>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
日志控制台窗口模块
使用 Tkinter 创建独立的日志查看窗口，支持彩色显示不同级别的日志。
"""

import tkinter as tk
import tkinter.scrolledtext as ScrolledText
import queue

from shared import GLOBAL_CMD_QUEUE


class ConsoleWindow:
    """日志控制台窗口类"""

    def __init__(self):
        # 初始化 Tkinter 根窗口
        self.root = tk.Tk()
        self.root.title(f"ASMRip - Console Log")
        self.root.geometry("900x600")
        self.root.configure(bg='black')

        # 创建日志文本显示区域
        self.text = ScrolledText.ScrolledText(
            self.root,
            bg='black',
            fg='#e0e0e0',  # 浅灰色文字
            font=('Consolas', 10),  # 等宽字体
            state='disabled'  # 初始禁用，通过代码插入内容
        )
        self.text.pack(fill=tk.BOTH, expand=True)

        # 配置日志级别对应的颜色
        self.text.tag_config("INFO", foreground="#e0e0e0")  # 普通信息
        self.text.tag_config("WARNING", foreground="#facc15")  # 警告
        self.text.tag_config("ERROR", foreground="#ef4444")  # 错误
        self.text.tag_config("DEBUG", foreground="#3b82f6")  # 调试
        self.text.tag_config("SYSTEM", foreground="#a855f7")  # 系统
        self.text.tag_config("TASK", foreground="#06b6d4")  # 任务
        self.text.tag_config("DOWNLOAD", foreground="#3b82f6")  # 下载进度
        self.text.tag_config("PROGRESS", foreground="#a855f7")  # 进度百分比

        # 线程安全的日志队列
        self.log_queue = queue.Queue()

        # 拦截窗口关闭事件：点击 X 隐藏窗口而非退出程序
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        # 启动 UI 更新定时器（每 100ms 检查一次队列）
        self.root.after(100, self._update_ui)

        # 强制刷新窗口，确保显示出来
        self.root.update()

    def _update_ui(self):
        """定时检查队列并更新 UI（主线程调用）"""

        # 1. 处理窗口控制命令
        try:
            while True:
                cmd = GLOBAL_CMD_QUEUE.get_nowait()
                if cmd == 'show':
                    # 显示窗口并置顶
                    self.root.deiconify()
                    self.root.lift()
                    self.root.focus_force()  # 强制获得焦点
                elif cmd == 'hide':
                    self.root.withdraw()
        except queue.Empty:
            pass

        # 2. 处理日志消息
        try:
            while True:
                data = self.log_queue.get_nowait()

                # 解析日志数据（兼容 2 元组和 3 元组格式）
                if isinstance(data, tuple) and len(data) == 2:
                    level_name, message = data
                    extra = None
                elif isinstance(data, tuple) and len(data) == 3:
                    level_name, message, extra = data
                else:
                    return  # 格式错误，丢弃

                # 判断是否为进度消息
                if isinstance(extra, dict) and extra.get("progress"):
                    # 进度消息：清空后写入新内容（单行刷新）
                    self.text.config(state='normal')
                    self.text.delete(1.0, tk.END)
                    self.text.insert(tk.END, message + "\n", level_name)
                    self.text.see(tk.END)
                    self.text.config(state='disabled')
                else:
                    # 普通日志：追加到末尾
                    self.text.config(state='normal')
                    self.text.insert(tk.END, message + "\n", level_name)
                    self.text.see(tk.END)
                    self.text.config(state='disabled')
        except queue.Empty:
            pass

        # 继续定时检查
        self.root.after(100, self._update_ui)

    def run(self):
        """启动 Tkinter 主循环（必须在主线程调用）"""
        self.root.mainloop()

    def show(self):
        """显示窗口（供外部调用）"""
        GLOBAL_CMD_QUEUE.put('show')

    def hide(self):
        """隐藏窗口"""
        self.root.withdraw()

    def log(self, level_name, message, extra=None):
        """写入日志到控制台"""
        self.log_queue.put((level_name, message, extra))
