import requests
import os

def upload(file_path: str) -> str:
    url = 'https://tmpsend.com/upload'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Referer': 'https://tmpsend.com/',
    }
    
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    # 第一次请求：添加文件信息
    files = {
        'action': (None, 'add'),
        'name': (None, file_name),
        'size': (None, str(file_size)),
        'file': (file_name, open(file_path, 'rb'))
    }
    
    response = requests.post(url, headers=headers, files=files)
    if response.status_code != 200:
        raise Exception(f"Upload failed with status code {response.status_code}")
    
    result = response.json()
    if result.get('hasError'):
        raise Exception(result.get('error'))
    
    file_id = result.get('id')
    if not file_id:
        raise Exception("Failed to get file ID")
    
    # 第二次请求：上传实际文件
    upload_files = {
        'action': (None, 'upload'),
        'id': (None, file_id),
        'name': (None, file_name),
        'size': (None, str(file_size)),
        'start': (None, '0'),
        'end': (None, str(file_size)),
        'data': (file_name, open(file_path, 'rb'), 'application/octet-stream')
    }
    
    upload_response = requests.post(url, headers=headers, files=upload_files)
    if upload_response.status_code != 200:
        raise Exception(f"File upload failed with status code {upload_response.status_code}")
    
    return 'https://tmpsend.com/' + file_id

if __name__ == "__main__":
    file_path = r"主题1.thmx"
    print(upload(file_path))

