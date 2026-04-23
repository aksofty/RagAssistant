import os
import re
from urllib.parse import urlparse, unquote
import magic

def get_file_type(file_path):
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(file_path)
    return file_type    

def convert_links_to_html(text):
    # Обновленное регулярное выражение: 
    # Ищем http/https, затем любые символы, кроме скобок и знаков препинания в конце
    url_pattern = r'(https?://[^\s()<>]+(?:\([\w\d]+\)|(?:[^.,!?:;\"\'<>\s]|\/)))'
    
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')

    def replace_link(match):
        url = match.group(0)
        # Убираем возможные знаки препинания, которые могли случайно попасть в конец
        url = url.rstrip('.,!?:;"\'')
        
        if url.lower().endswith(image_extensions):
            return f'<img style="margin-top: 10px;" width="100%" src="{url}" alt="image" />'
        else:
            return f'<a target="_blank" href="{url}">{url}</a>'

    return re.sub(url_pattern, replace_link, text)

def clean_response_for_chat(text):
    text = convert_links_to_html(text)
    text = text.replace('\n', '<br>')
    #text = text.replace("✈️", "<div style=\"width: 100%; border-top: 1px solid #cccccc; margin: 10px 0;\"></div>✈️")
    text = text.replace("ibblock", "iblock")
    return text

'''def get_rag_cache_path2(source: dict, cache_dir: str):
    file_path = os.path.join(cache_dir, f"{source.get('meta_type')}.cache")
    return file_path'''

def get_rag_cache_path(source: dict, cache_dir: str):
    file_name = format_url_to_filename(source["url"])
    file_path = os.path.join(cache_dir, f"{file_name}.cache")
    return file_path

def format_url_to_filename(url):
    parsed = urlparse(url)
    
    # 1. Обрабатываем домен: убираем точки
    domain = parsed.netloc.replace('.', '_')
    
    # 2. Получаем имя: берем последнюю часть пути, если путь пустой - берем предпоследнюю
    path_parts = [p for p in unquote(parsed.path).split('/') if p]
    
    if not path_parts:
        name = "index"
    else:
        # Берем последний элемент и отрезаем расширение (например, .html)
        name = os.path.splitext(path_parts[-1])[0]
    
    return f"{domain}_{name}"