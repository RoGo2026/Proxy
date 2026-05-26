import requests
import time
import re

def fetch_all_proxies(output_file):
    links = set()
    print("📁 Собираем все прокси (без проверки).")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html, */*",
        "Referer": "https://mtprotoproxy.app/ru/",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    # Главная страница
    try:
        main_page = requests.get("https://mtprotoproxy.app/ru/", headers=headers, timeout=15)
        featured = re.findall(r'tg://proxy\?[^"\'\s<>]+', main_page.text)
        for link in featured:
            links.add(link)
        print(f"✅ С главной страницы: {len(featured)}")
    except Exception as e:
        print(f"⚠️ Ошибка главной: {e}")
    
    # API
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
    print(f"🎯 Собрано уникальных прокси: {len(links)} (сохранено в {output_file})")

if __name__ == "__main__":
    fetch_all_proxies("all_proxies.txt")
