import requests
from bs4 import BeautifulSoup
import html2text
import os
import re
import json
import time
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Cấu hình Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN_1") # Thay YOUR_BOT_TOKEN bằng token của bot Telegram
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")  # Thay YOUR_CHAT_ID bằng chat ID của bạn
ENABLE_TELEGRAM = True  # Đặt thành True khi bạn đã cấu hình token và chat ID

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("markdown_crawler.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("markdown_crawler")

def send_telegram_message(message):
    """
    Gửi tin nhắn tới Telegram Bot
    
    Args:
        message (str): Nội dung tin nhắn
    """
    if not ENABLE_TELEGRAM:
        return
        
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Lỗi khi gửi tin nhắn Telegram: {str(e)}")

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
        dict: Dictionary containing title and content
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
            error_msg = f"Không tìm thấy nội dung trong selector chỉ định tại {url}"
            logger.warning(error_msg)
            send_telegram_message(f"⚠️ {error_msg}")
            return {
                "title": "Error",
                "content": "Không tìm thấy nội dung trong selector chỉ định.",
                "status": "error"
            }
        
        # Loại bỏ các phần tử không mong muốn
        unwanted_classes = [
            '.paging.paging-btn',
            '.list',
            '.vj-toc',
            '.vj-more',
            '.vj-note',
            '.box-new-title',
            '.box-new',
            '.box-slide',
            '.box-course',
            '.box-most-viewed',
            '.all-list',
            '._2pi8'
        ]
        
        # Lặp qua từng class và xóa tất cả các phần tử có class đó
        for selector in unwanted_classes:
            while True:
                # Tìm phần tử đầu tiên có class hiện tại
                element = main_content.select_one(selector)
                if not element:
                    # Không còn phần tử nào với class này
                    break
                # Xóa phần tử
                element.decompose()
        
        # Sửa đường dẫn tương đối thành tuyệt đối
        main_content = fix_relative_urls(main_content, url)
        
        # Chuyển đổi HTML sang markdown
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = False
        converter.body_width = 0  # Không ngắt dòng
        markdown_content = converter.handle(str(main_content))
        
        # Lấy tiêu đề bài viết nếu có
        title_element = main_content.select_one('h1')
        title = title_element.text.strip() if title_element else "Không có tiêu đề"
        
        return {
            "title": title,
            "content": markdown_content,
            "status": "success"
        }
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Lỗi khi crawl {url}: {str(e)}"
        logger.error(error_msg)
        send_telegram_message(f"❌ {error_msg}")
        return {
            "title": "Error",
            "content": f"Lỗi khi crawl dữ liệu: {str(e)}",
            "status": "error"
        }

def create_filename_from_url(url, title):
    """
    Tạo tên file từ URL và tiêu đề
    
    Args:
        url (str): URL của trang web
        title (str): Tiêu đề bài viết
    
    Returns:
        str: Tên file hợp lệ
    """
    # Lấy phần cuối của URL (không bao gồm đuôi)
    path = urlparse(url).path
    filename = os.path.splitext(os.path.basename(path))[0]
    
    # Nếu filename rỗng, sử dụng tiêu đề
    if not filename:
        filename = title
    
    # Loại bỏ các ký tự không hợp lệ
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = re.sub(r'[\s-]+', '-', filename).strip('-')
    
    return filename + '.md'

def load_urls_from_json(json_file):
    """
    Đọc danh sách URL từ file JSON
    
    Args:
        json_file (str): Đường dẫn đến file JSON
    
    Returns:
        list: Danh sách URL
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Kiểm tra cấu trúc của file JSON và trích xuất URL
        urls = []
        if isinstance(data, list):
            # Nếu JSON là một mảng
            for item in data:
                if isinstance(item, str):
                    # Nếu item là string (URL trực tiếp)
                    urls.append(item)
                elif isinstance(item, dict) and 'url' in item:
                    # Nếu item là đối tượng có thuộc tính url
                    urls.append(item['url'])
        elif isinstance(data, dict):
            # Nếu JSON là một đối tượng
            if 'urls' in data and isinstance(data['urls'], list):
                # Nếu có thuộc tính urls là mảng
                urls = data['urls']
            elif 'links' in data and isinstance(data['links'], list):
                # Nếu có thuộc tính links là mảng
                urls = data['links']
        
        return urls
    
    except Exception as e:
        error_msg = f"Lỗi khi đọc file JSON {json_file}: {str(e)}"
        logger.error(error_msg)
        send_telegram_message(f"❌ {error_msg}")
        return []

def load_checkpoint(checkpoint_file):
    """
    Đọc danh sách URL đã crawl từ file checkpoint
    
    Args:
        checkpoint_file (str): Đường dẫn đến file checkpoint
    
    Returns:
        set: Tập hợp các URL đã crawl
    """
    try:
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()
    except Exception as e:
        error_msg = f"Lỗi khi đọc file checkpoint {checkpoint_file}: {str(e)}"
        logger.error(error_msg)
        send_telegram_message(f"❌ {error_msg}")
        return set()

def save_checkpoint(checkpoint_file, crawled_urls):
    """
    Lưu danh sách URL đã crawl vào file checkpoint
    
    Args:
        checkpoint_file (str): Đường dẫn đến file checkpoint
        crawled_urls (set): Tập hợp các URL đã crawl
    """
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(list(crawled_urls), f, ensure_ascii=False, indent=2)
        logger.info(f"Đã lưu checkpoint vào {checkpoint_file}")
    except Exception as e:
        error_msg = f"Lỗi khi lưu file checkpoint {checkpoint_file}: {str(e)}"
        logger.error(error_msg)
        send_telegram_message(f"❌ {error_msg}")

def extract_path_components(json_path):
    """
    Trích xuất các thành phần đường dẫn từ đường dẫn file JSON
    
    Args:
        json_path (str): Đường dẫn đến file JSON
    
    Returns:
        dict: Các thành phần đường dẫn
    """
    # Chuẩn hóa đường dẫn để làm việc với tất cả các hệ điều hành
    json_path = os.path.normpath(json_path)
    parts = json_path.split(os.sep)
    
    # Tìm các phần trong đường dẫn
    lop = ""
    mon = ""
    
    for i, part in enumerate(parts):
        if part.startswith("lop-"):
            lop = part
            if i+1 < len(parts):
                mon = parts[i+1]
    
    return {
        "lop": lop,
        "mon": mon
    }

def create_output_directory(json_path):
    """
    Tạo thư mục đầu ra dựa trên đường dẫn file JSON
    
    Args:
        json_path (str): Đường dẫn đến file JSON
    
    Returns:
        str: Đường dẫn đến thư mục đầu ra
    """
    # Lấy các thành phần đường dẫn
    components = extract_path_components(json_path)
    lop = components["lop"]
    mon = components["mon"]
    
    # Tạo đường dẫn đến thư mục đầu ra
    json_dir = os.path.dirname(json_path)
    output_dir = os.path.join(json_dir, "markdown")
    
    # Tạo thư mục nếu chưa tồn tại
    Path(output_dir).mkdir(exist_ok=True, parents=True)
    
    return output_dir

def find_json_files(base_dir, lop_range=range(1,2), mon_choices=["tieng_viet", "toan"]):
    """
    Tìm tất cả các file JSON content_links.json trong thư mục
    
    Args:
        base_dir (str): Thư mục cơ sở để tìm kiếm
        lop_range (range): Phạm vi lớp cần tìm
        mon_choices (list): Danh sách các môn học cần tìm
        
    Returns:
        list: Danh sách đường dẫn đến các file JSON
    """
    json_files = []
    
    for lop_choice in lop_range:
        lop = f"lop-{lop_choice}"
        lop_dir = os.path.join(base_dir, lop)
        
        if not os.path.isdir(lop_dir):
            continue
            
        for mon in mon_choices:
            # Tìm tất cả các thư mục con trong thư mục môn học
            mon_dir = os.path.join(lop_dir, mon)
            
            if not os.path.isdir(mon_dir):
                continue
                
            # Duyệt qua tất cả thư mục con trong thư mục môn học
            for root, dirs, files in os.walk(mon_dir):
                if "content_links.json" in files:
                    json_files.append(os.path.join(root, "content_links.json"))
    
    return json_files

def main():
    # Thời gian bắt đầu
    start_time = datetime.now()
    
    # Banner
    banner = """
    =========================================================
    =            CRAWLER VIETJACK TO MARKDOWN              =
    =                  PHIÊN BẢN LỚP 1                  =
    =========================================================
    """
    
    logger.info(banner)
    
    # Gửi thông báo bắt đầu
    start_msg = f"🚀 <b>BẮT ĐẦU CRAWL VIETJACK TO MARKDOWN</b>\n" \
               f"⏰ Thời gian: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
    send_telegram_message(start_msg)
    
    # Đường dẫn mặc định cho thư mục crawl
    base_dir = "."  # Thay đổi nếu cần
    
    # Thống kê
    stats = {
        "total_files": 0,
        "processed_files": 0,
        "total_urls": 0,
        "processed_urls": 0,
        "skipped_urls": 0,
        "failed_urls": 0
    }
    
    # Tìm tất cả các file JSON cần xử lý
    json_files = find_json_files(base_dir)
    
    if not json_files:
        error_msg = "Không tìm thấy file JSON content_links.json nào!"
        logger.error(error_msg)
        send_telegram_message(f"⚠️ {error_msg}")
        return
    
    stats["total_files"] = len(json_files)
    logger.info(f"Tìm thấy {len(json_files)} file JSON cần xử lý")
    send_telegram_message(f"🔍 Tìm thấy {len(json_files)} file JSON cần xử lý")
    
    # Lặp qua tất cả các file JSON
    for file_index, json_path in enumerate(json_files, 1):
        # Lấy thông tin lớp và môn học từ đường dẫn
        components = extract_path_components(json_path)
        lop = components["lop"]
        mon = components["mon"]
        
        # Hiển thị tên môn học đẹp hơn
        display_mon = "Tiếng Việt" if mon == "tieng_viet" else "Toán"
        
        logger.info(f"\n=== [{file_index}/{len(json_files)}] Đang xử lý: {lop} - {display_mon} ===")
        send_telegram_message(f"📂 <b>Đang xử lý ({file_index}/{len(json_files)}):</b> {lop} - {display_mon}")
        
        try:
            # Kiểm tra xem file JSON có tồn tại không
            if not os.path.exists(json_path):
                logger.warning(f"Không tìm thấy file JSON tại đường dẫn: {json_path}")
                continue  # Bỏ qua và tiếp tục với môn/lớp tiếp theo
            
            # Tạo thư mục đầu ra
            output_dir = create_output_directory(json_path)
            
            # Tạo file checkpoint
            checkpoint_file = os.path.join(output_dir, "checkpoint.json")
            
            # Đọc danh sách URL đã crawl từ file checkpoint
            crawled_urls = load_checkpoint(checkpoint_file)
            
            # Đọc danh sách URL từ file JSON
            all_urls = load_urls_from_json(json_path)
            
            if not all_urls:
                warning_msg = f"Không tìm thấy URL nào trong file {json_path}"
                logger.warning(warning_msg)
                send_telegram_message(f"⚠️ {warning_msg}")
                continue  # Bỏ qua và tiếp tục với môn/lớp tiếp theo
            
            # Lọc các URL chưa crawl
            urls_to_crawl = [url for url in all_urls if url not in crawled_urls]
            
            stats["total_urls"] += len(all_urls)
            stats["skipped_urls"] += len(crawled_urls)
            
            logger.info(f"Tổng số URL: {len(all_urls)}")
            logger.info(f"Số URL đã crawl: {len(crawled_urls)}")
            logger.info(f"Số URL cần crawl: {len(urls_to_crawl)}")
            
            # Gửi thông báo số lượng URL cần crawl
            urls_info_msg = f"📊 <b>{lop} - {display_mon}:</b>\n" \
                           f"- Tổng số URL: {len(all_urls)}\n" \
                           f"- URL đã crawl: {len(crawled_urls)}\n" \
                           f"- URL cần crawl: {len(urls_to_crawl)}"
            send_telegram_message(urls_info_msg)
            
            if not urls_to_crawl:
                logger.info("Tất cả URL đã được crawl!")
                continue  # Bỏ qua và tiếp tục với môn/lớp tiếp theo
            
            # Số URL thành công và thất bại trong file này
            successful_count = 0
            failed_count = 0
            
            # Crawl từng URL và lưu vào file markdown
            for i, url in enumerate(urls_to_crawl, 1):
                logger.info(f"[{i}/{len(urls_to_crawl)}] Đang crawl: {url}")
                
                try:
                    result = crawl_and_convert_to_markdown(url)
                    
                    if result["status"] == "success":
                        # Tạo tên file từ URL hoặc tiêu đề
                        filename = create_filename_from_url(url, result["title"])
                        file_path = os.path.join(output_dir, filename)
                        
                        # Lưu nội dung vào file
                        with open(file_path, 'w', encoding='utf-8') as f:
                            # Thêm tiêu đề vào đầu file markdown
                            f.write(f"# {result['title']}\n\n")
                            f.write(result["content"])
                        
                        logger.info(f"Đã lưu nội dung vào file {file_path}")
                        
                        # Thêm URL vào danh sách đã crawl
                        crawled_urls.add(url)
                        successful_count += 1
                        
                        # Lưu checkpoint sau mỗi 5 URL hoặc khi crawl URL cuối cùng
                        if i % 5 == 0 or i == len(urls_to_crawl):
                            save_checkpoint(checkpoint_file, crawled_urls)
                            
                            # Gửi thông báo tiến độ sau mỗi 5 URL
                            progress_msg = f"🔄 <b>{lop} - {display_mon}:</b> Đã xử lý {i}/{len(urls_to_crawl)} URL"
                            send_telegram_message(progress_msg)
                    else:
                        logger.error(f"Lỗi khi xử lý URL {url}: {result['content']}")
                        failed_count += 1
                
                except Exception as e:
                    error_msg = f"Lỗi không xác định khi xử lý URL {url}: {str(e)}"
                    logger.error(error_msg)
                    send_telegram_message(f"❌ {error_msg}")
                    failed_count += 1
                
                # Nghỉ một chút để tránh bị chặn
                time.sleep(1)
            
            # Lưu checkpoint cuối cùng
            save_checkpoint(checkpoint_file, crawled_urls)
            
            # Cập nhật thống kê
            stats["processed_urls"] += successful_count
            stats["failed_urls"] += failed_count
            stats["processed_files"] += 1
            
            # Gửi thông báo hoàn thành file
            complete_msg = f"✅ <b>Hoàn thành {lop} - {display_mon}:</b>\n" \
                          f"- Đã crawl thành công: {successful_count}/{len(urls_to_crawl)} URL\n" \
                          f"- Lỗi: {failed_count} URL\n" \
                          f"- Lưu tại: {output_dir}"
            
            logger.info(f"Hoàn thành! Đã crawl và lưu {successful_count} trang vào thư mục {output_dir}")
            send_telegram_message(complete_msg)
            
        except Exception as e:
            error_msg = f"Lỗi không xác định khi xử lý file {json_path}: {str(e)}"
            logger.error(error_msg)
            send_telegram_message(f"❌ {error_msg}")
    
    # Thời gian kết thúc
    end_time = datetime.now()
    duration = end_time - start_time
    
    # Gửi thông báo hoàn thành toàn bộ
    final_msg = f"🎉 <b>HOÀN THÀNH TOÀN BỘ CÔNG VIỆC</b>\n" \
               f"⏰ Thời gian bắt đầu: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n" \
               f"⏰ Thời gian kết thúc: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n" \
               f"⏱️ Tổng thời gian: {str(duration).split('.')[0]}\n" \
               f"📊 <b>Thống kê:</b>\n" \
               f"- Files đã xử lý: {stats['processed_files']}/{stats['total_files']}\n" \
               f"- URL đã crawl: {stats['processed_urls']}\n" \
               f"- URL bỏ qua (đã crawl trước đó): {stats['skipped_urls']}\n" \
               f"- URL lỗi: {stats['failed_urls']}\n" \
               f"- Tổng URL: {stats['total_urls']}"
    
    logger.info("\n=== KẾT QUẢ CUỐI CÙNG ===")
    logger.info(f"Files đã xử lý: {stats['processed_files']}/{stats['total_files']}")
    logger.info(f"URL đã crawl: {stats['processed_urls']}")
    logger.info(f"URL bỏ qua (đã crawl trước đó): {stats['skipped_urls']}")
    logger.info(f"URL lỗi: {stats['failed_urls']}")
    logger.info(f"Tổng URL: {stats['total_urls']}")
    logger.info(f"Tổng thời gian: {str(duration).split('.')[0]}")
    logger.info("=== HOÀN THÀNH ===")
    
    send_telegram_message(final_msg)

if __name__ == "__main__":
    main()