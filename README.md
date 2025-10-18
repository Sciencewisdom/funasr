# 音频转录工具集

## 📁 文件说明

### 🎵 FFmpeg音频分割工具
- **`ffmpeg_split.bat`** - FFmpeg音频分割批处理工具
- **`ffmpeg_split_audio.py`** - FFmpeg流式分割脚本（推荐）

### 📤 API转录工具
- **`run_transcription_local.py`** - 本地文件转录脚本（Plan C方案）
- **`upload_split_files.py`** - 分割文件批量上传转录脚本
- **`funasr_transcriber.py`** - 通用转录器
- **`start.bat`** - 一键启动转录脚本

### ⚙️ 配置工具
- **`setup_api_key.py`** - API密钥配置工具
- **`asr.txt`** - 待处理音频文件列表

## 🚀 使用流程

### 1. 音频分割（推荐）
```bash
# 使用FFmpeg进行专业级音频分割
ffmpeg_split.bat
```

### 2. 转录处理

#### 方案A：直接转录原文件
```bash
# 直接转录asr.txt中的文件
start.bat
```

#### 方案B：转录分割后的文件
```bash
# 先分割文件
ffmpeg_split.bat

# 然后转录分割后的文件
upload_split.bat
```

## ✨ 特性

### FFmpeg分割
- ⚡ 流式复制，保持原始音质
- 🎵 确保每个分片完整可播放
- 📊 智能均匀分割，无0MB文件
- 🚀 多线程并行处理

### API转录
- 🌐 支持多种文件托管服务
- 🔄 自动重试机制
- 📝 自动保存转录结果
- ⚡ 批量处理能力

## 📋 输出

- 分割文件保存在 `split_audio/` 目录
- 转录结果保存为对应的 `.txt` 文件
- 分割文件列表：`split_audio/split_files_list.txt`

## 🔧 环境要求

- Python 3.7+
- FFmpeg（自动安装）
- 阿里云DashScope API Key

## 📝 注意事项

1. 确保已配置API密钥
2. 大文件建议先分割再转录
3. 转录过程需要网络连接
4. 分割后的文件保持原始音质