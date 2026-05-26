import requests
import time
import re
import socket

def check_proxy(proxy_link):
    """Проверка прокси: возвращает True, если сервер отвечает."""
    match = re.search(r'server=([^&]+)&port=(\d+)', proxy_link)
    if not match: return False
    address, port = match.group(1), int(match.group(2))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.5) # Ждем 1.5 сек
            s.connect((address, port))
        return True
    except: return False

def main():
    links = set()
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Сбор прокси
    print("⏳ Собираю прокси...")
    try:
        main_page = requests.get("https://mtprotoproxy.app/ru/", headers=headers)
        links.update(re.findall(r'tg://proxy\?[^"\'\s<>]+', main_page.text))
    except: pass
    
    # Фильтрация
    working = [p for p in links if check_proxy(p)]
    
    # Запись в proxies.txt
    with open("proxies.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(working))
    
    # Обновление index.html
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>MTProto</title></head>
<body>
    <h1>Рабочих прокси: {len(working)}</h1>
    <div>{"".join([f'<a href="{p}">Подключить #{i+1}</a><br>' for i, p in enumerate(working)])}</div>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Готово! Рабочих: {len(working)}")

if __name__ == "__main__":
    main()
