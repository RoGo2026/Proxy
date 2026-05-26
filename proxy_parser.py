import requests
import re
import socket
import time

def check_proxy(proxy_link):
    match = re.search(r'server=([^&]+)&port=(\d+)', proxy_link)
    if not match: return False
    address, port = match.group(1), int(match.group(2))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.5)
            s.connect((address, port))
        return True
    except: return False

def main():
    links = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    print("⏳ Пробую API...")
    try:
        url = "https://mtprotoproxy.app/api/proxies?page=1"
        response = requests.get(url, headers=headers, timeout=10)
        print(f"📡 Статус API: {response.status_code}")
        
        # Сохраняем ответ для отладки
        with open("api_response.txt", "w", encoding="utf-8") as f:
            f.write(response.text[:500])
        
        data = response.json()
        print(f"📋 Ответ API: {data}")
        
        if data.get('ok') and data.get('items'):
            for item in data['items']:
                link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                links.add(link)
            print(f"✅ Найдено через API: {len(links)}")
    except Exception as e:
        print(f"❌ API не сработал: {e}")
    
    # Fallback: парсинг HTML если API не дал результатов
    if len(links) == 0:
        print("🔄 Пробую HTML-парсинг...")
        try:
            main_page = requests.get("https://mtprotoproxy.app/ru/", headers=headers, timeout=10)
            found = re.findall(r'tg://proxy\?[^"\'\s<>]+', main_page.text)
            links.update(found)
            print(f"✅ Найдено через HTML: {len(found)}")
        except Exception as e:
            print(f"❌ HTML-парсинг не сработал: {e}")
    
    if len(links) == 0:
        print("⚠️ Прокси не найдены вообще!")
        # Создаем пустой HTML чтобы не ломать сайт
        html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>MTProto Прокси</title></head>
<body><h1>Прокси временно недоступны</h1><p>Попробуйте позже</p></body></html>"""
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html)
        return
    
    # Проверка рабочих
    working = []
    print(f"🔍 Проверяю {len(links)} прокси...")
    for i, link in enumerate(links):
        if check_proxy(link):
            working.append(link)
        if i % 10 == 0:
            print(f"  Проверено: {i}/{len(links)}")
    
    print(f"✅ Рабочих: {len(working)}")
    
    # Генерация HTML
    html_links = "\n".join([f'<li><a href="{p}">#{i+1}</a></li>' for i, p in enumerate(working)])
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><title>MTProto Прокси</title></head>
<body>
<h1>MTProto Прокси</h1>
<p>Рабочих: {len(working)}</p>
<ul>{html_links}</ul>
</body></html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    with open("proxies.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(working))

if __name__ == "__main__":
    main()
