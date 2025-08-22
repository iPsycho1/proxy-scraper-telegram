import requests
from bs4 import BeautifulSoup
import os

def extract_proxies(url):
    """صفحه وب را برای استخراج پروکسی‌ها اسکرپ می‌کند."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # اگر وضعیت خطا بود (مثل 403, 404, 500)، استثنا ایجاد می‌کند
        
        soup = BeautifulSoup(response.content, 'html.parser')
        proxy_table = soup.find('table', class_='table-striped')
        
        if not proxy_table:
            # اگر جدول پیدا نشد، یک پیام خطا برمی‌گردانیم
            return None, "جدول پروکسی‌ها در صفحه پیدا نشد. (احتمالاً ساختار سایت تغییر کرده است)"

        proxies = []
        rows = proxy_table.find_all('tr')
        # فقط ۱۰ پروکسی اول برای جلوگیری از طولانی شدن پیام
        for row in rows[1:11]: 
            cols = row.find_all('td')
            if len(cols) > 4:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                country = cols[2].text.strip()
                proxy_type = cols[4].text.strip()
                proxies.append(f"{ip}:{port} ({country} - {proxy_type})")
        
        if not proxies:
            return None, "جدول پیدا شد اما هیچ پروکسی‌ای در آن نبود."

        return proxies, "موفق"

    except requests.exceptions.RequestException as e:
        # اگر خطای شبکه یا HTTP رخ داد
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
    url = "https://gologin.com/free-proxy/"
    proxy_list, status_message = extract_proxies(url)
    
    if proxy_list:
        # فرمت کردن پیام برای ارسال
        message = "✅ **لیست پروکسی‌های جدید:**\n\n"
        message += "\n".join(f"`{p}`" for p in proxy_list)
        send_to_telegram(message)
    else:
        # ارسال پیام خطا با جزئیات بیشتر
        error_message = f"❌ دریافت لیست پروکسی‌ها ناموفق بود.\n\n**دلیل:** {status_message}"
        send_to_telegram(error_message)
