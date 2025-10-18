import os
import sys
import requests
import json
from http import HTTPStatus
from dashscope.audio.asr import Transcription

# --- 配置 ---
INPUT_FILE = 'asr.txt'
TRANSFER_URL_BASE = 'https://transfer.sh/'

def upload_file_to_temp_service(file_path):
    """上传单个文件到临时文件托管服务 (多备用方案)"""
    filename = os.path.basename(file_path)
    print(f"正在上传: {filename} ...", end="", flush=True)
    
    # 配置优化的网络设置
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    # 禁用代理，避免本地代理干扰
    session.trust_env = False  # 禁用环境变量中的代理设置
    
    # 多个备用服务列表
    services = [
        {
            'name': '0x0.st',
            'url': 'http://0x0.st',
            'method': 'POST',
            'files_key': 'file'
        },
        {
            'name': 'file.io',
            'url': 'https://file.io',
            'method': 'POST',
            'files_key': 'file'
        },
        {
            'name': 'keep.sh',
            'url': 'https://keep.sh',
            'method': 'PUT',
            'files_key': None
        }
    ]
    
    for service in services:
        try:
            print(f"\n  尝试 {service['name']}...", end="", flush=True)
            
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
                    print(f" 成功! URL: {url}")
                    return url
                    
        except Exception as e:
            print(f" 失败: {str(e)[:50]}...", end="", flush=True)
            continue
    
    print(f"\n  所有服务都尝试失败")
    return None

def fetch_transcription_result(url):
    try:
        session = requests.Session()
        session.trust_env = False  # 禁用环境变量中的代理设置
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"获取转录结果失败: {e}")
        return None

def main():
    if not os.path.exists(INPUT_FILE): print(f"错误: 输入文件 '{INPUT_FILE}' 未找到。"); sys.exit(1)

    print(f"STEP 1: 正在从 {INPUT_FILE} 读取文件列表...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        original_paths = [line.strip().strip('" ') for line in f if line.strip()]

    print(f"\nSTEP 2: 正在上传所有文件到临时公共存储...")
    file_urls = []
    for path in original_paths:
        if not os.path.exists(path): print(f"警告: 文件路径不存在，已跳过 - {path}"); continue
        public_url = upload_file_to_temp_service(path)
        if public_url:
            file_urls.append(public_url)
    
    if not file_urls: print("\n没有文件成功上传，程序退出。"); sys.exit(1)

    print(f"\nSTEP 3: 所有文件上传完毕，正在提交转录任务...")
    try:
        task_response = Transcription.async_call(model='fun-asr', file_urls=file_urls)
        if task_response and task_response.status_code == HTTPStatus.OK and hasattr(task_response.output, 'task_id'):
            task_id = task_response.output.task_id
            print(f"任务已提交，ID: {task_id}。等待服务器处理...")
            transcribe_response = Transcription.wait(task=task_id)
            if transcribe_response and transcribe_response.status_code == HTTPStatus.OK:
                print("\n任务成功完成！正在处理结果...")
                for result in transcribe_response.output.get('results', []):
                    if result.get('subtask_status') == 'SUCCEEDED':
                        original_url = result['file_url']
                        transcription_url = result['transcription_url']
                        # 从原始URL中解析出原始文件名
                        original_filename = os.path.basename(original_url).split('/')[-1]
                        output_filename = f"{os.path.splitext(original_filename)[0]}.txt"
                        print(f"正在获取 '{original_filename}' 的转录结果...")
                        transcript_data = fetch_transcription_result(transcription_url)
                        if transcript_data and 'sentences' in transcript_data:
                            full_text = "".join([s['text'] for s in transcript_data.get('sentences', [])])
                            with open(output_filename, 'w', encoding='utf-8') as out_f: out_f.write(full_text)
                            print(f"转录结果已保存至: {output_filename}")
                    else: print(f"子任务失败: URL {result.get('file_url')}, 原因: {result.get('message')}")
            else:
                print("\n等待任务结果时出错。")
                print(f"调试信息: {transcribe_response}")
        else:
            print("\n提交任务失败，未能获取任务ID。")
            print(f"调试信息: {task_response}")
    except Exception as e:
        print(f"调用API时发生严重错误: {e}")

if __name__ == '__main__':
    main()