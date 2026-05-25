import requests
import time

def fetch_proxies(file_path):
    links = set()
    print("📁 Собираем прокси с нуля (старые из файла будут удалены).")
        
    page = 1
    print("⏳ Начинаю сбор новых прокси с сайта...")
    
    # Максимальная маскировка под реального пользователя
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://mtprotoproxy.app/ru/",
        "Origin": "https://mtprotoproxy.app",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    while True:
        try:
            url = f"https://mtprotoproxy.app/api/proxies?page={page}"
            print(f"➡️ Отправляю запрос: {url}")
            response = requests.get(url, headers=headers)
            print(f"ℹ️ Код ответа сервера: {response.status_code}")
            
            # Если сайт нас заблокировал
            if response.status_code != 200:
                print(f"❌ Сервер отклонил запрос. Начало ответа:\n{response.text[:300]}")
                break
                
            try:
                data = response.json()
            except Exception as e:
                print(f"❌ Не удалось прочитать JSON: {e}")
                break
                
            # Если сайт вернул пустоту
            if not data.get('ok') or not data.get('items'):
                print(f"⚠️ API не вернуло прокси на странице {page}.")
                break
                
            for item in data['items']:
                link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                links.add(link)
                
            print(f"✅ Страница {page} успешно обработана.")
            
            if not data.get('has_more'):
                print("🏁 Это была последняя страница.")
                break
                
            page += 1
            time.sleep(1.5)
            
        except Exception as e:
            print(f"❌ Критическая ошибка сети: {e}")
            break

    # Жестко перезаписываем файл только новыми ссылками
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(links))
        
    print(f"🎯 ИТОГ: В файл сохранено {len(links)} абсолютно свежих прокси.")

if __name__ == "__main__":
    fetch_proxies("proxies.txt")
