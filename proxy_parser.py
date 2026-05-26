import requests
import time
import re
import socket

def check_proxy(proxy_link):
    """Проверяет, отвечает ли сервер прокси по указанному адресу и порту."""
    match = re.search(r'server=([^&]+)&port=(\d+)', proxy_link)
    if not match:
        return False
        
    address = match.group(1)
    port = int(match.group(2))
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)  # Ждем ответа максимум 2 секунды
            s.connect((address, port))
        return True
    except Exception:
        return False

def fetch_proxies(file_path):
    links = set()
    print("📁 Собираем прокси с нуля.")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html, */*",
        "Referer": "https://mtprotoproxy.app/ru/",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    # === ШАГ 1: Сбор с главной страницы ===
    print("🌟 Ищем 'отборные' прокси прямо на главной...")
    try:
        main_page = requests.get("https://mtprotoproxy.app/ru/", headers=headers)
        featured = re.findall(r'tg://proxy\?[^"\'\s<>]+', main_page.text)
        for link in featured:
            links.add(link)
        print(f"✨ С главной страницы вытащено ссылок: {len(featured)}")
    except Exception as e:
        print(f"⚠️ Ошибка при чтении главной страницы: {e}")
        
    # === ШАГ 2: Сбор через API ===
    page = 1
    while True:
        try:
            url = f"https://mtprotoproxy.app/api/proxies?page={page}"
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                break
                
            try:
                data = response.json()
            except Exception:
                break
                
            if not data.get('ok') or not data.get('items'):
                break
                
            for item in data['items']:
                link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                links.add(link)
                
            if not data.get('has_more'):
                break
                
            page += 1
            time.sleep(1.5)
            
        except Exception:
            break

    # === ШАГ 3: Жесткая проверка на работоспособность ===
    print(f"🔍 Найдено {len(links)} прокси. Начинаю проверку на работоспособность (Пинг)...")
    working_proxies = []
    
    for proxy in sorted(list(links)):
        if check_proxy(proxy):
            working_proxies.append(proxy)
            
    print(f"🎯 ИТОГ ПРОВЕРКИ: Из {len(links)} выжило {len(working_proxies)}.")

    # === ШАГ 4: Запись только живых прокси в файл ===
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(working_proxies))
    print("🧹 Файл proxies.txt перезаписан (только рабочие).")

    if not working_proxies:
        print("⚠️ Нет рабочих прокси для обновления сайта.")
        return

    # === ШАГ 5: Автоматическое обновление сайта ===
    print("🌐 Начинаем автоматическое обновление index.html...")
    
    html_template = f"""<!DOCTYPE html>
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
        .proxy-link {{ display: flex; flex-direction: column; justify-content: center; align-items: center; flex: 1 1 calc(33.333% - 10px); min-width: 140px; background-color: #0088cc; color: white; padding: 12px 8px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; box-sizing: border-box; transition: background-color 0.2s; }}
        .ping-text {{ display: none; }}
        .proxy-link:active {{ background-color: #006699; }}
        .proxy-link.clicked {{ background-color: #d9534f; }}
        @media (max-width: 600px) {{ .proxy-link {{ flex: 1 1 calc(50% - 10px); }} }}
        @media (max-width: 360px) {{ .proxy-link {{ flex: 1 1 100%; }} }}
    </style>
</head>
<body>

    <div class="header-container">
        <h2>MTProto Прокси</h2>
        <div class="counter">Работает: {len(working_proxies)}</div>
    </div>

    <div class="proxy-grid">
"""

    for i, proxy in enumerate(working_proxies, 1):
        html_template += f'        <a href="{proxy}" class="proxy-link"><span>#{i} Подключить</span><span class="ping-text"></span></a>\n'

    html_template += """    </div>
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
        f.write(html_template)
    print("✅ Файл index.html успешно сгенерирован!")

if __name__ == "__main__":
    fetch_proxies("proxies.txt")
