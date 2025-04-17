import requests
from bs4 import BeautifulSoup
import html2text
import os
import re
from urllib.parse import urljoin, urlparse

def fix_relative_urls(html_content, base_url):
    """
    Sửa các đường dẫn tương đối (../path) thành đường dẫn tuyệt đối
    
    Args:
        html_content: Đối tượng BeautifulSoup
        base_url: URL cơ sở của trang web
    """
    # Sửa các đường dẫn trong thẻ img
    for img in html_content.find_all('img'):
        if img.get('src'):
            img['src'] = urljoin(base_url, img['src'])
    
    # Sửa các đường dẫn trong thẻ a
    for a in html_content.find_all('a'):
        if a.get('href'):
            a['href'] = urljoin(base_url, a['href'])
    
    # Sửa các đường dẫn trong thuộc tính style có url()
    for tag in html_content.find_all(style=True):
        if 'url(' in tag['style']:
            style = tag['style']
            # Tìm tất cả các url() trong style
            urls = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style)
            for url in urls:
                if not url.startswith(('http://', 'https://', 'data:')):
                    absolute_url = urljoin(base_url, url)
                    style = style.replace(f'url({url})', f'url({absolute_url})')
            tag['style'] = style
    
    return html_content

def crawl_and_convert_to_markdown(url):
    """
    Crawl content from a webpage and convert to markdown using BeautifulSoup.
    
    Args:
        url (str): URL of the webpage to crawl
        
    Returns:
        str: Content converted to markdown
    """
    # Thêm User-Agent để tránh bị chặn
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Lấy tên miền cơ sở từ URL
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Gửi request đến URL
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm container chính
        main_content = soup.select_one('.col-md-7.middle-col')
        
        if not main_content:
            return "Không tìm thấy nội dung trong selector chỉ định."
        
        # Loại bỏ các phần tử không mong muốn
        unwanted_classes = [
            '.paging.paging-btn',
            '.list',
            '.vj-toc',
            '.vj-more',
            '.vj-note',
            '.box-new-title'
        ]
        
        for selector in unwanted_classes:
            for element in main_content.select(selector):
                element.decompose()  # Xóa phần tử khỏi DOM
        
        # Sửa đường dẫn tương đối thành tuyệt đối
        main_content = fix_relative_urls(main_content, url)
        
        # Chuyển đổi HTML sang markdown
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = False
        converter.body_width = 0  # Không ngắt dòng
        markdown_content = converter.handle(str(main_content))
        
        return markdown_content
    
    except requests.exceptions.RequestException as e:
        return f"Lỗi khi crawl dữ liệu: {str(e)}"

def save_to_file(content, filename="output.md"):
    """Save content to a file"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Đã lưu nội dung vào file {filename}")

def main():
    # URL cần crawl
    url = "https://vietjack.com/toan-3-cd/on-tap-ve-phep-nhan-bang-nhan-2-bang-nhan-5.jsp"
    
    print(f"Đang crawl dữ liệu từ: {url}")
    markdown_content = crawl_and_convert_to_markdown(url)
    
    # Lưu nội dung vào file
    save_to_file(markdown_content)
    
    # In ra một phần nội dung để kiểm tra
    print(markdown_content + "...\n")

if __name__ == "__main__":
    main()