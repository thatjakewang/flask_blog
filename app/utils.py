import bleach
import logging

ALLOWED_HTML_TAGS = ['p', 'strong', 'h1', 'h2', 'h3', 'ul', 'ol', 'li', 'a', 'code', 'pre', 'span', 'img', 'details','summary']
ALLOWED_HTML_ATTRIBUTES = {'*': ['class', 'id'], 'a': ['href', 'class'], 'img': ['src', 'alt', 'class'], 'details': ['open', 'class', 'id']}

# Bleach version logging moved to app initialization

def clean_html_content(html_content: str, context: str = None) -> str:
    """
    Clean HTML content by removing disallowed tags and attributes.
    """
    try:
        # 自定義屬性過濾函數 - 直接在 clean 函數中定義
        def custom_attribute_filter(tag, name, value):
            """
            Custom attribute filter for bleach.clean()
            Args:
                tag: HTML tag name (e.g., 'a', 'img')
                name: attribute name (e.g., 'href', 'src')
                value: attribute value
            Returns:
                True to keep the attribute, False to remove it
            """
            # 允許基本屬性
            if name in ['class', 'id', 'alt']:
                return True
            
            # 處理 img 標籤的 src 屬性
            if tag == 'img' and name == 'src':
                if not isinstance(value, str):
                    return False
                # 允許本地靜態檔案和信任的外部網域
                trusted_patterns = [
                    '/static/images/',  # 本地靜態圖片
                    'https://jake.tw',  # 外部信任網域
                    'data:image/'       # base64 圖片
                ]
                return any(value.startswith(pattern) for pattern in trusted_patterns)
            
            # 處理 a 標籤的 href 屬性  
            if tag == 'a' and name == 'href':
                if not isinstance(value, str):
                    return False
                return value.startswith(('http://', 'https://'))
            
            # 其他屬性預設不允許
            # Allow boolean "open" attribute on <details>
            if tag == 'details' and name == 'open':
                return True

            return False

        # 使用 bleach.clean 進行清理
        cleaned_content = bleach.clean(
            html_content,
            tags=ALLOWED_HTML_TAGS,
            attributes=custom_attribute_filter,  # 使用函數而不是字典
            protocols=['http', 'https'],
            strip=True  # 移除不允許的標籤而不是轉義
        )
        
        return cleaned_content
    
    except Exception as e:
        context_str = f" Context: {context}" if context else ""
        logging.error(f"Error cleaning HTML content: {e}. Input snippet: {html_content[:100]}...{context_str}")
        return ""