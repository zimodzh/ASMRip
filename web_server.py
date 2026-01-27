# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 zimo <zimo@zmlll.top>
# SPDX-License-Identifier: AGPL-3.0-or-later

# Flask Web 服务器模块
# 提供 Web 界面 API 接口

from flask import Flask, request, jsonify, render_template_string, send_file
import urllib.request
import logging
import os

import config
import downloader
from shared import LOG_MESSAGES, save_log, log_message

# 初始化 Flask 应用
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 允许中文直接显示

# ============================================================
# 前端页面模板 (HTML + JavaScript + CSS)
# ============================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <link rel="icon" type="image/x-icon" href="favicon.ico">
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <title>ASMRip - ASMR 本地下载器 - zimo</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Segoe UI', Roboto, sans-serif; background-color: #f3f4f6; }
        .file-item:hover { background-color: #f9fafb; }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #f1f1f1; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        .progress-fill {
            background: linear-gradient(90deg, #8b5cf6 0%, #a78bfa 100%);
            transition: width 0.3s ease;
        }
    </style>
</head>
<body class="text-gray-800 h-screen flex flex-col">
    <!-- 顶部导航栏 -->
    <header class="bg-white shadow-sm p-4 flex justify-between items-center z-10">
        <div class="flex items-center gap-2">
            <div class="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold">Z</div>
            <h1 class="text-xl font-bold tracking-tight">ASMR 下载器 <span class="text-xs font-normal text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">Local</span></h1>
        </div>
        <div class="flex items-center gap-3">
            <div id="statusIndicator" class="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-500 transition-colors">空闲</div>
        </div>
    </header>

    <main class="flex-1 overflow-hidden flex flex-col p-6 gap-6">
        <!-- 搜索区域：输入 RJ 号 -->
        <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex gap-4 items-center">
            <input type="text" id="rjInput" placeholder="输入 RJ 号 (例如: RJ123456)" 
                   class="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
            <button onclick="fetchWorkInfo()" id="btnSearch"
                    class="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors shadow-sm flex-shrink-0">搜索</button>
            <button onclick="clearUI()" 
                    class="px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-colors flex-shrink-0">清除</button>
            <button onclick="exportLog()" 
                    class="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-colors shadow-sm flex-shrink-0">导出日志</button>
        </div>

        <!-- 下载进度条区域 -->
        <div id="progressArea" class="hidden bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div class="flex items-center gap-3 mb-2">
                <span id="progressFile" class="text-sm font-medium text-gray-700 truncate flex-1"></span>
                <span id="progressPercent" class="text-lg font-mono font-bold text-purple-600">0.00%</span>
            </div>
            <div class="h-6 bg-gray-200 rounded-full overflow-hidden relative">
                <div id="progressBar" class="progress-fill h-full absolute left-0 top-0 rounded-full" style="width: 0%"></div>
            </div>
            <div class="mt-2 flex justify-between text-sm text-gray-500">
                <div class="flex gap-4">
                    <span id="currentFileProgress">等待开始...</span>
                    <span id="speedDisplay">0.00 KB/s</span>
                </div>
                <span id="totalProgress">0.00%</span>
            </div>
        </div>

        <!-- 作品信息与文件列表区域 -->
        <div id="workArea" class="hidden flex-1 flex gap-6 overflow-hidden">
            <!-- 左侧：作品详情 -->
            <div class="w-1/3 bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col gap-4 overflow-y-auto">
                <div class="w-full bg-gray-100 rounded-lg overflow-hidden relative shadow-sm flex-shrink-0">
                    <img id="workCover" src="" alt="封面" class="w-full h-auto object-contain block hidden">
                    <span id="coverPlaceholder" class="text-gray-400 text-sm absolute inset-0 flex items-center justify-center">加载封面中...</span>
                </div>

                <h2 id="workTitle" class="text-xl font-bold leading-tight"></h2>

                <div class="text-sm text-gray-600 space-y-2">
                    <p><span class="font-medium">ID:</span> <span id="workId"></span></p>
                    <p><span class="font-medium">社团:</span> <span id="workCircle"></span></p>
                    <p><span class="font-medium">总大小:</span> <span id="workSize" class="font-mono text-indigo-600"></span></p>
                </div>

                <hr class="border-gray-100">

                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">保存路径</label>
                    <div class="flex gap-2">
                        <input type="text" id="savePath" value="./Download" readonly 
                               class="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded text-sm text-gray-600">
                        <button onclick="alert('请在启动程序的目录下手动修改 Download 文件夹位置，或使用默认路径。')" 
                                class="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded text-sm transition">设置</button>
                    </div>
                </div>

                <div class="mt-auto pt-4">
                    <div class="flex gap-2">
                        <button onclick="startDownload()" id="btnStart"
                                class="flex-1 py-3 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg shadow-lg shadow-green-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed">开始下载</button>
                        <button onclick="confirmStop()" id="btnStop" disabled
                                class="flex-1 py-3 bg-red-500 hover:bg-red-600 text-white font-bold rounded-lg shadow-lg shadow-red-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed">停止下载</button>
                    </div>
                </div>
            </div>

            <!-- 右侧：文件列表 -->
            <div class="flex-1 bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col overflow-hidden">
                <div class="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
                    <h3 class="font-bold text-gray-700">文件列表</h3>
                    <div class="flex gap-2 text-sm">
                        <button onclick="toggleAll(true)" class="text-indigo-600 hover:underline">全选</button>
                        <span class="text-gray-300">|</span>
                        <button onclick="toggleAll(false)" class="text-indigo-600 hover:underline">全不选</button>
                    </div>
                </div>
                <div id="fileList" class="flex-1 overflow-y-auto p-2 space-y-1"></div>
            </div>
        </div>
    </main>

    <!-- 停止确认弹窗 -->
    <div id="stopModal" class="fixed inset-0 bg-black/50 z-50 hidden flex items-center justify-center">
        <div class="bg-white rounded-2xl p-8 max-w-md w-full text-center shadow-2xl">
            <h3 class="text-xl font-bold text-gray-900 mb-4">确认停止</h3>
            <p class="text-gray-500 mb-6">确定要停止下载吗？未完成的文件将被删除。</p>
            <div class="flex gap-3">
                <button onclick="closeStopModal()" class="flex-1 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg">取消</button>
                <button onclick="stopDownload()" class="flex-1 py-3 bg-red-500 hover:bg-red-600 text-white font-bold rounded-lg">确认停止</button>
            </div>
        </div>
    </div>

    <!-- 下载开始提示弹窗 -->
    <div id="startModal" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 hidden flex items-center justify-center">
        <div class="bg-white rounded-2xl py-8 px-6 max-w-md w-full text-center shadow-2xl">
            <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
            </div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">任务已开始</h2>
            <p class="text-gray-500 mb-2">下载正在后台运行。</p>
            <p class="text-gray-500 mb-6">请点击右下角托盘图标 -> "显示日志窗口" 查看进度。</p>
            <button onclick="closeStartModal()" class="w-full py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors">
                好的，我知道了
            </button>
        </div>
    </div>

    <!-- 下载完成弹窗 -->
    <div id="finishModal" class="fixed inset-0 bg-black/50 z-50 hidden flex items-center justify-center">
        <div class="bg-white rounded-2xl p-8 max-w-md w-full text-center shadow-2xl">
            <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
            </div>
            <h3 class="text-xl font-bold text-gray-900 mb-4">下载完成</h3>
            <div class="text-left text-sm text-gray-600 space-y-2 mb-4">
                <p><span class="font-medium">总计文件:</span> <span id="finishTotal">0</span></p>
                <p class="text-green-600"><span class="font-medium">成功:</span> <span id="finishSuccess">0</span></p>
                <p class="text-red-600"><span class="font-medium">失败:</span> <span id="finishFailed">0</span></p>
            </div>
            <div id="finishFailedList" class="text-left text-xs text-red-500 max-h-32 overflow-y-auto mb-4 hidden">
                <p class="font-medium mb-1">失败列表:</p>
            </div>
            <button onclick="closeFinishModal()" class="w-full py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg">确定</button>
        </div>
    </div>

    <!-- JavaScript 交互逻辑 -->
    <script>
        let currentFiles = [];       // 当前加载的文件列表
        let progressTimer = null;    // 进度更新定时器

        // HTML 转义，防止 XSS 攻击
        function escapeHtml(text) {
            if (!text) return "";
            return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
        }

        // 格式化网速显示
        function formatSpeed(bytesPerSecond) {
            if (bytesPerSecond === 0) return '0.00 B/s';
            const k = 1024;
            if (bytesPerSecond < k) {
                return bytesPerSecond.toFixed(2) + ' B/s';
            } else if (bytesPerSecond < k * k) {
                return (bytesPerSecond / k).toFixed(2) + ' KB/s';
            } else if (bytesPerSecond < k * k * k) {
                return (bytesPerSecond / k / k).toFixed(2) + ' MB/s';
            } else {
                return (bytesPerSecond / k / k / k).toFixed(2) + ' GB/s';
            }
        }

        // 获取作品信息
        async function fetchWorkInfo() {
            const rjId = document.getElementById('rjInput').value.trim().toUpperCase();
            if (!rjId.startsWith('RJ')) { alert('请输入有效的 RJ 号'); return; }

            const btn = document.getElementById('btnSearch');
            btn.disabled = true;
            btn.innerText = '加载中...';

            try {
                const res = await fetch(`/api/info/${rjId}`);
                const data = await res.json();
                if (data.error) { alert(data.error); return; }

                // 显示封面
                document.getElementById('workCover').src = `/api/image/${rjId}`;
                document.getElementById('workCover').onload = () => {
                    document.getElementById('workCover').classList.remove('hidden');
                    document.getElementById('coverPlaceholder').classList.add('hidden');
                };

                // 显示作品信息
                document.getElementById('workTitle').innerText = data.title;
                document.getElementById('workId').innerText = data.id;
                document.getElementById('workCircle').innerText = data.name;
                document.getElementById('workArea').classList.remove('hidden');

                // 获取文件列表
                await fetchFileList(rjId);
            } catch (e) { alert('网络请求失败'); console.error(e); }

            btn.disabled = false;
            btn.innerText = '搜索';
        }

        // 获取文件列表
        async function fetchFileList(rjId) {
            const res = await fetch(`/api/files/${rjId}`);
            const data = await res.json();
            currentFiles = data.files;
            renderFiles(currentFiles);
        }

        // 渲染文件列表
        function renderFiles(files) {
            const container = document.getElementById('fileList');
            container.innerHTML = '';
            let totalSize = 0;
            files.forEach(f => totalSize += f.size);
            document.getElementById('workSize').innerText = formatSize(totalSize);

            files.forEach((file, index) => {
                const div = document.createElement('div');
                div.className = 'file-item flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50';
                div.innerHTML = `
                    <input type="checkbox" id="file-${index}" checked class="w-5 h-5 text-indigo-600 rounded">
                    <div class="flex-1 min-w-0">
                        <div class="text-sm font-medium text-gray-900 truncate" title="${escapeHtml(file.path)}">${escapeHtml(file.path)}</div>
                    </div>
                    <div class="text-xs text-gray-500 font-mono w-20 text-right">${formatSize(file.size)}</div>
                `;
                container.appendChild(div);
            });
        }

        // 格式化文件大小
        function formatSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        // 全选/取消全选
        function toggleAll(checked) {
            document.querySelectorAll('#fileList input[type="checkbox"]').forEach(cb => cb.checked = checked);
        }

        // 开始下载
        async function startDownload() {
            const checkboxes = document.querySelectorAll('#fileList input[type="checkbox"]:checked');
            if (checkboxes.length === 0) { alert('请至少选择一个文件'); return; }

            const selectedFiles = [];
            checkboxes.forEach((cb, i) => { if (cb.checked) selectedFiles.push(currentFiles[i]); });

            const rjId = document.getElementById('workId').innerText;
            const savePath = document.getElementById('savePath')?.value || './Download';

            const res = await fetch('/api/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ rj_id: rjId, files: selectedFiles, save_path: savePath })
            });

            if (!res.ok) { alert('下载启动失败'); return; }

            // 显示开始提示弹窗
            document.getElementById('startModal').classList.remove('hidden');
            document.getElementById('progressArea').classList.remove('hidden');

            // 启动进度更新定时器
            if (progressTimer) clearInterval(progressTimer);
            progressTimer = setInterval(updateProgress, 1000);
        }

        // 确认停止下载弹窗
        function confirmStop() { document.getElementById('stopModal').classList.remove('hidden'); }
        function closeStopModal() { document.getElementById('stopModal').classList.add('hidden'); }
        function closeStartModal() { document.getElementById('startModal').classList.add('hidden'); }

        // 立即停止下载
        async function stopDownload() {
            closeStopModal();
            await fetch('/api/stop_immediate', { method: 'POST' });
            if (progressTimer) clearInterval(progressTimer);
            progressTimer = null;
            document.getElementById('progressArea').classList.add('hidden');
            document.getElementById('progressBar').style.width = '0%';
            document.getElementById('progressPercent').innerText = '0.00%';
        }

        // 更新下载进度显示
        async function updateProgress() {
            try {
                const res = await fetch('/api/progress');
                const data = await res.json();

                if (data.total_percent !== undefined && data.total_percent > 0) {
                    document.getElementById('progressBar').style.width = data.total_percent + '%';
                    document.getElementById('progressPercent').innerText = data.total_percent.toFixed(2) + '%';
                    document.getElementById('currentFileProgress').innerText = data.current_filename || '下载中...';

                    // 网速转换与显示
                    const speedBytes = (data.speed || 0) * 1024;
                    document.getElementById('speedDisplay').innerText = formatSpeed(speedBytes);
                    document.getElementById('totalProgress').innerText = '总进度: ' + data.total_percent.toFixed(2) + '%';
                }
            } catch (e) { console.error(e); }
        }

        // 检查下载状态
        async function checkStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();

                const startBtn = document.getElementById('btnStart');
                const stopBtn = document.getElementById('btnStop');
                const indicator = document.getElementById('statusIndicator');

                if (data.downloading) {
                    // 下载中状态
                    startBtn.disabled = true;
                    startBtn.classList.add('opacity-50', 'cursor-not-allowed');
                    stopBtn.disabled = false;
                    stopBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                    indicator.className = 'px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-600';
                    indicator.innerText = '下载中';
                } else {
                    // 空闲状态
                    startBtn.disabled = false;
                    startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                    stopBtn.disabled = true;
                    stopBtn.classList.add('opacity-50', 'cursor-not-allowed');
                    indicator.className = 'px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-500';
                    indicator.innerText = '空闲';

                    if (progressTimer) {
                        clearInterval(progressTimer);
                        progressTimer = null;
                    }

                    // 检查是否刚完成
                    const finishRes = await fetch('/api/finish_check');
                    const finishData = await finishRes.json();
                    if (finishData.just_finished) {
                        showFinishModal(finishData);
                    }
                }
            } catch (e) { console.error(e); }
        }

        // 显示下载完成弹窗
        function showFinishModal(data) {
            document.getElementById('finishTotal').innerText = data.total;
            document.getElementById('finishSuccess').innerText = data.success;
            document.getElementById('finishFailed').innerText = data.failed;

            const failedList = document.getElementById('finishFailedList');
            if (data.failed_list && data.failed_list.length > 0) {
                failedList.classList.remove('hidden');
                failedList.innerHTML = '<p class="font-medium mb-1">失败列表:</p>' + 
                    data.failed_list.map(f => `<p>• ${f[0]}: ${f[1]}</p>`).join('');
            } else {
                failedList.classList.add('hidden');
            }

            document.getElementById('finishModal').classList.remove('hidden');
        }

        // 关闭完成弹窗
        function closeFinishModal() {
            document.getElementById('finishModal').classList.add('hidden');
            document.getElementById('progressArea').classList.add('hidden');
            document.getElementById('progressBar').style.width = '0%';
            document.getElementById('progressPercent').innerText = '0.00%';
        }

        // 清空界面
        function clearUI() {
            document.getElementById('rjInput').value = '';
            document.getElementById('workArea').classList.add('hidden');
            document.getElementById('fileList').innerHTML = '';
            document.getElementById('progressArea').classList.add('hidden');
            document.getElementById('progressBar').style.width = '0%';
            currentFiles = [];
            if (progressTimer) clearInterval(progressTimer);
            progressTimer = null;
        }

        // 导出日志
        async function exportLog() {
            window.open('/api/export_log', '_blank');
        }

        // 定期检查状态
        setInterval(checkStatus, 1000);
    </script>
