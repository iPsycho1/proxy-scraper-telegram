import requests
import os
import re
import time
import concurrent.futures
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- ثابت‌های پروژه ---
GOLOGIN_URL = "https://gologin.com/free-proxy/"
TEST_URL = "http://httpbin.org/ip"
MAX_THREADS = 10  # به دلیل مصرف بالای منابع در Selenium، تعداد را کمتر می‌کنیم
TIMEOUT = 15

def escape_markdown_v2(text):
    """تمام کاراکترهای خاص را برای MarkdownV2 تلگرام escape می‌کند."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def fetch_proxies_from_gologin():
    """لیست پروکسی‌ها را با استفاده از Selenium از سایت gologin استخراج می‌کند."""
    print("راه‌اندازی مرورگر Chrome در حالت headless...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    potential_proxies = []
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(GOLOGIN_URL)
        print(f"صفحه {GOLOGIN_URL} باز شد.")

        # منتظر ماندن برای دکمه فیلتر HTTP و کلیک روی آن
        wait = WebDriverWait(driver, 20) # تا ۲۰ ثانیه صبر می‌کند
        http_filter_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//label[contains(., 'HTTP')]")))
        http_filter_button.click()
        print("روی فیلتر HTTP کلیک شد. منتظر بارگذاری جدول...")
        
        # کمی صبر می‌کنیم تا جدول به طور کامل بارگذاری شود
        time.sleep(5)

        # دریافت سورس صفحه بعد از اجرای جاوا اسکریپت
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        proxy_table = soup.find('table', class_='table-striped')
        if proxy_table:
            rows = proxy_table.find('tbody').find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) > 1:
                    proxy_address = cols[0].text.strip()
                    potential_proxies.append(proxy_address)
            print(f"تعداد {len(potential_proxies)} پروکسی از جدول استخراج شد.")
        else:
            print("جدول پروکسی‌ها در صفحه پیدا نشد.")
            
    except Exception as e:
        print(f"خطا در فرآیند Selenium: {e}")
    finally:
        if driver:
            driver.quit()
            
    return potential_proxies

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
    CHANNEL_LINK = "https://t.me/YourChannelLink"
    FOOTER_TEXT = "📣 با معرفی کانال و اشتراک پست ها با دوستان خود، ما را حمایت کنید ❤️"
    
    potential_proxies = fetch_proxies_from_gologin()
    
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
            header = f"✅ *تست کامل شد\\! {len(proxies_to_send)} پروکسی فعال از GoLogin پیدا شد:*\n\n"
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
