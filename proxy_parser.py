import requests
import time
import re
import socket

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # Собираем прокси со всех страниц HTML
    print("⏳ Собираю прокси...")
    try:
        main_page = requests.get("https://mtprotoproxy.app/ru/", headers=headers, timeout=15)
        found = re.findall(r'tg://proxy\?server=[^&]+&port=\d+&secret=[a-zA-Z0-9]+', main_page.text)
        links.update(found)
        print(f"✅ Собрано со страницы: {len(found)}")
    except Exception as e:
        print(f"❌ Ошибка сбора: {e}")
    
    # Если HTML не сработал — пробуем API
    if not links:
        print("🔄 Пробую API...")
        try:
            for page in range(1, 6):
                resp = requests.get(f"https://mtprotoproxy.app/api/proxies?page={page}", headers=headers, timeout=10)
                data = resp.json()
                if not data.get('items'):
                    break
                for item in data['items']:
                    link = f"tg://proxy?server={item['server']}&port={item['port']}&secret={item['secret']}"
                    links.add(link)
                time.sleep(0.5)
            print(f"✅ Собрано через API: {len(links)}")
        except Exception as e:
            print(f"❌ API ошибка: {e}")
    
    if not links:
        print("⚠️ Прокси не найдены")
        return
    
    # Проверяем
    print(f"🔍 Проверяю {len(links)} прокси...")
    for i, link in enumerate(links, 1):
        if check_proxy(link):
            working.append(link)
            print(f"  [{i}/{len(links)}] ✅")
        if i % 20 == 0:
            print(f"  ... {i}/{len(links)}")
    
    print(f"✅ Рабочих: {len(working)} из {len(links)}")
    
    # Сохраняем ТОЛЬКО рабочие
    with open("proxies.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(working))
    
    # Удаляем all_proxies.txt если он был создан раньше
    import os
    if os.path.exists("all_proxies.txt"):
        os.remove("all_proxies.txt")
    
    # Генерируем HTML
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
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ margin: 0.5rem 0; }}
        a {{ display: block; padding: 0.75rem; background: #0088cc; color: white; text-decoration: none; border-radius: 6px; text-align
