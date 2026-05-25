import urllib.request
import socket
import time
from urllib.parse import parse_qs
import concurrent.futures

# ПРАВИЛЬНАЯ ссылка на сырой текст (raw)
URL = "https://raw.githubusercontent.com/Argh94/Proxy-List/main/MTProto.txt"
TIMEOUT = 2.0 # Максимальное время ожидания ответа от сервера

def normalize_link(link):
    """
    Универсальный преобразователь ссылок.
    Берет любую ссылку, находит параметры и делает из нее правильную tg://
    """
    link = link.strip()
    # Если в строке есть параметры прокси
    if "proxy?" in link:
        # Отрезаем всё, что было ДО "proxy?", и берем только правую часть с параметрами
        params = link.split("proxy?")[1]
        # Собираем идеальную ссылку для мобильного приложения
        return f"tg://proxy?{params}"
    
    # Если это не прокси (например, пустая строка или комментарий в файле)
    return None

def check_proxy(link):
    """Проверяет доступность порта сервера и возвращает пинг в мс."""
    try:
        if "?" not in link:
            return None
        
        query = link.split("?")[1]
        params = parse_qs(query)
        
        server = params.get("server", [None])[0]
        port_str = params.get("port", [None])[0]
        
        if not server or not port_str:
            return None
            
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
    try:
        response = urllib.request.urlopen(URL)
        lines = response.read().decode('utf-8').splitlines()
    except Exception as e:
        print(f"Ошибка при скачивании файла: {e}")
        return

    # 1. Читаем файл и приводим ВСЕ ссылки к единому формату tg://
    tg_proxies = []
    for line in lines:
        clean_link = normalize_link(line)
        if clean_link: # Если ссылка корректно преобразовалась
            tg_proxies.append(clean_link)

    print(f"Найдено ссылок в файле: {len(tg_proxies)}. Начинаю проверку пинга...")

    # 2. Многопоточная проверка серверов
    working_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(check_proxy, tg_proxies)
        for result in results:
            if result is not None:
                working_proxies.append(result)

    # 3. Сортируем по пингу
    working_proxies.sort(key=lambda x: x["ping"])
    total_count = len(working_proxies)
    
    print(f"Осталось живых прокси: {total_count}")

    # 4. Формируем HTML
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
