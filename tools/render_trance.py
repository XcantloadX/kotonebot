import json
import os
from pathlib import Path

def format_json(data):
    """将 JSON 数据格式化为更易读的字符串"""
    formatted = []
    for key, value in data.items():
        if isinstance(value, list):
            value = ', '.join(f'{v:.3f}' if isinstance(v, float) else str(v) for v in value)
        formatted.append(f"<b>{key}:</b> {value}")
    return '<br>'.join(formatted)

def generate_html(entries):
    """生成 HTML 内容"""
    html = """
    <html>
    <head>
        <title>Image Data</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/viewerjs/1.11.7/viewer.min.js" integrity="sha512-lZD0JiwhtP4UkFD1mc96NiTZ14L7MjyX5Khk8PMxJszXMLvu7kjq1sp4bb0tcL6MY+/4sIuiUxubOqoueHrW4w==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/viewerjs/1.11.7/viewer.min.css" integrity="sha512-vRbASHFS0JiM4xwX/iqr9mrD/pXGnOP2CLdmXSSNAjLdgQVFyt4qI+BIoUW7/81uSuKRj0cWv3Dov8vVQOTHLw==" crossorigin="anonymous" referrerpolicy="no-referrer" />
        <style>
            .img-container {
                margin: 20px; padding: 20px; border: 1px solid #ccc;
                display: inline-block;
            }
            img { 
                max-width: 100%; 
                max-height: 400px;
                height: auto; 
                object-fit: contain; 
            }
            .data { margin-top: 10px; }
        </style>
    </head>
    <body>
    """
    
    html += "<div id='container'>"
    for image, data in entries:
        html += f"""
        <div class="img-container">
            <img src="{image}" alt="{image}">
            <div class="data">
                {format_json(data)}
            </div>
        </div>
        """
    html += "</div>"
    html += """
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const gallery = new Viewer(document.getElementById('container'));
            // gallery.show()
        });
    </script>
    </body>
    </html>
    """
    return html

def parse_log(log_content, base_dir):
    """解析日志内容"""
    entries = []
    lines = log_content.strip().split('\n')
    
    for i in range(0, len(lines), 2):
        if i+1 >= len(lines):
            break
        image = os.path.abspath(os.path.join(base_dir, os.path.basename(lines[i])))
        image = 'file:///' + image
        try:
            data = json.loads(lines[i+1])
            entries.append((image, data))
        except json.JSONDecodeError:
            continue
    
    return entries

def main(input_file, output_file):
    """主函数"""
    with open(input_file, 'r') as f:
        log_content = f.read()
    
    base_dir = os.path.dirname(input_file)
    entries = parse_log(log_content, base_dir)
    html_content = generate_html(entries)
    
    with open(output_file, 'w') as f:
        f.write(html_content)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Render log data to HTML')
    parser.add_argument('input', help='Input log file')
    parser.add_argument('output', help='Output HTML file')
    
    args = parser.parse_args()
    
    main(args.input, args.output) 