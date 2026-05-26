import requests
import time
import re
import socket
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

def check_proxy_tcp(link, timeout=0.2):
    """Проверяет доступность прокси по TCP с заданным таймаутом."""
    try:
        # Парсим server и port из ссылки tg://proxy?server=...&port=...
        parsed = urlparse(link.replace("tg://", "http://"))
        query_params = parse_qs(parsed.query)
        
        server = query_params.get('server', [None])[0]
        port = query_params.get('port', [None])[0]
        
        if not server or not port:
            return None
            
        # Пытаемся открыть TCP-соединение
        with socket.create_connection((server, int(port)), timeout=timeout):
            return link
    except (socket.timeout, socket.error, ValueError, TypeError):
        return None

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
        main_page = requests.get("https://mtprotoproxy.app/ru/", headers=headers, timeout=20)
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
            print(f"➡️ Отправляю запрос API: {url}")
            response = requests.get(url, headers=headers, timeout=20)
            
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

    print(f"🔍 Всего собрано уникальных ссылок: {len(links)}")

    # === ШАГ 3: Фильтрация по TCP ===
    print("⚡ Начинаем проверку доступности по TCP (таймаут 0.2с)...")
    working_links = set()
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(check_proxy_tcp, links)
        for result in results:
            if result:
                working_links.add(result)
                
    sorted_links = sorted(list(working_links))
    print(f"🎯 ИТОГ: Проверку прошли {len(sorted_links)} из {len(links)} прокси.")

    # === ШАГ 4: Запись в текстовый файл proxies.txt ===
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted_links))
    print(f"💾 Сохранено {len(sorted_links)} рабочих прокси в файл {file_path}.")

    # === Получаем текущее время для обновления сайта ===
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    # === ШАГ 5: Автоматическая генерация HTML ===
    print("🌐 Начинаем автоматическое обновление index.html...")
    
    html_template = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MTProto Proxies</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            padding: 15px;
            max-width: 800px;
            margin: 0 auto;
        }}
        .header-container {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #ddd;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .title-block h2 {{ margin: 0; color: #333; font-size: 20px; }}
        .title-block .update-time {{ font-size: 12px; color: #777; margin-top: 4px; }}
        .counter {{
            background-color: #2e7d32;
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }}
        .proxy-grid {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .proxy-link {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            flex: 1 1 calc(33.333% - 10px);
            min-width: 140px;
            background-color: #0088cc;
            color: white;
            padding: 12px 8px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            font-size: 14px;
            box-sizing: border-box;
            transition: background-color 0.2s;
        }}
        .ping-text {{ display: none; }}
        .proxy-link:active {{ background-color: #006699; }}
        .proxy-link.clicked {{ background-color: #d9534f; }}
        @media (max-width: 600px) {{ .proxy-link {{ flex: 1 1 calc(50% - 10px); }} }}
        @media (max-width: 360px) {{ .proxy-link {{ flex: 1 1 100%; }} }}
    </style>
</head>
<body>

    <div class="header-container">
        <div class="title-block">
            <h2>MTProto Прокси</h2>
            <div class="update-time">Обновлено: {current_time}</div>
        </div>
        <div class="counter">Работает: {len(sorted_links)}</div>
    </div>

    <div class="proxy-grid">
"""

    for i, proxy in enumerate(sorted_links, 1):
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
    print(f"✅ Файл index.html успешно сгенерирован! Время: {current_time}.")

if __name__ == "__main__":
    fetch_proxies("proxies.txt")
