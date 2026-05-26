import requests
import time
import re
import socket
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

def normalize_proxy_link(link: str) -> str:
    """Приводит ссылку к единому формату (заменяет &amp; на &)."""
    return link.replace("&amp;", "&")

def parse_proxy_from_link(link: str):
    """Извлекает server, port из tg://proxy ссылки."""
    link = normalize_proxy_link(link)
    parsed = urllib.parse.urlparse(link)
    params = urllib.parse.parse_qs(parsed.query)
    server = params.get('server', [None])[0]
    port = params.get('port', [None])[0]
    if server is None or port is None:
        raise ValueError("Неверный формат прокси-ссылки")
    return server, int(port)

def check_proxy_worker(proxy_link: str, timeout: float = 1.5) -> tuple:
    try:
        server, port = parse_proxy_from_link(proxy_link)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((server, port))
        # Отправляем первые 4 байта MTProto v2 (0xEF + три нуля)
        sock.send(b'\xef\x00\x00\x00')
        # Ждём ответа (хотя бы 1 байт)
        data = sock.recv(1024)
        sock.close()
        # Если получили ответ, считаем прокси рабочим
        return proxy_link, len(data) > 0
    except Exception:
        return proxy_link, False

def filter_working_proxies(proxy_links, timeout=1.5, max_workers=10):
    """Параллельно проверяет список прокси, возвращает только рабочие."""
    working = []
    total = len(proxy_links)
    print(f"🔍 Начинаем проверку {total} прокси (таймаут {timeout} сек)...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_link = {executor.submit(check_proxy_worker, link, timeout): link for link in proxy_links}
        for i, future in enumerate(as_completed(future_to_link), 1):
            link, is_working = future.result()
            if is_working:
                working.append(link)
            if i % 10 == 0 or i == total:
                print(f"   Прогресс: {i}/{total} | Рабочих: {len(working)}")
    print(f"✅ Проверка завершена. Рабочих прокси: {len(working)} из {total}")
    return working

def fetch_proxies(file_path):
    links = set()
    print("📁 Собираем прокси с нуля.")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html, */*",
        "Referer": "https://mtprotoproxy.app/ru/",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    # === ШАГ 1: главная страница ===
    print("🌟 Ищем 'отборные' прокси на главной...")
    try:
        main_page = requests.get("https://mtprotoproxy.app/ru/", headers=headers, timeout=15)
        featured = re.findall(r'tg://proxy\?[^"\'\s<>]+', main_page.text)
        for link in featured:
            links.add(link)
        print(f"✨ С главной страницы получено ссылок: {len(featured)}")
    except Exception as e:
        print(f"⚠️ Ошибка при чтении главной страницы: {e}")

    # === ШАГ 2: API ===
    page = 1
    while True:
        try:
            url = f"https://mtprotoproxy.app/api/proxies?page={page}"
            print(f"➡️ API запрос: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"❌ API вернул код {response.status_code}")
                break

            data = response.json()
            if not data.get('ok') or not data.get('items'):
                break

            for item in data['items']:
                link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                links.add(link)

            print(f"✅ Страница {page} обработана, получено {len(data['items'])} записей")
            if not data.get('has_more'):
                print("🏁 API больше не возвращает данных.")
                break
            page += 1
            time.sleep(1.5)
        except Exception as e:
            print(f"❌ Ошибка при обращении к API: {e}")
            break

    unique_links = list(links)
    print(f"📦 Собрано уникальных прокси: {len(unique_links)}")

    # === ШАГ 3: Проверка работоспособности ===
    working_links = filter_working_proxies(unique_links, timeout=3, max_workers=20)

    # === ШАГ 4: Сохраняем рабочие прокси в файл ===
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(working_links)))
    print(f"🎯 Рабочие прокси сохранены в {file_path} (всего {len(working_links)})")

    # === ШАГ 5: Генерация index.html ===
    print("🌐 Обновляем index.html...")
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
        <div class="counter">Работает: {len(working_links)}</div>
    </div>

    <div class="proxy-grid">
"""

    for i, proxy in enumerate(sorted(working_links), 1):
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
    print(f"✅ index.html обновлён, добавлено кнопок: {len(working_links)}")

if __name__ == "__main__":
    fetch_proxies("proxies.txt")