</body>
</html>
"""


# ============================================================
# Flask API 接口路由
# ============================================================

# 主页
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


# 获取作品信息
@app.route('/api/info/<rj_id>')
def get_info(rj_id):
    data = downloader.get_work_info(rj_id)
    if data: return jsonify(data)
    return jsonify({"error": "获取作品信息失败"})


# 获取文件列表
@app.route('/api/files/<rj_id>')
def get_files(rj_id):
    files = downloader.get_file_list(rj_id)
    return jsonify({"files": files})


# 获取封面图片
@app.route('/api/image/<rj_id>')
def get_cover_image(rj_id):
    try:
        info = downloader.get_work_info(rj_id)
        if not info: return "No Info", 404
        cover_url = info.get('mainCoverUrl') or info.get('thumbnailCoverUrl')
        if not cover_url: return "No Cover URL found", 404

        # 代理请求封面图片
        req = urllib.request.Request(cover_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            img_data = response.read()
        return app.response_class(img_data, mimetype='image/jpeg')
    except Exception as e:
        log_message("ERROR", f"获取封面失败: {e}")
        return "Error", 500


# 提交下载任务
@app.route('/api/start', methods=['POST'])
def start_download_api():
    payload = request.json
    downloader.task_queue.put(payload)
    log_message("TASK", f"下载任务已提交: {payload['rj_id']}, 文件数: {len(payload['files'])}")
    return jsonify({"status": "queued"})


# 停止下载（温和）
@app.route('/api/stop', methods=['POST'])
def stop_download_api():
    downloader.stop_download(immediately=False)
    return jsonify({"status": "stop_signal_sent"})


# 立即停止下载
@app.route('/api/stop_immediate', methods=['POST'])
def stop_download_immediate_api():
    downloader.stop_download(immediately=True)
    return jsonify({"status": "stop_immediate_sent"})


# 获取下载状态
@app.route('/api/status')
def get_status():
    return jsonify({"downloading": downloader.get_status()})


# 获取下载进度
@app.route('/api/progress')
def get_progress():
    progress = downloader.get_progress()
    return jsonify(progress)


# 检查是否刚完成下载
@app.route('/api/finish_check')
def finish_check():
    """查询下载是否刚完成，如果是则返回结果"""
    if not downloader.is_downloading:
        with downloader.stats_lock:
            # 只有 pending_finish 为 True 时才返回结果
            if downloader.download_stats.get("pending_finish", False):
                result = {
                    "just_finished": True,
                    "total": downloader.download_stats["total_files"],
                    "success": downloader.download_stats["success_files"],
                    "failed": downloader.download_stats["failed_files"],
                    "failed_list": downloader.download_stats["failed_list"],
                    "stopped_by_user": downloader.download_stats.get("stopped_by_user", False)
                }
                # 清除标志，避免重复显示
                downloader.download_stats["pending_finish"] = False
                return jsonify(result)
    return jsonify({"just_finished": False})


# 导出日志文件
@app.route('/api/export_log')
def export_log():
    try:
        filename = save_log("手动")
        log_file = config.LOG_DIR / filename
        if log_file.exists():
            return send_file(str(log_file), as_attachment=True, download_name=filename, mimetype='text/plain')
        return "日志文件不存在", 404
    except Exception as e:
        log_message("ERROR", f"导出日志失败: {e}")
        return f"导出日志失败: {e}", 500


# 启动 Flask 服务
def run_flask():
    # 抑制 werkzeug 日志
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    log_message("SYSTEM", f"Flask 服务启动: http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, use_reloader=False, threaded=True)
