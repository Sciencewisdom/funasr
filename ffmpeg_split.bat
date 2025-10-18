@echo off
chcp 65001 >nul
echo === FFmpeg音频文件分割工具 (流式复制模式) ===
echo.
echo 🎵 使用ffmpeg进行专业音频分割
echo ⚡ 流式复制，保持原始音质
echo 🎯 确保每个分片都完整可播放
echo.
echo 检查FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到FFmpeg，正在安装...
    conda install ffmpeg -c conda-forge -y
    echo ✅ FFmpeg安装完成
)
echo.
python ffmpeg_split_audio.py
echo.
pause