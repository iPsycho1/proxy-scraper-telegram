import requests
from bs4 import BeautifulSoup
import os

def extract_proxies(url):
    """صفحه وب را برای استخراج پروکسی‌ها اسکرپ می‌کند."""
    proxies = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        proxy_table = soup.find('table', class_='table-striped')

        if proxy_table:
            rows = proxy_table.find_all('tr')
            for row in rows[1:11]: # فقط ۱۰ پروکسی اول برای جلوگیری از طولانی شدن پیام
                cols = row.find_all('td')
                if len(cols) > 4:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    country = cols[2].text.strip()
                    proxy_type = cols[4].text.strip()
                    proxies.append(f"{ip}:{port} ({country} - {proxy_type})")
    except requests.exceptions.RequestException as e:
        print(f"خطا در دریافت پروکسی‌ها: {e}")
    return proxies

def send_to_telegram(message):
    """پیام را به کانال تلگرام ارسال می‌کند."""
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')

    if not bot_token or not chat_id:
        print("توکن ربات یا چت آیدی در متغیرهای محیطی تنظیم نشده است.")
        return

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        response = requests.post(api_url, data=payload, timeout=10)
        print(response.json())
    except Exception as e:
        print(f"خطا در ارسال پیام به تلگرام: {e}")

if __name__ == "__main__":
    url = "https://gologin.com/free-proxy/"
    proxy_list = extract_proxies(url)

    if proxy_list:
        # فرمت کردن پیام برای ارسال
        message = "✅ **لیست پروکسی‌های جدید:**\n\n"
        message += "\n".join(f"`{p}`" for p in proxy_list)

        send_to_telegram(message)
    else:
        send_to_telegram("❌ دریافت لیست پروکسی‌ها ناموفق بود.")

