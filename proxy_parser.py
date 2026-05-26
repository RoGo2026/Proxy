import requests
import re
import socket
import time

def check_proxy(proxy_link):
    """Проверяет, отвечает ли сервер прокси по TCP."""
    match = re.search(r'server=([^&]+)&port=(\d+)', proxy_link)
    if not match:
        return False
    address, port = match.group(1), int(match.group(2))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((address, port))
        return True
    except Exception:
        return False

def main():
    links = set()
    working = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }

    print("⏳ Собираю прокси через API...")
    page = 1
    while True:
        try:
            url = f"https://mtprotoproxy.app/api/proxies?page={page}"
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()

            if not data.get('ok') or not data.get('items'):
                print(f"⚠️ Данные закончились на странице {page}.")
                break

            for item in data['items']:
                link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                links.add(link)

            if not data.get('has_more'):
                break

            page += 1
            time.sleep(1)  # Пауза, чтобы не получить блокировку
        except Exception as e:
            print(f"❌ Ошибка при сборе: {e}")
            break

    print(f"📦 Найдено уникальных прокси: {len(links)}. Начинаю проверку сокетов...")

    # Проверка рабочих прокси
    for i, link in enumerate(links, 1):
        if check_proxy(link):
            working.append(link)
        if i % 20 == 0:
            print(f"🔍 Проверено: {i}/{len(links)}")

    print(f"✅ Рабочих прокси: {len(working)}")

    # Генерация index.html
    html_links = "\n".join([
        f'        <li><a href="{p}">Подключить #{i+1}</a></li>' 
        for i, p in enumerate(working)
    ])
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MTProto Прокси</title>
    <style>body{{font-family:system-ui, sans-serif; max-width:600px; margin:2rem auto; padding:0 1rem;}}</style>
</head>
<body>
    <h1>MTProto Прокси</h1>
    <p>Рабочих прокси: {len(working)}</p>
    <ul>
{html_links}
    </ul>
    <p><small>Обновлено: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}</small></p>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    # Сохраняем сырой список (опционально, полезно для других скриптов)
    with open("proxies.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(working))

if __name__ == "__main__":
    main()
