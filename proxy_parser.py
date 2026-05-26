import requests
import time
import re
import socket
import struct
import urllib.parse
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import time as time_module

# ANSI цвета для красивого вывода
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

def colored(text, color):
    return f"{color}{text}{RESET}"

def normalize_proxy_link(link: str) -> str:
    return link.replace("&amp;", "&")

def parse_proxy_from_link(link: str):
    link = normalize_proxy_link(link)
    parsed = urllib.parse.urlparse(link)
    params = urllib.parse.parse_qs(parsed.query)
    server = params.get('server', [None])[0]
    port = params.get('port', [None])[0]
    if server is None or port is None:
        raise ValueError("Неверный формат прокси-ссылки")
    return server, int(port)

def mtproto_ping_packet(ping_id=None):
    """Формирует сырой MTProto пакет для вызова req_ping (unencrypted режим)."""
    if ping_id is None:
        ping_id = random.getrandbits(64)
    
    # TL-конструктор для req_ping = 0x7abe77ec (little-endian)
    req_ping_code = 0x7abe77ec
    body = struct.pack('<Iq', req_ping_code, ping_id)  # code (4 байта) + ping_id (8 байт)
    
    # Заголовок unencrypted сообщения:
    # auth_key_id = 0 (8 байт)
    auth_key_id = b'\x00' * 8
    # msg_id = текущее время * 2^32 (уникальный идентификатор)
    msg_id = int((time_module.time() * 2**32)) & 0xFFFFFFFFFFFFFFFF
    seqno = 0
    length = len(body)
    
    header = struct.pack('<8sQII', auth_key_id, msg_id, seqno, length)
    return header + body, ping_id

def check_mtproto_ping(proxy_link: str, timeout: float = 0.5):
    """
    Проверяет прокси через отправку MTProto ping.
    Возвращает (ссылка, время_ответа_сек) если получен корректный pong,
    иначе (ссылка, None).
    """
    try:
        server, port = parse_proxy_from_link(proxy_link)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start = time_module.perf_counter()
        sock.connect((server, port))
        
        packet, ping_id = mtproto_ping_packet()
        sock.send(packet)
        
        # Читаем ответ: минимум 24 байта для заголовка + тело
        resp = sock.recv(1024)
        elapsed = time_module.perf_counter() - start
        
        if len(resp) < 24:
            sock.close()
            return proxy_link, None
        
        # Извлекаем длину тела (байты 20-23)
        body_len = struct.unpack('<I', resp[20:24])[0]
        if len(resp) < 24 + body_len:
            sock.close()
            return proxy_link, None
        
        body = resp[24:24+body_len]
        if len(body) < 12:
            sock.close()
            return proxy_link, None
        
        # Код pong должен быть 0x347773c5
        pong_code = struct.unpack('<I', body[:4])[0]
        if pong_code != 0x347773c5:
            sock.close()
            return proxy_link, None
        
        # Проверяем, что полученный ping_id совпадает с отправленным
        returned_ping_id = struct.unpack('<Q', body[4:12])[0]
        if returned_ping_id != ping_id:
            sock.close()
            return proxy_link, None
        
        sock.close()
        return proxy_link, elapsed
    
    except Exception:
        return proxy_link, None

def filter_mtproto_proxies(proxy_links, timeout=0.5, max_workers=20):
    """Параллельно проверяет прокси через MTProto ping."""
    results = []
    total = len(proxy_links)
    print(colored(f"\n🏓 Проверяем MTProto ping на {total} прокси (таймаут {timeout}с)...", CYAN))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_link = {executor.submit(check_mtproto_ping, link, timeout): link for link in proxy_links}
        for i, future in enumerate(as_completed(future_to_link), 1):
            link, elapsed = future.result()
            if elapsed is not None:
                results.append((link, elapsed))
                print(f"   [{i}/{total}] {colored('✅ PONG получен', GREEN)} ({elapsed:.3f} сек)")
            else:
                print(f"   [{i}/{total}] {colored('❌ Нет ответа/не MTProto', RED)}")
    
    # Сортируем по скорости ответа
    results.sort(key=lambda x: x[1])
    working_links = [link for link, _ in results]
    
    print(colored(f"\n🏆 Рабочих MTProto прокси: {len(working_links)} из {total}", CYAN))
    if working_links:
        print(colored(f"   Отсеяно: {total - len(working_links)} прокси", YELLOW))
        print(colored("   Топ-5 по скорости ответа:", CYAN))
        for i, (link, t) in enumerate(results[:5], 1):
            short_link = link[:80] + "..." if len(link) > 80 else link
            print(f"      #{i}: {t:.3f} сек - {short_link}")
    return working_links

def fetch_proxies(file_path):
    links = set()
    print(colored("📁 Собираем прокси с нуля.", CYAN))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html, */*",
        "Referer": "https://mtprotoproxy.app/ru/",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    # ШАГ 1: главная страница
    print(colored("\n🌟 Ищем 'отборные' прокси на главной...", CYAN))
    try:
        main_page = requests.get("https://mtprotoproxy.app/ru/", headers=headers, timeout=15)
        featured = re.findall(r'tg://proxy\?[^"\'\s<>]+', main_page.text)
        for link in featured:
            links.add(link)
        print(colored(f"✨ С главной страницы получено ссылок: {len(featured)}", GREEN))
    except Exception as e:
        print(colored(f"⚠️ Ошибка при чтении главной страницы: {e}", RED))

    # ШАГ 2: API
    page = 1
    while True:
        try:
            url = f"https://mtprotoproxy.app/api/proxies?page={page}"
            print(colored(f"\n➡️ API запрос: {url}", CYAN))
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(colored(f"❌ API вернул код {response.status_code}", RED))
                break
            data = response.json()
            if not data.get('ok') or not data.get('items'):
                break
            for item in data['items']:
                link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                links.add(link)
            print(colored(f"✅ Страница {page} обработана, получено {len(data['items'])} записей", GREEN))
            if not data.get('has_more'):
                print(colored("🏁 API больше не возвращает данных.", CYAN))
                break
            page += 1
            time.sleep(1.5)
        except Exception as e:
            print(colored(f"❌ Ошибка при обращении к API: {e}", RED))
            break

    unique_links = list(links)
    print(colored(f"\n📦 Собрано уникальных прокси: {len(unique_links)}", CYAN))

    # ШАГ 3: Проверка через MTProto ping (таймаут 0.2 сек)
    working_links = filter_mtproto_proxies(unique_links, timeout=0.2, max_workers=20)

    # ШАГ 4: Сохраняем в файл
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(working_links)))
    print(colored(f"\n🎯 Рабочие прокси сохранены в {file_path} (всего {len(working_links)})", GREEN))

    # ШАГ 5: Генерация index.html
    print(colored("🌐 Обновляем index.html...", CYAN))
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
    print(colored(f"✅ index.html обновлён, добавлено кнопок: {len(working_links)}", GREEN))

if __name__ == "__main__":
    fetch_proxies("proxies.txt")
