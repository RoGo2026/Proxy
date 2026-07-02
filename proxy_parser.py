import requests
import time
import re
import socket
import ssl
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

# =====================================================================
# НАСТРОЙКИ ЖЕСТКОГО ОТБОРА
# =====================================================================
MAX_PING_SECONDS = 0.6  # Максимальное время ответа. Все, что медленнее 600мс - удаляем.
SOCKET_TIMEOUT = 2.0    # Максимальное время на попытку подключения к порту

def check_proxy_elite(link):
    """
    Супер-жесткая проверка:
    1. Проверка Fake-TLS
    2. Измерение скорости (пинга) до миллисекунд
    3. Тест на удержание соединения (отправка мусорных данных)
    """
    try:
        parsed = urlparse(link.replace("tg://", "http://"))
        query_params = parse_qs(parsed.query)
        
        server = query_params.get('server', [None])[0]
        port = query_params.get('port', [None])[0]
        secret = query_params.get('secret', [None])[0]
        
        if not server or not port or not secret:
            return None
            
        if not secret.startswith("ee") or len(secret) <= 34:
            return None
            
        try:
            domain_hex = secret[34:]
            decoy_domain = bytes.fromhex(domain_hex).decode('utf-8')
        except Exception:
            return None 

        # Начинаем замер скорости
        start_time = time.time()
        
        sock = socket.create_connection((server, int(port)), timeout=SOCKET_TIMEOUT)
        
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # Проводим TLS-хендшейк
        secure_sock = context.wrap_socket(sock, server_hostname=decoy_domain)
        
        # Фиксируем время хендшейка
        ping_time = time.time() - start_time
        
        # ЖЕСТКИЙ ОТСЕВ 1: Если прокси слишком медленный - в мусор
        if ping_time > MAX_PING_SECONDS:
            secure_sock.close()
            return None
            
        # ЖЕСТКИЙ ОТСЕВ 2: Проверка на разрыв соединения (Drop Test)
        # Отправляем 64 случайных байта. Мертвый бэкенд сразу сбросит сокет.
        secure_sock.sendall(os.urandom(64))
        
        # Ставим микро-таймаут, чтобы проверить, не отвалился ли сервер
        secure_sock.settimeout(0.5)
        try:
            secure_sock.recv(1)
        except socket.timeout:
            # Таймаут здесь — это ХОРОШО. Значит сервер жив и держит соединение.
            pass
        except Exception:
            # Соединение сброшено сервером - бэкенд мертв
            secure_sock.close()
            return None
            
        secure_sock.close()
        return link
    except Exception:
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

    # === ШАГ 3: Элитная фильтрация (Пинг + Удержание) ===
    print(f"⚡ Начинаем ЖЕСТКУЮ проверку (Лимит пинга: {MAX_PING_SECONDS}с)...")
    working_links = set()
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(check_proxy_elite, links)
        for result in results:
            if result:
                working_links.add(result)
                
    sorted_links = sorted(list(working_links))
    print(f"🎯 ИТОГ: Элитную проверку прошли {len(sorted_links)} из {len(links)} прокси.")

    # === ШАГ 4: Запись в текстовый файл proxies.txt ===
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted_links))
    print(f"💾 Сохранено {len(sorted_links)} рабочих прокси в файл {file_path}.")

    # === Получаем текущее время для обновления сайта ===
    moscow_tz = timezone(timedelta(hours=3))
    current_time = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S MSK")

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

# =====================================================================
# БЛОК АВТОМАТИЧЕСКОЙ РАССЫЛКИ В ТЕЛЕГРАМ
# =====================================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
USERS_FILE = "users.txt"
PROXIES_FILE = "proxies.txt"

if BOT_TOKEN:
    print("🤖 Запуск модуля рассылки в Telegram...")
    
    known_users = set()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            known_users = set(line.strip() for line in f if line.strip())

    try:
        updates_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        res = requests.get(updates_url, timeout=10)
        if res.status_code == 200:
            updates = res.json().get("result", [])
            for update in updates:
                if "message" in update and "chat" in update["message"]:
                    chat_id = str(update["message"]["chat"]["id"])
                    known_users.add(chat_id)
    except Exception as e:
        print(f"❌ Не удалось проверить новые сообщения: {e}")

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(known_users)))

    if os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, "r", encoding="utf-8") as f:
            links = [line.strip() for line in f if line.strip()]
    else:
        links = []

    if links and known_users:
        text = f"✅ **Прокси обновлены!**\nВсего найдено рабочих: {len(links)}\n\nНажми на кнопку для подключения:"
        
        keyboard = {"inline_keyboard": []}
        row = []
        for i, link in enumerate(links, 1):
            row.append({"text": f"🔌 #{i}", "url": link})
            if len(row) == 3 or i == len(links):
                keyboard["inline_keyboard"].append(row)
                row = []

        send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
        for chat_id in known_users:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            }
            try:
                r = requests.post(send_url, json=payload, timeout=10)
                if r.status_code == 200:
                    print(f"   [+] Успешно отправлено пользователю: {chat_id}")
                else:
                    print(f"   [-] Ошибка отправки пользователю {chat_id}: {r.text}")
            except Exception as e:
                print(f"   [-] Ошибка связи при отправке пользователю {chat_id}: {e}")
    else:
        print("ℹ️ Рассылка отменена: либо нет прокси, либо боту еще никто никогда не писал.")
else:
    print("❌ Модуль рассылки не запущен: в Settings репозитория отсутствует BOT_TOKEN!")
