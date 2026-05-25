import requests
import time
import re  # Библиотека для поиска ссылок прямо в HTML-коде

def fetch_proxies(file_path):
    links = set()
    print("📁 Собираем прокси с нуля.")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html, */*",
        "Referer": "https://mtprotoproxy.app/ru/",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    # === ШАГ 1: Охота на отборные прокси с главной страницы ===
    print("🌟 Ищем 'отборные' прокси прямо на главной...")
    try:
        main_page = requests.get("https://mtprotoproxy.app/ru/", headers=headers)
        
        # Магия регулярных выражений: ищем всё, что начинается с tg://proxy? 
        # и продолжается до любой кавычки, пробела или скобки.
        featured = re.findall(r'tg://proxy\?[^"\'\s<>]+', main_page.text)
        
        for link in featured:
            links.add(link)
            
        print(f"✨ С главной страницы вытащено ссылок (включая отборные): {len(featured)}")
    except Exception as e:
        print(f"❌ Ошибка при поиске на главной: {e}")

    # === ШАГ 2: Собираем основной массив через API ===
    page = 1
    print("⏳ Начинаю сбор массовых прокси по API...")
    
    while True:
        try:
            url = f"https://mtprotoproxy.app/api/proxies?page={page}"
            print(f"➡️ Отправляю запрос API: {url}")
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Сервер отклонил запрос API. Код: {response.status_code}")
                break
                
            try:
                data = response.json()
            except Exception as e:
                print(f"❌ Не удалось прочитать JSON: {e}")
                break
                
            if not data.get('ok') or not data.get('items'):
                break
                
            for item in data['items']:
                link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                links.add(link)
                
            print(f"✅ Страница {page} API успешно обработана.")
            
            if not data.get('has_more'):
                print("🏁 Это была последняя страница API.")
                break
                
            page += 1
            time.sleep(1.5)
            
        except Exception as e:
            print(f"❌ Критическая ошибка сети API: {e}")
            break

    # Жестко перезаписываем файл
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(links))
        
    print(f"🎯 ИТОГ: Сохранено {len(links)} уникальных прокси (Включая отборные!).")

if __name__ == "__main__":
    fetch_proxies("proxies.txt")
