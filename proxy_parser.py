import requests
import time

def fetch_proxies(file_path):
    links = set() # Используем set, чтобы автоматически исключить дубликаты
    
    # 1. Читаем прокси, которые УЖЕ лежат в твоем файле перед тестом
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    links.add(line.strip())
    except FileNotFoundError:
        pass
        
    page = 1
    print("⏳ Начинаю сбор новых прокси...")
    
    # 2. Добавляем к ним новые с сайта
    while True:
        try:
            url = f"https://mtprotoproxy.app/api/proxies?page={page}"
            response = requests.get(url)
            data = response.json()
            
            if not data.get('ok') or not data.get('items'):
                break
                
            for item in data['items']:
                link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                links.add(link)
                
            if not data.get('has_more'):
                break
                
            page += 1
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Ошибка сети: {e}")
            break

    # 3. Перезаписываем твой файл общим списком (старые + новые)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(links))
        
    print(f"✅ Готово! Всего уникальных прокси в файле для теста: {len(links)}")

if __name__ == "__main__":
    # ВАЖНО: замени "proxies.txt" на точное имя твоего текстового файла в репозитории
    fetch_proxies("proxies.txt")
