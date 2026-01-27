# ASMRip

ASMR 本地下载器 - 方便从 [https://asmr.one](https://asmr.one/)下载 ASMR 音频/视频内容。  
这是ASMRip下载器的Windows PC本地版，后续会推出服务器版。

## 特性

- 简洁的图形界面
- 系统托盘常驻运行
- 支持多种 ASMR 平台
- 自动保存下载记录

## 安装

### 方式一：直接运行（推荐）

下载 `ASMRip.exe`，双击即可运行，无需安装 Python。

### 方式二：从源码运行

```bash
# 1. 安装 Python 3.10+

# 2. 克隆仓库
git clone https://github.com/你的用户名/asmrdownloader.git
cd asmrdownloader

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行
python main.py
```

## 依赖

| 包名 | 用途 |
|------|------|
| Python 3.10+ | 运行环境 |
| curl | HTTP 请求工具（项目已内置） |
| Flask | Web 服务器 |
| orjson | JSON 解析 |
| pystray | 系统托盘图标 |
| Pillow | 图片处理 |

## 感谢与声明

感谢 [https://asmr.one](https://asmr.one/) 平台提供的优质 ASMR 内容。

本工具仅供学习交流使用，请合理使用，不要将本软件和下载的内容用于商业用途或传播。

### 许可证

本项目采用 AGPL-3.0-or-later 许可证开源。

Copyright (c) 2026 zimo <zimo@zmlll.top>

