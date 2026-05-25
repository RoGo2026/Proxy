import requests
import time

def fetch_proxies(file_path):
    links = set()
    
    # 1. Читаем прокси, которые УЖЕ лежат в файле (если он есть)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    links.add(line.strip())
    except FileNotFoundError:
        pass
        
    page = 1
    print("⏳ Начинаю сбор новых прокси...")
    
    # МАскируемся под обычный браузер (Chrome на Windows 10)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }
    
    # 2. Собираем новые
    while True:
        try:
            url = f"https://mtprotoproxy.app/api/proxies?page={page}"
            response = requests.get(url, headers=headers)
            
            # Если сайт вернул страницу с защитой Cloudflare, а не JSON
            try:
                data = response.json()
            except ValueError:
                print("❌ Сайт вернул не JSON. Возможно, включилась защита от ботов (Cloudflare).")
                break
            
            if not data.get('ok') or not data.get('items'):
                print(f"⚠️ API не вернуло данные на странице {page}. Ответ сервера: {data}")
                break
                
            for item in data['items']:
                link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                links.add(link)
                
            if not data.get('has_more'):
                break
                
            page += 1
            time.sleep(1) # Увеличил паузу до 1 секунды, чтобы не злить защиту сайта
            
        except Exception as e:
            print(f"❌ Ошибка сети: {e}")
            break

    # 3. Перезаписываем файл
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(links))
        
    print(f"✅ Готово! Всего уникальных прокси в файле для теста: {len(links)}")

if __name__ == "__main__":
    fetch_proxies("proxies.txt")
