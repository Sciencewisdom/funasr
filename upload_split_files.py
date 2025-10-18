#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分割文件上传助手
帮助按顺序上传分割后的音频文件到转录服务
"""

import os
import sys
import time
from dashscope.audio.asr import Transcription
from http import HTTPStatus
import requests
import json

# --- 配置 ---
SPLIT_FILES_LIST = "split_audio/split_files_list.txt"
MAX_CONCURRENT_UPLOADS = 3  # 同时上传的文件数限制

def upload_file_to_service(file_path):
    """上传单个文件到转录服务"""
    try:
        filename = os.path.basename(file_path)
        print(f"📤 正在上传: {filename}")
        
        # 使用之前的上传逻辑，但优化了网络设置
        session = requests.Session()
        session.trust_env = False
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 尝试多个上传服务
        services = [
            {'name': '0x0.st', 'url': 'http://0x0.st', 'method': 'POST'},
            {'name': 'transfer.sh', 'url': 'https://transfer.sh', 'method': 'PUT'},
        ]
        
        for service in services:
            try:
                print(f"  🔄 尝试 {service['name']}...")
                
                with open(file_path, 'rb') as f:
                    if service['method'] == 'POST':
                        response = session.post(
                            service['url'],
                            files={'file': (filename, f, 'application/octet-stream')},
                            timeout=30
                        )
                    else:  # PUT
                        response = session.put(
                            f"{service['url']}/{filename}",
                            data=f,
                            timeout=30
                        )
                
                if response.status_code == 200:
                    url = response.text.strip()
                    if url.startswith('http'):
                        print(f"  ✅ 上传成功: {url}")
                        return url
                        
            except Exception as e:
                print(f"  ❌ {service['name']} 失败: {str(e)[:50]}...")
                continue
        
        print(f"  ❌ 所有上传服务都失败了")
        return None
        
    except Exception as e:
        print(f"❌ 上传 {filename} 时出错: {e}")
        return None

def transcribe_file(file_url, original_filename):
    """转录单个文件"""
    try:
        print(f"🎵 开始转录: {original_filename}")
        
        task_response = Transcription.async_call(
            model='fun-asr',
            file_urls=[file_url]
        )
        
        if task_response and task_response.status_code == HTTPStatus.OK:
            task_id = task_response.output.task_id
            print(f"  📋 任务ID: {task_id}")
            
            # 等待完成
            transcribe_response = Transcription.wait(task=task_id)
            
            if transcribe_response and transcribe_response.status_code == HTTPStatus.OK:
                results = transcribe_response.output.get('results', [])
                if results and results[0].get('subtask_status') == 'SUCCEEDED':
                    transcription_url = results[0].get('transcription_url')
                    
                    # 获取转录结果
                    response = requests.get(transcription_url, timeout=30)
                    if response.status_code == 200:
                        transcript_data = response.json()
                        if 'sentences' in transcript_data:
                            full_text = "".join([s['text'] for s in transcript_data.get('sentences', [])])
                            
                            # 保存结果
                            output_filename = f"{os.path.splitext(original_filename)[0]}_转录结果.txt"
                            with open(output_filename, 'w', encoding='utf-8') as out_f:
                                out_f.write(full_text)
                            
                            print(f"  ✅ 转录完成: {output_filename}")
                            return True
                        else:
                            print(f"  ❌ 转译结果格式错误")
                    else:
                        print(f"  ❌ 获取转录结果失败: {response.status_code}")
                else:
                    error_msg = results[0].get('message', '未知错误') if results else '未知错误'
                    print(f"  ❌ 转录失败: {error_msg}")
            else:
                print(f"  ❌ 等待转录结果失败")
        else:
            print(f"  ❌ 提交转录任务失败")
            
    except Exception as e:
        print(f"❌ 转录 {original_filename} 时出错: {e}")
    
    return False

def main():
    print("=== 分割文件上传转录助手 ===")
    print()
    
    # 检查分割文件列表
    if not os.path.exists(SPLIT_FILES_LIST):
        print(f"错误: 分割文件列表 '{SPLIT_FILES_LIST}' 未找到。")
        print("请先运行 fast_split_audio.py 生成分割文件。")
        sys.exit(1)
    
    # 读取分割文件列表
    print(f"📂 正在读取分割文件列表...")
    with open(SPLIT_FILES_LIST, 'r', encoding='utf-8') as f:
        file_paths = [line.strip() for line in f if line.strip()]
    
    print(f"找到 {len(file_paths)} 个分割文件")
    print()
    
    # 统计信息
    success_count = 0
    total_count = len(file_paths)
    
    # 处理每个文件
    for i, file_path in enumerate(file_paths, 1):
        if not os.path.exists(file_path):
            print(f"⚠️  文件不存在，跳过: {file_path}")
            continue
        
        filename = os.path.basename(file_path)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        print(f"📁 [{i}/{total_count}] 处理: {filename} ({file_size_mb:.1f}MB)")
        
        # 上传文件
        file_url = upload_file_to_service(file_path)
        if not file_url:
            print(f"❌ 上传失败，跳过此文件")
            print()
            continue
        
        # 转录文件
        if transcribe_file(file_url, filename):
            success_count += 1
        
        print(f"📊 进度: {success_count}/{i} 成功")
        print("-" * 50)
        print()
        
        # 短暂休息避免频率限制
        time.sleep(2)
    
    print("=== 处理完成 ===")
    print(f"总文件数: {total_count}")
    print(f"成功转录: {success_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    print()
    print("🎉 转录结果已保存为对应的 .txt 文件")

if __name__ == '__main__':
    main()