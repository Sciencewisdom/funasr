
import os
import sys
import json
import time
from http.client import HTTPSConnection
from urllib.parse import urlparse
from dashscope.audio.asr import Transcription
from dashscope import Generation

# --- 用户配置开始 ---
# 请在此处实现您的文件上传逻辑
# 例如，如果您使用阿里云OSS，您需要使用oss2 SDK
# import oss2
def upload_file_to_cloud(local_path):
    """
    将本地文件上传到云存储并返回公共URL。
    这是一个占位函数，您必须自行实现此功能。
    
    Args:
        local_path (str): 本地文件的路径。

    Returns:
        str: 可公开访问的文件URL。
    """
    # ----------------------------------------------------------------
    # 示例：阿里云OSS上传逻辑 (需要您填写自己的配置)
    # ----------------------------------------------------------------
    # 1. 取消以下注释并安装 oss2: pip install oss2
    # 2. 填写您的认证和存储桶信息
    #
    # auth = oss2.Auth('YOUR_ACCESS_KEY_ID', 'YOUR_ACCESS_KEY_SECRET')
    # bucket_name = 'YOUR_BUCKET_NAME'
    # endpoint = 'YOUR_OSS_ENDPOINT' # 例如: oss-cn-hangzhou.aliyuncs.com
    # bucket = oss2.Bucket(auth, endpoint, bucket_name)
    # 
    # object_name = os.path.basename(local_path)
    # 
    # try:
    #     bucket.put_object_from_file(object_name, local_path)
    #     public_url = f"https://{bucket_name}.{endpoint}/{object_name}"
    #     print(f"文件 {local_path} 已上传至 {public_url}")
    #     return public_url
    # except oss2.exceptions.OssError as e:
    #     print(f"上传失败: {e}")
    #     return None
    # ----------------------------------------------------------------

    # --- 占位逻辑 ---
    # 在您实现真实的上传逻辑前，此代码将无法工作
    print("警告: `upload_file_to_cloud` 是一个占位函数。")
    print("您必须实现将文件上传到云存储的逻辑，并返回一个公共URL。")
    # 返回一个示例URL，您需要替换它
    return f"https://your-bucket.your-endpoint.com/{os.path.basename(local_path)}"


# --- 用户配置结束 ---

def fetch_transcription_result(url):
    """从给定的URL获取并解析转录结果JSON。"""
    parsed_url = urlparse(url)
    conn = HTTPSConnection(parsed_url.netloc)
    conn.request("GET", parsed_url.path)
    response = conn.getresponse()
    if response.status == 200:
        data = response.read().decode('utf-8')
        return json.loads(data)
    else:
        print(f"获取转录结果失败，状态码: {response.status}")
        return None

def main():
    """主函数，执行读取、上传、转录和保存的整个流程。"""
    # 1. 检查API Key
    if 'DASHSCOPE_API_KEY' not in os.environ:
        print("错误: 请设置 'DASHSCOPE_API_KEY' 环境变量。")
        sys.exit(1)

    # 2. 读取 asr.txt 文件
    input_file = 'asr.txt'
    if not os.path.exists(input_file):
        print(f"错误: 输入文件 '{input_file}' 未找到。")
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        local_files = [line.strip() for line in f if line.strip()]

    if not local_files:
        print("asr.txt 文件为空，没有需要处理的文件。")
        return

    print(f"从 {input_file} 读取到 {len(local_files)} 个文件。")

    # 3. 上传文件并获取URL
    file_urls = []
    for local_path in local_files:
        if not os.path.exists(local_path):
            print(f"警告: 文件 '{local_path}' 不存在，已跳过。")
            continue
        # 调用您实现的上传函数
        public_url = upload_file_to_cloud(local_path)
        if public_url:
            file_urls.append(public_url)
        else:
            print(f"警告: 文件 '{local_path}' 上传失败，已跳过。")
    
    if not file_urls:
        print("没有成功上传的文件，程序退出。")
        sys.exit(1)
        
    print("\n所有文件已“上传”，准备调用Fun-ASR API。")

    # 4. 调用Fun-ASR API
    try:
        print("提交转录任务...")
        response = Transcription.async_call(model='fun-asr', file_urls=file_urls)
        
        print("任务已提交，等待服务器处理...")
        task_result = Transcription.wait(task=response)

        if task_result and task_result.task_status == 'SUCCEEDED':
            print("任务成功完成！正在处理结果...")
            for result in task_result.output['results']:
                if result.get('subtask_status') == 'SUCCEEDED':
                    original_url = result['file_url']
                    transcription_url = result['transcription_url']
                    
                    # 找到对应的本地文件名
                    original_filename = os.path.basename(urlparse(original_url).path)
                    output_filename = f"{os.path.splitext(original_filename)[0]}.txt"

                    print(f"正在获取 '{original_filename}' 的转录结果...")
                    
                    # 从结果URL下载详细JSON
                    transcript_data = fetch_transcription_result(transcription_url)
                    if transcript_data:
                        full_text = " ".join([s['text'] for s in transcript_data.get('sentences', [])])
                        
                        # 5. 保存转录稿
                        with open(output_filename, 'w', encoding='utf-8') as out_f:
                            out_f.write(full_text)
                        print(f"转录结果已保存至: {output_filename}")
                    else:
                        print(f"未能获取 '{original_filename}' 的详细转录内容。")

                else:
                    print(f"子任务失败: URL {result.get('file_url')}, 原因: {result.get('message')}")
        else:
            print(f"任务失败。状态: {task_result.task_status if task_result else '未知'}")
            if task_result:
                print(f"错误信息: {task_result.message}")

    except Exception as e:
        print(f"调用API时发生错误: {e}")

if __name__ == '__main__':
    main()
