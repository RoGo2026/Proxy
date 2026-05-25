import urllib.request
import socket
import time
from urllib.parse import parse_qs
import concurrent.futures

# Прямая ссылка на сырой текстовый файл
URL = "https://raw.githubusercontent.com/SoliSpirit/mtproto/master/all_proxies.txt"
TIMEOUT = 2.0 # Максимальное время ожидания ответа от сервера (в секундах)

def check_proxy(link):
    """Проверяет доступность порта сервера и возвращает пинг в мс. Если недоступен - возвращает None."""
    try:
        # Извлекаем параметры из ссылки (ищем server и port)
        if "?" not in link:
            return None
        
        query = link.split("?")[1]
        params = parse_qs(query)
        
        server = params.get("server", [None])[0]
        port_str = params.get("port", [None])[0]
        
        if not server or not port_str:
            return None
            
        port = int(port_str)
        
        # Засекаем время и пытаемся подключиться к порту (TCP Ping)
        start_time = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((server, port))
        
        # Считаем пинг в миллисекундах
        ping_ms = int((time.time() - start_time) * 1000)
        return {"link": link, "ping": ping_ms}
        
    except Exception:
        # Если таймаут, сервер не найден или порт закрыт — прокси мертв
        return None

def fetch_and_generate():
    try:
        response = urllib.request.urlopen(URL)
        lines = response.read().decode('utf-8').splitlines()
    except Exception as e:
        print(f"Ошибка при скачивании файла: {e}")
        return

    # Отфильтровываем пустые строки и переделываем ссылки в tg://
    raw_proxies = [line.strip() for line in lines if line.strip()]
    tg_proxies = []
    
    for link in raw_proxies:
        tg_link = link
        if tg_link.startswith("https://t.me/"):
            tg_link = tg_link.replace("https://t.me/", "tg://")
        elif tg_link.startswith("https://telegram.me/"):
            tg_link = tg_link.replace("https://telegram.me/", "tg://")
        tg_proxies.append(tg_link)

    print(f"Скачано ссылок: {len(tg_proxies)}. Начинаю проверку на работоспособность...")

    # Многопоточная проверка (проверяем сразу по 20 штук одновременно)
    working_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(check_proxy, tg_proxies)
        for result in results:
            if result is not None:
                working_proxies.append(result)

    # Сортируем рабочие прокси по пингу (от меньшего к большему)
    working_proxies.sort(key=lambda x: x["ping"])
    total_count = len(working_proxies)
    
    print(f"Осталось рабочих прокси: {total_count}")

    # Формируем HTML-каркас
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
        h2 {{
            margin: 0;
            color: #333;
            font-size: 20px;
        }}
        .counter {{
            background-color: #2e7d32; /* Сделали зеленым, раз они рабочие */
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }}
        .proxy-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .proxy-link {{
            display: block;
            flex: 1 1 calc(33.333% - 10px);
            min-width: 140px;
            background-color: #0088cc;
            color: white;
            padding: 12px 8px;
            text-decoration: none;
            border-radius: 6px;
            text-align: center;
            font-weight: bold;
            font-size: 14px;
            box-sizing: border-box;
            transition: background-color 0.2s;
            /* Добавили flex, чтобы красиво разместить текст и пинг */
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }}
        .ping-text {{
            font-size: 11px;
            opacity: 0.8;
            margin-top: 4px;
        }}
        .proxy-link:active {{
            background-color: #006699;
        }}
        .proxy-link.clicked {{
            background-color: #d9534f;
        }}
        @media (max-width: 600px) {{
            .proxy-link {{
                flex: 1 1 calc(50% - 10px);
            }}
        }}
        @media (max-width: 360px) {{
            .proxy-link {{
                flex: 1 1 100%;
            }}
        }}
    </style>
</head>
<body>

    <div class="header-container">
        <h2>MTProto Прокси</h2>
        <div class="counter">Работает: {total_count}</div>
    </div>

    <div class="proxy-grid">
"""

    # Добавляем каждую ссылку. Самые быстрые теперь сверху.
    for index, item in enumerate(working_proxies, start=1):
        html_content += f'        <a href="{item["link"]}" class="proxy-link"><span>#{index} Подключить</span><span class="ping-text">Пинг: {item["ping"]} мс</span></a>\n'

    # Закрываем сетку и добавляем JavaScript
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

    # Записываем результат в index.html
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("Генерация сайта завершена!")

if __name__ == "__main__":
    fetch_and_generate()
