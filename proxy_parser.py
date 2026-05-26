import requests
import time
import re
import socket
import os

def check_proxy(proxy_link):
    match = re.search(r'server=([^&]+)&port=(\d+)', proxy_link)
    if not match:
        return False
    address, port = match.group(1), int(match.group(2))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((address, port))
        return True
    except:
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
    try:
        while page <= 10:
            url = f"https://mtprotoproxy.app/api/proxies?page={page}"
            response = requests.get(url, headers=headers, timeout=10)
            
            try:
                data = response.json()
            except ValueError:
                print(f"❌ Страница {page}: не JSON (Cloudflare)")
                break
            
            if not data.get('ok') or not data.get('items'):
                break
                
            for item in data['items']:
                link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                links.add(link)
                
            if not data.get('has_more'):
                break
                
            page += 1
            time.sleep(1)
    except Exception as e:
        print(f"❌ Ошибка API: {e}")
    
    # Fallback на HTML если API не сработал
    if not links:
        print("🔄 API не сработал, пробую HTML...")
        try:
            resp = requests.get("https://mtprotoproxy.app/ru/", headers=headers, timeout=10)
            found = re.findall(r'tg://proxy\?[^"\'\s<>]+', resp.text)
            links.update(found)
        except Exception as e:
            print(f"❌ HTML ошибка: {e}")
    
    if not links:
        print("⚠️ Прокси не найдены")
        return
    
    print(f"📦 Собрано: {len(links)}. Проверяю сокеты...")
    
    for i, link in enumerate(links, 1):
        if check_proxy(link):
            working.append(link)
            print(f"  [{i}/{len(links)}] ✅")
        if i % 20 == 0:
            print(f"  ... проверено {i}/{len(links)}")
    
    print(f"✅ Рабочих: {len(working)}")
    
    # Удаляем мусор
    if os.path.exists("all_proxies.txt"):
        os.remove("all_proxies.txt")
    
    # Сохраняем ТОЛЬКО рабочие прокси
    with open("proxies.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(working))
    
    # Генерируем HTML с https://t.me/proxy
    html_lines = []
    for i, p in enumerate(working):
        https_link = p.replace("tg://", "https://t.me/")
        html_lines.append(f'        <li><a href="{https_link}">Подключить #{i+1}</a></li>')
    
    html_content = "\n".join(html_lines)
    
    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MTProto Прокси</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ margin: 0.5rem 0; }}
        a {{ display: block; padding: 0.75rem; background: #0088cc; color: white; text-decoration: none; border-radius: 6px; text-align: center; }}
        a:hover {{ background: #0099dd; }}
    </style>
</head>
<body>
    <h1>MTProto Прокси</h1>
    <p>Рабочих прокси: <b>{len(working)}</b></p>
    <ul>
{html_content}
    </ul>
    <p><small>Обновлено: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}</small></p>
</body>
</html>'''
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print("✅ Готово! index.html и proxies.txt обновлены.")

if __name__ == "__main__":
    main()
