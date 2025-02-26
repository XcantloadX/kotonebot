import requests
import os

def upload(file_path: str) -> str:
    """
    上传文件到 paste.sensio.no
    
    Args:
        file_path: 要上传的文件路径
    
    Returns:
        str: 上传后的 URL
    """
    url = 'https://paste.sensio.no/'
    headers = {
        'accept': 'text/plain',
        'User-Agent': 'KAA',
        'x-uuid': ''
    }
    
    files = {
        'file': (os.path.basename(file_path), open(file_path, 'rb'))
    }
        
    response = requests.post(url, files=files, headers=headers, allow_redirects=False)
    
    if response.status_code != 200:
        raise Exception(f"Upload failed with status code {response.status_code}")
    
    return response.text.strip()

if __name__ == "__main__":
    test_file = "version"
    if os.path.exists(test_file):
        result = upload(test_file)
        print(f"Upload result: {result}")
