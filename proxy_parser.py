import requests
import time
import re
import socket
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def check_proxy_tcp(proxy_link: str, timeout: float = 0.2):
    """Проверяет только TCP соединение (порт открыт)."""
    try:
        server, port = parse_proxy_from_link(proxy_link)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start = time.perf_counter()
        sock.connect((server, port))
        elapsed = time.perf_counter() - start
        sock.close()
        return proxy_link, elapsed
    except Exception:
        return proxy_link, None

def filter_proxies(proxy_links, timeout=0.2, max_workers=20):
    results = []
    total = len(proxy_links)
    print(colored(f"\n🔌 Проверяем {total} прокси (TCP, таймаут {timeout}с)...", CYAN))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_link = {executor.submit(check_proxy_tcp, link, timeout): link for link in proxy_links}
        for i, future in enumerate(as_completed(future_to_link), 1):
            link, elapsed = future.result()
            if elapsed is not None:
                results.append((link, elapsed))
                print(f"   [{i}/{total}] {colored('✅ ПОРТ ОТКРЫТ', GREEN)} ({elapsed:.3f} сек)")
            else:
                print(f"   [{i}/{total}] {colored('❌ ПОРТ ЗАКРЫТ', RED)}")
    results.sort(key=lambda x: x[1])
    working = [link for link, _ in results]
    print(colored(f"\n🏆 Прокси с открытым портом: {len(working)} из {total}", CYAN))
    if working:
        print(colored(f"   Отсеяно (порт закрыт/таймаут): {total - len(working)}", YELLOW))
        for i, (link, t) in enumerate(results[:5], 1):
            short = link[:80] + "..." if len(link) > 80 else link
            print(f"      #{i}: {t:.3f} сек - {short}")
    return working

def fetch_all_proxies(output_file):
    links = set()
    print(colored("📁 Сбор всех прокси...", CYAN))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/html, */*",
        "Referer": "https://mtprotoproxy.app/ru/",
    }
    try:
        main_page = requests.get("https://mtprotoproxy.app/ru/", headers=headers, timeout=15)
        featured = re.findall(r'tg://proxy\?[^"\'\s<>]+', main_page.text)
        for link in featured:
            links.add(link)
        print(colored(f"✅ С главной: {len(featured)}", GREEN))
    except Exception as e:
        print(colored(f"⚠️ Ошибка главной: {e}", RED))

    page = 1
    while True:
        try:
            url = f"https://mtprotoproxy.app/api/proxies?page={page}"
            print(f"➡️ API page {page}")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                break
            data = response.json()
            if not data.get('ok') or not data.get('items'):
                break
            for item in data['items']:
                link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                links.add(link)
            print(colored(f"✅ Страница {page}: {len(data['items'])}", GREEN))
            if not data.get('has_more'):
                break
            page += 1
            time.sleep(1.5)
        except Exception as e:
            print(colored(f"❌ Ошибка API: {e}", RED))
            break

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(links)))
    print(colored(f"🎯 Собрано уникальных прокси: {len(links)} в {output_file}", CYAN))

def generate_html(proxies):
    html = f"""<!DOCTYPE html>
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
        .proxy-link {{ display: flex; flex-direction: column; justify-content: center; align-items: center; flex: 1 1 calc(33.333% - 10px); min-width: 140px; background-color: #0088cc; color: white; padding: 12px 8px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; transition: background-color 0.2s; }}
        .proxy-link:active {{ background-color: #006699; }}
        .proxy-link.clicked {{ background-color: #d9534f; }}
        @media (max-width: 600px) {{ .proxy-link {{ flex: 1 1 calc(50% - 10px); }} }}
        @media (max-width: 360px) {{ .proxy-link {{ flex: 1 1 100%; }} }}
    </style>
</head>
<body>
    <div class="header-container">
        <h2>MTProto Прокси</h2>
        <div class="counter">Работает: {len(proxies)}</div>
    </div>
    <div class="proxy-grid">
"""
    for i, proxy in enumerate(proxies, 1):
        html += f'        <a href="{proxy}" class="proxy-link"><span>#{i} Подключить</span><span class="ping-text"></span></a>\n'
    html += """    </div>
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
        f.write(html)
    print(colored(f"🌐 index.html сгенерирован, кнопок: {len(proxies)}", GREEN))

if __name__ == "__main__":
    fetch_all_proxies("all_proxies.txt")
    with open("all_proxies.txt", "r") as f:
        proxies = [line.strip() for line in f if line.strip()]
    working = filter_proxies(proxies, timeout=0.2, max_workers=20)
    with open("proxies.txt", "w") as f:
        f.write("\n".join(working))
    generate_html(working)
