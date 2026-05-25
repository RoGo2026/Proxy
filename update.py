import urllib.request
import socket
import time
from urllib.parse import parse_qs
import concurrent.futures
import re
import html

# --- НАСТРОЙКИ ---
# Впиши сюда юзернейм публичного телеграм-канала (без @)
CHANNEL_NAME = "YOUR_CHANNEL" # <-- Поменяй на нужный канал
TIMEOUT = 2.0 # Максимальное время ожидания ответа от сервера

def fetch_links_from_telegram(channel):
    """Парсит веб-версию публичного Telegram-канала и достает все ссылки на прокси"""
    url = f"https://t.me/s/{channel}"
    print(f"Подключаюсь к каналу: {url}")
    
    try:
        # Притворяемся браузером, чтобы Телеграм нас не заблокировал
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        response = urllib.request.urlopen(req)
        html_content = response.read().decode('utf-8')
    except Exception as e:
        print(f"Ошибка при загрузке канала: {e}")
        return []

    # Ищем все ссылки, которые начинаются на https://t.me/proxy?
    # Регулярное выражение ищет куски текста по паттерну
    pattern = r'(https://t\.me/proxy\?[^"\']+)'
    raw_links = re.findall(pattern, html_content)
    
    # Декодируем HTML-символы (например, &amp; превращаем обратно в &)
    clean_links = [html.unescape(link) for link in raw_links]
    
    # Удаляем дубликаты (в каналах часто репостят одни и те же ссылки)
    unique_links = list(set(clean_links))
    
    return unique_links

def normalize_link(link):
    """Превращает веб-ссылку в правильную ссылку для приложения tg://"""
    if "proxy?" in link:
        params = link.split("proxy?")[1]
        return f"tg://proxy?{params}"
    return None

def check_proxy(link):
    """Проверяет доступность порта сервера и возвращает пинг в мс."""
    try:
        if "?" not in link: return None
        
        query = link.split("?")[1]
        params = parse_qs(query)
        
        server = params.get("server", [None])[0]
        port_str = params.get("port", [None])[0]
        
        if not server or not port_str: return None
            
        port = int(port_str)
        
        start_time = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((server, port))
        
        ping_ms = int((time.time() - start_time) * 1000)
        return {"link": link, "ping": ping_ms}
        
    except Exception:
        return None

def fetch_and_generate():
    # 1. Забираем ссылки прямо из Телеграм-канала
    raw_proxies = fetch_links_from_telegram(CHANNEL_NAME)
    
    if not raw_proxies:
        print("Не удалось найти прокси в канале. Возможно, канал приватный или пустой.")
        return

    # 2. Приводим все ссылки к формату tg://
    tg_proxies = []
    for link in raw_proxies:
        clean_link = normalize_link(link)
        if clean_link:
            tg_proxies.append(clean_link)

    print(f"Найдено уникальных ссылок в канале: {len(tg_proxies)}. Начинаю проверку пинга...")

    # 3. Многопоточная проверка серверов
    working_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(check_proxy, tg_proxies)
        for result in results:
            if result is not None:
                working_proxies.append(result)

    # 4. Сортируем по пингу
    working_proxies.sort(key=lambda x: x["ping"])
    total_count = len(working_proxies)
    
    print(f"Осталось живых прокси: {total_count}")

    # 5. Формируем HTML
    html_content = f"""<!DOCTYPE html>
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
        h2 {{ margin: 0; color: #333; font-size: 20px; }}
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
        .ping-text {{ font-size: 11px; opacity: 0.8; margin-top: 4px; font-weight: normal; }}
        .proxy-link:active {{ background-color: #006699; }}
        .proxy-link.clicked {{ background-color: #d9534f; }}
        @media (max-width: 600px) {{ .proxy-link {{ flex: 1 1 calc(50% - 10px); }} }}
        @media (max-width: 360px) {{ .proxy-link {{ flex: 1 1 100%; }} }}
    </style>
</head>
<body>

    <div class="header-container">
        <h2>MTProto Прокси</h2>
        <div class="counter">Работает: {total_count}</div>
    </div>

    <div class="proxy-grid">
"""

    for index, item in enumerate(working_proxies, start=1):
        html_content += f'        <a href="{item["link"]}" class="proxy-link"><span>#{index} Подключить</span><span class="ping-text">Пинг: {item["ping"]} мс</span></a>\n'

    html_content += """    </div>
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
        f.write(html_content)
    
    print("Генерация сайта завершена!")

if __name__ == "__main__":
    fetch_and_generate()
