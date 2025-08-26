import requests
import os
import re
import concurrent.futures

# آدرس سایتی که برای تست پروکسی استفاده می‌شود
TEST_URL = "http://httpbin.org/ip"
# حداکثر تعداد پروکسی برای تست همزمان
MAX_THREADS = 20
# حداکثر زمان انتظار برای تست هر پروکسی (به ثانیه)
TIMEOUT = 15

# --- لیست منابع پروکسی ---
# برای استفاده از هر منبع، کافیست آن را از حالت کامنت خارج کرده و بقیه را کامنت کنید.

# منبع پیشنهادی فعلی: ProxyScrape
PROXY_LIST_URL = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http"

# منبع قبلی: TheSpeedX
# PROXY_LIST_URL = "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"

# یک منبع خوب دیگر از گیت‌هاب: jetkai
# PROXY_LIST_URL = "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt"


def escape_markdown_v2(text):
    """تمام کاراکترهای خاص را برای MarkdownV2 تلگرام escape می‌کند."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def fetch_proxies():
    """لیست اولیه پروکسی‌ها را از منبع انتخابی دریافت می‌کند."""
    try:
        print(f"در حال دریافت پروکسی از منبع: {PROXY_LIST_URL}")
        response = requests.get(PROXY_LIST_URL, timeout=15)
        response.raise_for_status()
        potential_proxies = response.text.splitlines()
        # حذف خطوط خالی احتمالی
        potential_proxies = [p.strip() for p in potential_proxies if p.strip()]
        print(f"تعداد {len(potential_proxies)} پروکسی از منبع اولیه دریافت شد.")
        return potential_proxies
    except Exception as e:
        print(f"خطا در استخراج لیست اولیه پروکسی‌ها: {e}")
        return []

def test_and_get_info(proxy_address):
    """یک پروکسی را تست می‌کند و در صورت فعال بودن، کشور آن را نیز پیدا می‌کند."""
    proxy_dict = {'http': f"http://{proxy_address}", 'https': f"https://{proxy_address}"}
    try:
        response = requests.get(TEST_URL, proxies=proxy_dict, timeout=TIMEOUT)
        if response.status_code == 200:
            print(f"✅ پروکسی فعال: {proxy_address}")
            ip_address = proxy_address.split(':')[0]
            info_response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
            country = info_response.json().get('country', 'Unknown') if info_response.status_code == 200 else 'N/A'
            return {'address': proxy_address, 'country': country}
    except Exception:
        print(f"❌ پروکسی غیرفعال: {proxy_address}")
    return None

def send_to_telegram(message):
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if not bot_token or not chat_id:
        print("توکن ربات یا چت آیدی تنظیم نشده است.")
        return
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'MarkdownV2', 'disable_web_page_preview': True}
        response = requests.post(api_url, data=payload, timeout=10)
        print("Telegram API Response:", response.json())
    except Exception as e:
        print(f"خطا در ارسال پیام به تلگرام: {e}")

if __name__ == "__main__":
    CHANNEL_LINK = "@Sueproxy1" # لینک کانال خود را ویرایش کنید
    FOOTER_TEXT = "📣 با معرفی کانال و اشتراک پست ها با دوستان خود، ما را حمایت کنید ❤️"
    
    potential_proxies = fetch_proxies()
    
    if not potential_proxies:
        send_to_telegram("❌ لیست اولیه پروکسی‌ها از سایت منبع دریافت نشد")
    else:
        active_proxies_with_info = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            future_to_proxy = {executor.submit(test_and_get_info, p): p for p in potential_proxies}
            for future in concurrent.futures.as_completed(future_to_proxy):
                result = future.result()
                if result:
                    active_proxies_with_info.append(result)
        
        if active_proxies_with_info:
            proxies_to_send = active_proxies_with_info[:50]
            header = f"✅ *تست کامل شد\\! {len(proxies_to_send)} پروکسی فعال پیدا شد:*\n\n"
            message_lines = []
            for p in proxies_to_send:
                escaped_address = escape_markdown_v2(p['address'])
                escaped_country_name = escape_markdown_v2(p['country'])
                line = f"\\- `{escaped_address}` — *{escaped_country_name}*"
                message_lines.append(line)
            
            escaped_footer = escape_markdown_v2(FOOTER_TEXT)
            footer = f"\n\n{escaped_footer}\n[{escape_markdown_v2(CHANNEL_LINK)}]({CHANNEL_LINK})"
            message = header + "\n".join(message_lines) + footer
            
            if len(message) > 4096:
                message = header + "\n".join(message_lines)
            
            send_to_telegram(message)
        else:
            send_to_telegram("❌ هیچ پروکسی فعالی پس از تست پیدا نشد")

