import asyncio
import os
import time
import re
import requests
from telethon import TelegramClient

# === КЛЮЧИ ИЗ СЕКРЕТОВ GITHUB ===
api_id = int(os.environ.get('API_ID', 0))
api_hash = os.environ.get('API_HASH', '')
SESSION_FILE = 'my_session.session'
TIMEOUT_SEC = 4

if api_id == 0 or not api_hash:
    raise ValueError("Ошибка: не заданы API_ID или API_HASH. Проверьте секреты GitHub.")

# ------------------------------
# 1. СБОР ВСЕХ ПРОКСИ
# ------------------------------
def fetch_all_proxies(output_file):
    links = set()
    print("📁 Собираем все прокси (без проверки).")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/html, */*",
        "Referer": "https://mtprotoproxy.app/ru/",
    }
    try:
        main_page = requests.get("https://mtprotoproxy.app/ru/", headers=headers, timeout=15)
        featured = re.findall(r'tg://proxy\?[^"\'\s<>]+', main_page.text)
        for link in featured:
            links.add(link)
        print(f"✅ С главной: {len(featured)}")
    except Exception as e:
        print(f"⚠️ Ошибка главной: {e}")
    page = 1
    while True:
        try:
            url = f"https://mtprotoproxy.app/api/proxies?page={page}"
            print(f"➡️ API page {page}")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                break
            data = response.json()
            if not data.get('ok') or not data.get('items'):
                break
            for item in data['items']:
                link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                links.add(link)
            print(f"✅ Страница {page}: {len(data['items'])}")
            if not data.get('has_more'):
                break
            page += 1
            time.sleep(1.5)
        except Exception as e:
            print(f"❌ Ошибка API: {e}")
            break
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(links)))
    print(f"🎯 Собрано уникальных прокси: {len(links)} сохранено в {output_file}")

# ------------------------------
# 2. ПРОВЕРКА ЧЕРЕЗ TELETHON
# ------------------------------
async def check_single_proxy(client, proxy_link, semaphore):
    async with semaphore:
        start = time.time()
        try:
            await client.connect()
            if not await client.is_user_authorized():
                return None, None
            await client.get_me()
            latency = (time.time() - start) * 1000
            return proxy_link, latency
        except Exception:
            return None, None
        finally:
            if client.is_connected():
                await client.disconnect()

async def main_test():
    with open('all_proxies.txt', 'r') as f:
        proxy_links = [line.strip() for line in f if line.strip()]
    print(f"🚀 Проверяем {len(proxy_links)} прокси через Telethon (таймаут {TIMEOUT_SEC} сек)...")
    semaphore = asyncio.Semaphore(5)
    tasks = []
    for link in proxy_links:
        client = TelegramClient(SESSION_FILE, api_id, api_hash, proxy=link, timeout=TIMEOUT_SEC)
        tasks.append(asyncio.create_task(check_single_proxy(client, link, semaphore)))
    results = []
    for task in asyncio.as_completed(tasks):
        link, latency = await task
        if link:
            results.append((link, latency))
            print(f"✅ Рабочий: {link[:60]}... ({latency:.0f} мс)")
    results.sort(key=lambda x: x[1])
    working = [link for link, _ in results]
    with open("proxies.txt", "w") as f:
        f.write("\n".join(working))
    print(f"\n🏆 Рабочих прокси: {len(working)} из {len(proxy_links)}")
    generate_html(working)

def generate_html(proxies):
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MTProto Proxies</title>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 15px; max-width: 800px; margin: 0 auto; }}
        .header-container {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #ddd; padding-bottom: 10px; margin-bottom: 20px; }}
        h2 {{ margin: 0; color: #333; font-size: 20px; }}
        .counter {{ background-color: #2e7d32; color: white; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 14px; }}
        .proxy-grid {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .proxy-link {{ display: flex; flex-direction: column; justify-content: center; align-items: center; flex: 1 1 calc(33.333% - 10px); min-width: 140px; background-color: #0088cc; color: white; padding: 12px 8px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; transition: background-color 0.2s; }}
        .proxy-link:active {{ background-color: #006699; }}
        .proxy-link.clicked {{ background-color: #d9534f; }}
        @media (max-width: 600px) {{ .proxy-link {{ flex: 1 1 calc(50% - 10px); }} }}
        @media (max-width: 360px) {{ .proxy-link {{ flex: 1 1 100%; }} }}
    </style>
</head>
<body>
    <div class="header-container">
        <h2>MTProto Прокси</h2>
        <div class="counter">Работает: {len(proxies)}</div>
    </div>
    <div class="proxy-grid">
"""
    for i, proxy in enumerate(proxies, 1):
        html += f'        <a href="{proxy}" class="proxy-link"><span>#{i} Подключить</span><span class="ping-text"></span></a>\n'
    html += """    </div>
    <script>
        document.querySelectorAll('.proxy-link').forEach(button => {
            button.addEventListener('click', function() {
                this.classList.add('clicked');
            });
        });
    </script>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"🌐 index.html сгенерирован, кнопок: {len(proxies)}")

if __name__ == "__main__":
    fetch_all_proxies("all_proxies.txt")
    asyncio.run(main_test())
