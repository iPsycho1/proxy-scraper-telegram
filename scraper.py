import requests
from bs4 import BeautifulSoup
import os
import re
import concurrent.futures

# آدرس سایتی که برای تست پروکسی استفاده می‌شود (سریع و قابل اعتماد)
TEST_URL = "http://httpbin.org/ip"
# حداکثر تعداد پروکسی برای تست همزمان
MAX_THREADS = 20
# حداکثر زمان انتظار برای تست هر پروکسی (به ثانیه)
TIMEOUT = 10
# آدرس سایت منبع پروکسی
PROXY_LIST_URL = "https://free-proxy-list.net/"

def escape_markdown_v2(text):
    """تمام کاراکترهای خاص را برای MarkdownV2 تلگرام escape می‌کند."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def fetch_proxies():
    """لیست اولیه پروکسی‌ها را به همراه جزئیات از سایت منبع استخراج می‌کند."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(PROXY_LIST_URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table_container = soup.find('div', class_='table-responsive')
        
        potential_proxies = []
        rows = table_container.find('tbody').find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 6:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                country = cols[3].text.strip()
                proxy_info = {'address': f"{ip}:{port}", 'country': country}
                potential_proxies.append(proxy_info)
        
        return potential_proxies
    except Exception as e:
        print(f"خطا در استخراج لیست اولیه پروکسی‌ها: {e}")
        return []

def test_proxy(proxy_info):
    """یک پروکسی را تست می‌کند و در صورت فعال بودن، کل اطلاعات آن را برمی‌گرداند."""
    proxy_address = proxy_info['address']
    proxy_dict = {'http': f"http://{proxy_address}", 'https': f"https://{proxy_address}"}
    try:
        response = requests.get(TEST_URL, proxies=proxy_dict, timeout=TIMEOUT)
        if response.status_code == 200:
            print(f"✅ پروکسی فعال: {proxy_address}")
            return proxy_info
    except Exception:
        print(f"❌ پروکسی غیرفعال: {proxy_address}")
    return None

def send_to_telegram(message):
    """پیام را به کانال تلگرام ارسال می‌کند."""
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if not bot_token or not chat_id:
        print("توکن ربات یا چت آیدی تنظیم نشده است.")
        return
        
    if len(message) > 4096:
        message = message[:4090] + "\n\.\.\."
        
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'MarkdownV2', 'disable_web_page_preview': True}
        response = requests.post(api_url, data=payload, timeout=10)
        print(response.json())
    except Exception as e:
        print(f"خطا در ارسال پیام به تلگرام: {e}")

if __name__ == "__main__":
    # لینک کانال خود را اینجا وارد کنید
    CHANNEL_LINK = "@SueProxy1" # <--- این خط را ویرایش کنید
    
    # متن پایانی
    FOOTER_TEXT = "📣 با معرفی کانال و اشتراک پست ها با دوستان خود، ما را حمایت کنید ❤️"
    
    potential_proxies = fetch_proxies()
    
    if not potential_proxies:
        send_to_telegram("❌ لیست اولیه پروکسی‌ها از سایت منبع دریافت نشد")
    else:
        active_proxies = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            future_to_proxy = {executor.submit(test_proxy, p): p for p in potential_proxies}
            for future in concurrent.futures.as_completed(future_to_proxy):
                result = future.result()
                if result:
                    active_proxies.append(result)
        
        if active_proxies:
            header = f"✅ *تست کامل شد\\! {len(active_proxies)} پروکسی فعال پیدا شد:*\n\n"
            message_lines = []
            for p in active_proxies:
                # --- این بخش برای حل مشکل بولد شدن، ساده‌سازی شده است ---
                escaped_address = escape_markdown_v2(p['address'])
                escaped_country_name = escape_markdown_v2(p['country'])
                line = f"> `{escaped_address}` — *{escaped_country_name}*"
                # --- پایان بخش اصلاح شده ---
                message_lines.append(line)
            
            # آماده‌سازی متن پایانی
            escaped_footer = escape_markdown_v2(FOOTER_TEXT)
            footer = f"\n\n{escaped_footer}\n[{escape_markdown_v2(CHANNEL_LINK)}]({CHANNEL_LINK})"

            message = header + "\n".join(message_lines) + footer
            send_to_telegram(message)
        else:
            send_to_telegram("❌ هیچ پروکسی فعالی پس از تست پیدا نشد")
