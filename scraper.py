import requests
from bs4 import BeautifulSoup
import os

# آدرس سایت جدید که پروکسی‌ها را در جدول ساده نمایش می‌دهد
PROXY_LIST_URL = "https://free-proxy-list.net/"

def extract_proxies_from_table(url):
    """لیست پروکسی‌ها را از یک جدول HTML ساده استخراج می‌کند."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # در این سایت، جدول داخل یک div با کلاس خاص قرار دارد
        table_container = soup.find('div', class_='table-responsive')
        if not table_container:
            return None, "کانتینر جدول پروکسی‌ها پیدا نشد."

        proxies = []
        rows = table_container.find('tbody').find_all('tr')
        
        for row in rows[:10]: # فقط ۱۰ پروکسی اول
            cols = row.find_all('td')
            if len(cols) > 6:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                country = cols[3].text.strip()
                # چک می‌کنیم که پروکسی از نوع http یا https باشد
                is_https = cols[6].text.strip()
                proxy_type = "HTTPS" if is_https == 'yes' else "HTTP"
                
                proxies.append(f"{ip}:{port} ({country} - {proxy_type})")
        
        if not proxies:
            return None, "جدول پیدا شد اما هیچ پروکسی‌ای در آن نبود."

        return proxies, "موفق"

    except requests.exceptions.RequestException as e:
        return None, f"خطای شبکه در اتصال به سایت: {e}"

def send_to_telegram(message):
    """پیام را به کانال تلگرام ارسال می‌کند."""
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if not bot_token or not chat_id:
        print("توکن ربات یا چت آیدی تنظیم نشده است.")
        return
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
        response = requests.post(api_url, data=payload, timeout=10)
        print(response.json())
    except Exception as e:
        print(f"خطا در ارسال پیام به تلگرام: {e}")

if __name__ == "__main__":
    proxy_list, status_message = extract_proxies_from_table(PROXY_LIST_URL)
    
    if proxy_list:
        message = "✅ **لیست پروکسی‌های جدید:**\n\n"
        message += "\n".join(f"`{p}`" for p in proxy_list)
        send_to_telegram(message)
    else:
        error_message = f"❌ دریافت لیست پروکسی‌ها ناموفق بود.\n\n**دلیل:** {status_message}"
        send_to_telegram(error_message)
