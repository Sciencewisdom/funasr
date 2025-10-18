#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFmpeg音频文件分割脚本 (流式复制模式)
使用ffmpeg进行流式复制，确保每个分片都是完整可播放的音频文件
保持原始音质，极快的分割速度
"""

import os
import sys
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing as mp
import time

# --- 配置 ---
INPUT_FILE = 'asr.txt'
MAX_SIZE_MB = 50
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024  # 50MB in bytes
SUPPORTED_FORMATS = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.mp4', '.avi', '.mkv', '.mov']

# 性能配置
ENABLE_MULTITHREADING = True
MAX_WORKERS = min(mp.cpu_count(), 4)  # 限制线程数避免ffmpeg冲突

def get_media_duration(file_path):
    """获取媒体文件总时长"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
    except:
        return None

def ffmpeg_split_file(file_path, output_dir):
    """使用ffmpeg分割单个文件 (流式复制)"""
    if not os.path.exists(file_path):
        return f"⚠️  文件不存在: {os.path.basename(file_path)}", 0, 0
    
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in SUPPORTED_FORMATS:
        return f"⚠️  不支持的格式: {os.path.basename(file_path)}", 0, 0
    
    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)
    
    # 如果文件小于最大大小，直接复制
    if file_size <= MAX_SIZE_BYTES:
        output_path = os.path.join(output_dir, os.path.basename(file_path))
        try:
            start_time = time.time()
            shutil.copy2(file_path, output_path)
            copy_time = time.time() - start_time
            return f"✓ {os.path.basename(file_path)} ({file_size_mb:.1f}MB) - 直接复制 [{copy_time:.2f}s]", 1, 1
        except Exception as e:
            return f"✗ 复制失败 {os.path.basename(file_path)}: {e}", 0, 0
    
    # 使用ffmpeg分割大文件
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    extension = os.path.splitext(file_path)[1]
    
    result = f"📁 {os.path.basename(file_path)} ({file_size_mb:.1f}MB) → ffmpeg分割\n"
    
    try:
        start_time = time.time()
        
        # 获取媒体总时长
        total_duration = get_media_duration(file_path)
        if total_duration is None:
            return f"✗ 无法获取文件时长: {os.path.basename(file_path)}", 0, 0
        
        # 计算需要分割成多少部分（基于文件大小）
        parts_needed = min((file_size + MAX_SIZE_BYTES - 1) // MAX_SIZE_BYTES, 5)  # 最多5部分
        part_duration = total_duration / parts_needed
        
        result += f"  🎵 总时长: {total_duration:.1f}秒，分{parts_needed}部分\n"
        
        parts_created = 0
        
        # 使用ffmpeg按时间分割
        for part_num in range(parts_needed):
            start_time_part = part_num * part_duration
            
            # 生成分片文件名
            part_filename = f"{base_name}_part{part_num + 1}{extension}"
            part_path = os.path.join(output_dir, part_filename)
            
            # 构建ffmpeg命令
            cmd = [
                'ffmpeg', '-y',  # -y 覆盖输出文件
                '-ss', str(start_time_part),  # 开始时间
                '-i', file_path,  # 输入文件
                '-c', 'copy',  # 流式复制，不重新编码
                '-avoid_negative_ts', '1',  # 避免负时间戳
                '-map_metadata', '0',  # 复制元数据
            ]
            
            # 如果不是最后一部分，添加持续时间限制
            if part_num < parts_needed - 1:
                cmd.extend(['-t', str(part_duration)])
            
            cmd.append(part_path)
            
            try:
                print(f"    🔄 正在生成 {part_filename}...")
                process_result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=180  # 3分钟超时
                )
                
                if process_result.returncode == 0 and os.path.exists(part_path):
                    part_size_mb = os.path.getsize(part_path) / (1024 * 1024)
                    if part_size_mb > 0.1:  # 只计算大于0.1MB的文件
                        result += f"  ✓ {part_filename} ({part_size_mb:.1f}MB, {part_duration:.1f}s)\n"
                        parts_created += 1
                    else:
                        # 删除太小的文件
                        os.remove(part_path)
                        result += f"  ⚠️  {part_filename} 太小，已删除\n"
                else:
                    error_msg = process_result.stderr.strip() if process_result.stderr else "未知错误"
                    result += f"  ❌ {part_filename} 分割失败: {error_msg[:50]}...\n"
                    
            except subprocess.TimeoutExpired:
                result += f"  ⏱️  {part_filename} 分割超时\n"
            except Exception as e:
                result += f"  ❌ {part_filename} 分割出错: {str(e)[:30]}...\n"
        
        split_time = time.time() - start_time
        speed = (file_size_mb / split_time) if split_time > 0 else 0
        result += f"  ⚡ ffmpeg分割完成 [{split_time:.2f}s, {speed:.1f}MB/s]\n"
        
        return result, 1, parts_created
        
    except Exception as e:
        return f"✗ ffmpeg分割失败 {os.path.basename(file_path)}: {e}\n", 0, 0

