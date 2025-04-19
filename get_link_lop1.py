import requests
from bs4 import BeautifulSoup
import re
import os.path

def extract_links_from_col_md6(url):
    # Gửi request đến trang web và lấy nội dung HTML
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi tải trang web: {e}")
        return []

    # Phân tích cú pháp HTML bằng BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Lấy domain của trang web
    base_domain = "https://www.vietjack.com"
    
    # Tìm tất cả phần tử có class "col-md-6"
    col_elements = soup.find_all(class_="col-md-6")
    
    # Lấy tất cả các link href từ các thẻ a trong các phần tử trên
    links = []
    for element in col_elements:
        anchors = element.find_all('a', href=True)
        for anchor in anchors:
            href = anchor['href']
            
            # Xử lý các loại URL khác nhau
            if href.startswith('http://') or href.startswith('https://'):
                # URL đầy đủ, giữ nguyên
                fixed_href = href
            elif href.startswith('../'):
                # URL dạng "../path" - bỏ "../" và thêm domain
                fixed_href = base_domain + '/' + href.replace('../', '')
            elif href.startswith('./'):
                # URL dạng "./path" - bỏ "./" và thêm domain
                fixed_href = base_domain + '/' + href[2:]
            elif href.startswith('/'):
                # URL dạng "/path" - thêm domain
                fixed_href = base_domain + href
            else:
                # URL dạng "path" - thêm domain và dấu /
                fixed_href = base_domain + '/' + href
            
            links.append({
                'original': href,
                'fixed': fixed_href
            })
    
    return links

# Sử dụng hàm
if __name__ == "__main__":
    # Thay thế URL bằng trang web cần trích xuất
    target_url = "https://www.vietjack.com/series/lop-1.jsp"
    
    extracted_links = extract_links_from_col_md6(target_url)
    
    # In kết quả
    print(f"Tìm thấy {len(extracted_links)} link trong class 'col-md-6':")
    for i, link_data in enumerate(extracted_links, 1):
        print(f"{link_data['fixed']}")
    
    # # Lưu các link đã sửa vào file (tùy chọn)
    # with open('fixed_links.txt', 'w', encoding='utf-8') as f:
    #     for link_data in extracted_links:
    #         f.write(f"{link_data['fixed']}\n")
    
    # print("\nĐã lưu các link đã sửa vào file 'fixed_links.txt'")