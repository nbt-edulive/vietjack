import requests
from bs4 import BeautifulSoup
import json
import os
import re
from urllib.parse import urljoin, urlparse

def extract_grade_from_url(url):
    """
    Trích xuất thông tin lớp từ URL
    Ví dụ: từ https://vietjack.com/ngu-van-6-cd/index.jsp -> lop-6
    """
    # Tìm số lớp trong URL
    match = re.search(r'(ngu-van|tieng-viet|toan)-([6-9]|1[0-2])', url)
    if match:
        return f"lop-{match.group(2)}"
    return None

def extract_subject_from_url(url):
    """
    Trích xuất môn học từ URL
    """
    if "ngu-van" in url or "tieng-viet" in url:
        return "ngu_van"
    elif "toan" in url:
        return "toan"
    return None

def extract_all_links(url):
    """
    Lấy tất cả các link nằm trong class "list" thuộc lớp con của class "col-md-6"
    
    Args:
        url (str): URL của trang web cần crawl
        
    Returns:
        list: Danh sách các link href
    """
    # Thêm User-Agent để tránh bị chặn
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Danh sách để lưu tất cả các link
    all_links = []
    
    try:
        # Gửi request đến URL
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Lấy base URL từ URL hiện tại để xử lý đường dẫn tương đối
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Tìm tất cả các phần tử col-md-6
        col_md_6_elements = soup.select('.col-md-6')
        
        # Lặp qua từng phần tử col-md-6
        for col in col_md_6_elements:
            # Tìm tất cả các phần tử có class "list" trong col-md-6
            list_elements = col.select('.list')
            
            # Lặp qua từng phần tử list
            for list_element in list_elements:
                # Tìm tất cả các link trong phần tử list
                links = list_element.find_all('a')
                
                # Lặp qua từng link và lưu thông tin
                for link in links:
                    href = link.get('href')
                    
                    # Nếu href là đường dẫn tương đối, chuyển thành tuyệt đối
                    if href and not href.startswith(('http://', 'https://')):
                        href = urljoin(base_url, href)
                    
                    # Thêm vào danh sách kết quả (chỉ lưu URL)
                    if href:
                        all_links.append(href)
        
        return all_links
        
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi crawl dữ liệu: {str(e)}")
        return []

def load_links_from_json(folder_path, subject):
    """
    Đọc danh sách links từ file JSON
    """
    filename = os.path.join(folder_path, f"{subject}_links.json")
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Không tìm thấy file {filename}")
        return []

def save_to_json(data, filename):
    """
    Lưu danh sách links vào file JSON
    """
    # Đảm bảo thư mục tồn tại
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Đã lưu {len(data)} links vào file {filename}")

def main():
    # Tìm tất cả các thư mục lớp
    grade_folders = [folder for folder in os.listdir('.') if folder.startswith('lop-') and os.path.isdir(folder)]
    
    if not grade_folders:
        print("Không tìm thấy thư mục lớp nào (lop-6, lop-7, lop-8, lop-9, lop-10, lop-11, lop-12)")
        return
    
    for grade_folder in grade_folders:
        print(f"\n=== Xử lý dữ liệu cho {grade_folder} ===")
        
        # Tìm các file JSON trong thư mục lớp
        subject_files = [f for f in os.listdir(grade_folder) if f.endswith('_links.json')]
        
        if not subject_files:
            print(f"Không tìm thấy file JSON trong thư mục {grade_folder}")
            continue
        
        for subject_file in subject_files:
            subject = subject_file.replace('_links.json', '')
            
            # Hiển thị tên môn học đẹp hơn khi in
            display_subject = "Ngữ Văn" if subject == "ngu_van" else "Toán"
            print(f"\nĐang xử lý môn {display_subject}...")
            
            # Đọc danh sách links từ file JSON
            links = load_links_from_json(grade_folder, subject)
            
            if not links:
                print(f"Không có links nào trong file {subject_file}")
                continue

            print(f"Đã tìm thấy {len(links)} links cần crawl")
            
            # Crawl từng link và lưu kết quả
            for i, link in enumerate(links):
                print(f"\nCrawl ({i+1}/{len(links)}): {link}")
                
                # Trích xuất tên từ URL để đặt tên file
                link_name = link.split('/')[-1].replace('.jsp', '')
                
                # Tạo thư mục con trong thư mục lớp để lưu kết quả của link này
                content_folder = os.path.join(grade_folder, subject, link_name)
                os.makedirs(content_folder, exist_ok=True)
                
                # Crawl dữ liệu
                content_links = extract_all_links(link)
                
                if content_links:
                    print(f"Tìm thấy {len(content_links)} content links")
                    
                    # Lưu vào file JSON
                    content_file = os.path.join(content_folder, "content_links.json")
                    save_to_json(content_links, content_file)
                else:
                    print("Không tìm thấy content links nào")

if __name__ == "__main__":
    main()