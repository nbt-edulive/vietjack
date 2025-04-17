import requests
from bs4 import BeautifulSoup
import json
import os
import re
import unicodedata

def remove_accents(input_str):
    """
    Loại bỏ dấu tiếng Việt khỏi chuỗi
    """
    s1 = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in s1 if not unicodedata.combining(c)])

def extract_grade_from_url(url):
    """
    Trích xuất thông tin lớp từ URL
    Ví dụ: từ https://vietjack.com/series/lop-3.jsp -> lop-3
    """
    match = re.search(r'lop-[2-5]', url)
    if match:
        return match.group(0)
    return None

def extract_subject_links(url):
    """
    Lấy các link trong thẻ ul.list cùng cấp với thẻ h3.sub-title 
    nằm trong class="col-md-6", phân loại theo "Môn Tiếng Việt" và "Môn Toán"
    
    Args:
        url (str): URL của trang web cần crawl
        
    Returns:
        dict: Dictionary chứa danh sách các link cho từng môn học
    """
    # Thêm User-Agent để tránh bị chặn
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Dictionary để lưu kết quả với key không dấu
    result = {
        "tieng_viet": [],
        "toan": []
    }
    
    try:
        # Gửi request đến URL
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm tất cả các phần tử col-md-6
        col_md_6_elements = soup.select('.col-md-6')
        
        # Parse base URL để xử lý đường dẫn tương đối
        base_url = '/'.join(url.split('/')[:3])  # Lấy domain
        
        # Lặp qua từng phần tử col-md-6
        for col in col_md_6_elements:
            # Tìm thẻ h3 có class "sub-title" bên trong
            sub_title = col.select_one('h3.sub-title')
            
            if sub_title and sub_title.text:
                title_text = sub_title.text.strip()
                
                # Xác định đây là môn học nào (dùng tên không dấu cho key)
                current_subject = None
                if 'Môn Tiếng Việt' in title_text:
                    current_subject = "tieng_viet"
                elif 'Môn Toán' in title_text:
                    current_subject = "toan"
                
                # Nếu đây là một trong hai môn chúng ta cần
                if current_subject:
                    # Tìm thẻ ul.list cùng cấp với h3.sub-title
                    list_element = sub_title.find_next_sibling('ul', class_='list')
                    
                    if list_element:
                        # Lấy tất cả các link trong ul.list
                        links = list_element.find_all('a')
                        
                        for link in links:
                            href = link.get('href')
                            
                            # Nếu href là đường dẫn tương đối, chuyển thành tuyệt đối
                            if href and not href.startswith(('http://', 'https://')):
                                href = f"{base_url}{href if href.startswith('/') else '/' + href}"
                            
                            # Thêm vào danh sách tương ứng với môn học (chỉ lưu URL)
                            if href:
                                result[current_subject].append(href)
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi crawl dữ liệu: {str(e)}")
        return result

def save_to_json(data, folder_path, subject):
    """
    Lưu dữ liệu vào file JSON theo từng môn học và theo dạng mảng của URLs
    """
    # Tạo folder nếu chưa tồn tại
    os.makedirs(folder_path, exist_ok=True)
    
    # Tạo tên file không dấu
    filename = os.path.join(folder_path, f"{subject}_links.json")
    
    # Lưu dữ liệu dưới dạng mảng URLs
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Đã lưu {len(data)} links môn {subject} vào file {filename}")

def main():
    # Danh sách URLs của các lớp cần crawl
    grade_urls = [
        "https://vietjack.com/series/lop-2.jsp",
        "https://vietjack.com/series/lop-3.jsp",
        "https://vietjack.com/series/lop-4.jsp",
        "https://vietjack.com/series/lop-5.jsp"
    ]
    
    # Xử lý từng URL
    for url in grade_urls:
        grade = extract_grade_from_url(url)
        
        if not grade:
            print(f"Không thể xác định lớp từ URL: {url}")
            continue
        
        print(f"\n=== Đang crawl dữ liệu cho {grade} từ: {url} ===")
        
        # Tạo thư mục cho lớp
        folder_path = grade
        
        # Lấy dữ liệu
        result = extract_subject_links(url)
        
        # Lưu dữ liệu vào file JSON tách biệt cho từng môn
        for subject, links in result.items():
            if links:  # Chỉ lưu nếu có dữ liệu
                # Hiển thị tên môn học đẹp hơn khi in
                display_subject = "Tiếng Việt" if subject == "tieng_viet" else "Toán"
                print(f"\nMôn {display_subject}: Tìm thấy {len(links)} links")
                
                for i, link in enumerate(links[:3], 1):  # Hiển thị 3 links đầu tiên
                    print(f"{i}. {link}")
                
                if len(links) > 3:
                    print(f"... và {len(links) - 3} links khác")
                
                # Lưu vào file JSON (dùng tên không dấu)
                save_to_json(links, folder_path, subject)
            else:
                display_subject = "Tiếng Việt" if subject == "tieng_viet" else "Toán"
                print(f"\nMôn {display_subject}: Không tìm thấy links")

if __name__ == "__main__":
    main()