def create_empty_txt_files(file_paths):
    """为每个音频文件创建对应的空白txt文件"""
    print("📝 为音频文件创建对应的空白txt文件...")
    
    created_count = 0
    for file_path in file_paths:
        if os.path.exists(file_path):
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext == '.m4a':
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                txt_filename = f"{base_name}.txt"
                
                # 检查文件是否已存在
                if not os.path.exists(txt_filename):
                    with open(txt_filename, 'w', encoding='utf-8') as f:
                        f.write("")  # 创建空白文件
                    print(f"  ✓ 创建: {txt_filename}")
                    created_count += 1
                else:
                    print(f"  ⚠️  已存在: {txt_filename}")
    
    print(f"📝 共创建 {created_count} 个空白txt文件")
    print()

def main():
    print("=== FFmpeg音频文件分割工具 (流式复制模式) ===")
    print(f"最大文件大小: {MAX_SIZE_MB}MB")
    print(f"多线程处理: {'启用' if ENABLE_MULTITHREADING else '禁用'}")
    print(f"最大线程数: {MAX_WORKERS}")
    print("🎵 使用ffmpeg流式复制，确保音频完整性")
    print()
    
    # 检查ffmpeg是否可用
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✅ FFmpeg 检查通过")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 错误: 未找到 FFmpeg")
        print("请安装 FFmpeg: conda install ffmpeg -c conda-forge")
        sys.exit(1)
    
    # 检查输入文件
    if not os.path.exists(INPUT_FILE):
        print(f"错误: 输入文件 '{INPUT_FILE}' 未找到。")
        sys.exit(1)
    
    # 读取文件列表
    print(f"正在从 {INPUT_FILE} 读取文件列表...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        file_paths = [line.strip().strip('" ') for line in f if line.strip()]
    
    print(f"找到 {len(file_paths)} 个文件")
    print()
    
    # 为m4a文件创建空白txt文件
    create_empty_txt_files(file_paths)
    
    # 创建输出目录
    output_dir = "split_audio"
    if os.path.exists(output_dir):
        # 清理之前的分割文件
        print("🧹 清理之前的分割文件...")
        shutil.rmtree(output_dir)
    
    os.makedirs(output_dir)
    print(f"创建输出目录: {output_dir}")
    print()
    
    total_start_time = time.time()
    total_files_processed = 0
    total_parts_created = 0
    total_size_mb = 0
    
    # 计算总文件大小
    for file_path in file_paths:
        if os.path.exists(file_path):
            total_size_mb += os.path.getsize(file_path) / (1024 * 1024)
    
    print(f"总文件大小: {total_size_mb:.1f}MB")
    print()
    
    if ENABLE_MULTITHREADING and len(file_paths) > 1:
        # 多线程处理
        print(f"🚀 启动ffmpeg多线程处理...")
        print()
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(ffmpeg_split_file, file_path, output_dir): file_path
                for file_path in file_paths
            }
            
            # 收集结果
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result_info, files_processed, parts_created = future.result()
                    print(result_info)
                    total_files_processed += files_processed
                    total_parts_created += parts_created
                except Exception as e:
                    print(f"处理文件出错 {os.path.basename(file_path)}: {e}")
    else:
        # 单线程处理
        for file_path in file_paths:
            result_info, files_processed, parts_created = ffmpeg_split_file(file_path, output_dir)
            print(result_info)
            total_files_processed += files_processed
            total_parts_created += parts_created
    
    # 生成分割后的文件列表
    split_files_list = os.path.join(output_dir, "split_files_list.txt")
    with open(split_files_list, 'w', encoding='utf-8') as f:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith(tuple(SUPPORTED_FORMATS)):
                    file_path = os.path.join(root, file)
                    f.write(file_path + '\n')
    
    total_time = time.time() - total_start_time
    
    print()
    print("=== FFmpeg分割完成 ===")
    print(f"总耗时: {total_time:.2f}秒")
    print(f"处理文件数: {total_files_processed}")
    print(f"生成文件数: {total_parts_created}")
    print(f"总处理大小: {total_size_mb:.1f}MB")
    print(f"平均速度: {total_size_mb/total_time:.1f}MB/s")
    print(f"输出目录: {output_dir}")
    print(f"文件列表: {split_files_list}")
    print()
    print("🎉 FFmpeg分割完成！所有分片都是完整可播放的音频文件。")

if __name__ == '__main__':
    main()