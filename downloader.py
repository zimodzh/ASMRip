# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 zimo <zimo@zmlll.top>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
下载模块
负责从 ASMR 网站下载音频文件，使用 curl 进行下载操作。
"""

import sys
import pathlib
import subprocess
import threading
import queue
import orjson
import logging
import time
import re
from datetime import datetime

# Windows 平台静默启动配置
if sys.platform == 'win32':
    STARTF_USESHOWWINDOW = 0x00000001
    SW_HIDE = 0

import config
import utils
from shared import log_message

# ============================================================
# 全局变量：任务队列与状态标志
# ============================================================

task_queue = queue.Queue()  # 待下载任务队列
download_stop_signal = False  # 下载停止信号
delete_partial_signal = False  # 是否删除未完成的文件

# ============================================================
# 下载进度相关
# ============================================================

is_downloading = False  # 是否正在下载

# 当前下载进度信息
current_progress = {
    "total_percent": 0.0,  # 总进度百分比
    "current_file_percent": 0.0,  # 当前文件进度
    "current_filename": "",  # 当前下载的文件名
    "speed": 0.0,  # 下载速度 (KB/s)
    "downloaded_size": 0,  # 已下载字节数
    "total_size": 0,  # 总字节数
}
progress_lock = threading.Lock()  # 进度数据锁

# 下载统计信息
download_stats = {
    "total_files": 0,  # 总文件数
    "success_files": 0,  # 成功数
    "failed_files": 0,  # 失败数
    "failed_list": [],  # 失败文件列表
    "stopped_by_user": False,  # 是否用户手动停止
    "pending_finish": False,  # 是否有待显示的完成结果
}
stats_lock = threading.Lock()  # 统计信息锁

# 网速计算相关
last_speed_time = time.time()
last_downloaded_size = 0
speed_lock = threading.Lock()

# Windows 静默启动配置
if sys.platform == 'win32':
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= STARTF_USESHOWWINDOW
    STARTUPINFO.wShowWindow = SW_HIDE
else:
    STARTUPINFO = None


# ============================================================
# 进度查询与控制函数
# ============================================================

def get_status():
    """返回是否正在下载"""
    global is_downloading
    return is_downloading


def get_progress():
    """获取当前下载进度（线程安全）"""
    global current_progress, last_speed_time, last_downloaded_size

    with speed_lock:
        now = time.time()
        # 每秒计算一次下载速度
        if now - last_speed_time >= 1.0:
            delta_size = current_progress["downloaded_size"] - last_downloaded_size
            delta_time = now - last_speed_time
            if delta_time > 0 and last_downloaded_size > 0:
                current_progress["speed"] = round(delta_size / 1024 / delta_time, 2)
            last_downloaded_size = current_progress["downloaded_size"]
            last_speed_time = now

    with progress_lock:
        return current_progress.copy()


def set_progress(total_percent, current_file_percent, current_filename, downloaded_size=0, total_size=0):
    """设置当前下载进度"""
    global current_progress
    with progress_lock:
        current_progress = {
            "total_percent": round(total_percent, 2),
            "current_file_percent": str(current_file_percent) if isinstance(current_file_percent, str) else round(
                current_file_percent, 2),
            "current_filename": current_filename,
            "speed": current_progress["speed"],
            "downloaded_size": downloaded_size,
            "total_size": total_size
        }


def reset_progress():
    """重置所有进度和统计数据"""
    global current_progress, last_downloaded_size, last_speed_time, download_stats
    with progress_lock, speed_lock, stats_lock:
        current_progress = {
            "total_percent": 0.0,
            "current_file_percent": 0.0,
            "current_filename": "",
            "speed": 0.0,
            "downloaded_size": 0,
            "total_size": 0
        }
        last_downloaded_size = 0
        last_speed_time = time.time()
        download_stats = {
            "total_files": 0,
            "success_files": 0,
            "failed_files": 0,
            "failed_list": [],
            "stopped_by_user": False,
            "pending_finish": False
        }


# ============================================================
# API 请求函数
# ============================================================

def request_by_curl(url: str, timeout: int = 10):
    """使用 curl 发送 GET 请求，返回 JSON 数据"""
    try:
        cmd = [utils.get_curl_path(), "-s", "--max-time", str(timeout), "--connect-timeout", "5", url]
        result = subprocess.check_output(cmd, stderr=subprocess.PIPE, startupinfo=STARTUPINFO)
        return orjson.loads(result)
    except Exception as e:
        log_message("ERROR", f"Curl 请求失败: {e}")
        return None


def get_work_info(rj_id: str):
    """获取作品详细信息"""
    rj_num = rj_id.replace("RJ", "").replace("rj", "")
    url = f"{config.API_ENDPOINT}/api/workInfo/{rj_num}"
    return request_by_curl(url)


def get_file_list(rj_id: str):
    """获取作品文件列表"""
    rj_num = rj_id.replace("RJ", "").replace("rj", "")
    url = f"{config.API_ENDPOINT}/api/tracks/{rj_num}?v=2"
    data = request_by_curl(url)
    if not data:
        return []

    files = []

    def traverse(items, current_path=""):
        """递归遍历文件树"""
        for item in items:
            path = f"{current_path}/{item['title']}" if current_path else item['title']
            if item["type"] == "folder":
                traverse(item.get("children", []), path)
            else:
                files.append({
                    "path": path,
                    "hash": item["hash"],
                    "size": item["size"],
                    "mediaDownloadUrl": item.get("mediaDownloadUrl"),
                    "mediaStreamUrl": item.get("mediaStreamUrl")
                })

    traverse(data if isinstance(data, list) else data.get("children", []))
    return files


# ============================================================
# 下载控制函数
# ============================================================

def stop_download(immediately=False):
    """停止下载任务"""
    global download_stop_signal, delete_partial_signal
    download_stop_signal = True
    delete_partial_signal = immediately
    with stats_lock:
        download_stats["stopped_by_user"] = True
    log_message("TASK", f"用户请求{'立即' if immediately else ''}停止下载")


def generate_rename_log(target_dir, rj_id, rename_list):
    """生成文件名修改记录文件"""
    if not rename_list:
        return
    base_path = target_dir.parent
    log_file = base_path / f"{rj_id}_重命名记录.txt"
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"ASMRip 文件名修改记录\n")
            f.write(f"RJ号: {rj_id}\n")
            f.write(f"总文件数: {len(rename_list)}\n")
            f.write(f"修改文件数: {len(rename_list)}\n\n")
            f.write(f"说明：由于文件名包含 Windows 不支持的全角字符，\n")
            f.write(f"程序已自动将其替换为下划线以确保下载成功。\n\n")
            f.write(f"--- 修改列表 ---\n")
            for original, new in rename_list:
                f.write(f"原名: {original}\n")
                f.write(f"新名: {new}\n\n")
        log_message("SYSTEM", f"已生成重命名日志: {log_file.name}")
    except Exception as e:
        log_message("ERROR", f"生成重命名日志失败: {e}")


# ============================================================
# 核心下载函数
# ============================================================

def download_single_file(file_info, target_dir, downloaded_size, total_selected_size, max_retries=5, retry_delay=5):
    """下载单个文件，支持重试"""
    original_path = file_info['path']

    # 清洗文件名（处理特殊字符）
    safe_parts = [utils.safe_path_part(p) for p in original_path.split('/')]
    safe_relative_path = pathlib.Path(*safe_parts)
    save_file = target_dir / safe_relative_path

    save_file.parent.mkdir(parents=True, exist_ok=True)

    # 记录文件名修改
    rename_info = None
    if str(safe_relative_path) != original_path:
        rename_info = (original_path, str(safe_relative_path))

    url = file_info.get('mediaDownloadUrl') or file_info.get('mediaStreamUrl')
    if not url:
        log_message("WARNING", f"跳过: 无有效下载链接 - {original_path}")
        return False, "无有效下载链接", rename_info

    # 检查文件是否已完整下载
    if save_file.exists() and save_file.stat().st_size == file_info['size']:
        log_message("TASK", f"跳过: 文件已存在且完整 - {original_path}")
        return True, None, rename_info

    # 删除不完整的文件
    if save_file.exists():
        save_file.unlink()

    curl_path = utils.get_curl_path()
    cmd = [curl_path, "-L", "-o", str(save_file), url]

    # 重试下载
    for attempt in range(max_retries):
        if download_stop_signal:
            if delete_partial_signal and save_file.exists():
                save_file.unlink()
            return False, "用户停止", rename_info

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=STARTUPINFO)

            # 读取进度输出
            while True:
                line = proc.stderr.readline()
                if not line:
                    break
                line_text = line.decode('utf-8', errors='ignore')
                # 解析 curl 输出的进度百分比
                percent_match = re.search(r'(\d+\.\d+%)', line_text)
                if percent_match:
                    current_percent = float(percent_match.group(1).replace('%', ''))
                    estimated_downloaded = file_info['size'] * (current_percent / 100)
                    get_progress()
                    with progress_lock:
                        current_progress["current_file_percent"] = f"{current_percent:.2f}%"
                        current_progress["current_filename"] = original_path
                    set_progress(
                        (downloaded_size + estimated_downloaded) / total_selected_size * 100,
                        f"{current_percent:.2f}%",
                        original_path,
                        downloaded_size + estimated_downloaded,
                        total_selected_size
                    )

            proc.wait()
            # 验证下载结果
            if proc.returncode == 0 and save_file.exists() and save_file.stat().st_size == file_info['size']:
                log_message("TASK", f"完成: {original_path}")
                return True, None, rename_info
            raise Exception(f"Curl 返回码: {proc.returncode}")

        except Exception as e:
            error_msg = str(e)
            log_message("WARNING", f"下载失败 (尝试 {attempt + 1}/{max_retries}): {original_path} - {error_msg}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    # 清理失败的文件
    if delete_partial_signal and save_file.exists():
        save_file.unlink()
    return False, f"下载失败: {error_msg}", rename_info


# ============================================================
# 下载工作线程
# ============================================================

def download_worker():
    """后台下载工作线程，持续从队列中获取任务并执行"""
    log_message("SYSTEM", f"下载线程已启动，监听端口 {config.PORT}...")

    while True:
        try:
            task = task_queue.get()
            if task is None:
                break

            # 初始化本次任务状态
            global download_stop_signal, delete_partial_signal, is_downloading
            download_stop_signal = False
            delete_partial_signal = False
            is_downloading = True
            reset_progress()

            # 标记有待显示的完成结果
            with stats_lock:
                download_stats["pending_finish"] = True

            rj_id = task['rj_id']
            files = task['files']
            base_path = pathlib.Path(task['save_path'])
            target_dir = base_path / f"RJ{rj_id.replace('RJ', '')}"
            target_dir.mkdir(parents=True, exist_ok=True)

            selected_files = files
            total_selected_size = sum(f['size'] for f in selected_files)
            total_files_count = len(selected_files)

            log_message("TASK", f"开始任务: {rj_id}")
            log_message("TASK", f"保存路径: {target_dir}")
            log_message("TASK", f"文件数量: {total_files_count} / 总大小: {utils.format_size(total_selected_size)}")

            with stats_lock:
                download_stats["total_files"] = total_files_count

            with progress_lock:
                current_progress["total_size"] = total_selected_size

            downloaded_size = 0
            success_count = 0
            failed_list = []
            rename_log = []

            # 遍历下载所有文件
            for i, file_info in enumerate(selected_files):
                if download_stop_signal:
                    log_message("TASK", "任务已停止")
                    break

                log_message("TASK", f"[{i + 1}/{total_files_count}] {file_info['path']}")

                success, reason, rename_info = download_single_file(
                    file_info, target_dir, downloaded_size, total_selected_size
                )

                if success:
                    downloaded_size += file_info['size']
                    success_count += 1
                    with progress_lock:
                        current_progress["downloaded_size"] = downloaded_size
                    set_progress(downloaded_size / total_selected_size * 100, 0, "", downloaded_size,
                                 total_selected_size)
                    if rename_info:
                        rename_log.append(rename_info)
                else:
                    failed_list.append((file_info['path'], reason))

            # 失败文件自动重试
            if failed_list and not download_stop_signal:
                log_message("WARNING", f"检测到 {len(failed_list)} 个文件失败，5秒后重试...")
                time.sleep(5)
                retry_failed = []
                for item in failed_list[:]:
                    file_info = next(f for f in selected_files if f['path'] == item[0])
                    if download_stop_signal:
                        break
                    success, reason, rename_info = download_single_file(
                        file_info, target_dir, downloaded_size, total_selected_size
                    )
                    if success:
                        downloaded_size += file_info['size']
                        success_count += 1
                        with progress_lock:
                            current_progress["downloaded_size"] = downloaded_size
                        set_progress(downloaded_size / total_selected_size * 100, 0, "", downloaded_size,
                                     total_selected_size)
                        failed_list.remove(item)
                        if rename_info:
                            rename_log.append(rename_info)
                    else:
                        retry_failed.append((file_info['path'], reason))
                failed_list = retry_failed

            # 任务完成，更新状态
            is_downloading = False
            set_progress(100 if downloaded_size == total_selected_size else downloaded_size / total_selected_size * 100,
                         0, "", downloaded_size, total_selected_size)

            with stats_lock:
                download_stats["success_files"] = success_count
                download_stats["failed_files"] = len(failed_list)
                download_stats["failed_list"] = failed_list
                download_stats["pending_finish"] = True

            # 生成重命名日志
            if rename_log:
                generate_rename_log(target_dir, rj_id, rename_log)

            # 输出最终结果
            if download_stop_signal:
                log_message("TASK", f"任务已手动停止: 成功 {success_count}/{total_files_count}")
            else:
                log_message("TASK", f"任务完成: 成功 {success_count}/{total_files_count}, 失败 {len(failed_list)}")

        except Exception as e:
            log_message("ERROR", f"工作线程异常: {e}")
            is_downloading = False


def start_worker_thread():
    """启动后台下载线程"""
    t = threading.Thread(target=download_worker, daemon=True)
    t.start()
    return t
