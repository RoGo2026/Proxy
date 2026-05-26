import requests
import time
import re
import socket

def check_proxy(proxy_link):
    """Проверяет прокси с логированием."""
    match = re.search(r'server=([^&]+)&port=(\d+)', proxy_link)
    if not match: 
        return False, "Неверный формат"
    
    address, port = match.group(1), int(match.group(2))
    
    # Пробуем подключиться 2 раза с разным таймаутом
    for timeout in [2.0, 3.0]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((address, port))
                # Отправляем пустой байт для проверки MTProto
                s.send(b'\x00')
                return True, "OK"
        except socket.timeout:
            continue
        except Exception as e:
            continue
    
    return False, f"Не отвечает"

def main():
    links = set()
    headers = {"User-Agent": "Mozilla/5.0"}
    working = []
    failed_details = []
    
    # Сбор прокси
    print("⏳ Собираю прокси...")
    try:
        main_page = requests.get("https://mtprotoproxy.app/ru/", headers=headers, timeout=10)
        found = re.findall(r'tg://proxy\?[^"\'\s<>]+', main_page.text)
        links.update(found)
        print(f"✅ Найдено через HTML: {len(found)}")
    except Exception as e:
        print(f"❌ Ошибка сбора: {e}")
        return
    
    if not links:
        print("⚠️ Прокси не найдены!")
        return
    
    # Проверка с логированием
    print(f"\n🔍 Проверяю {len(links)} прокси...")
    for i, link in enumerate(links, 1):
        is_works, reason = check_proxy(link)
        
        if is_works:
            working.append(link)
            print(f"  [{i}/{len(links)}] ✅ РАБОЧАЯ")
        else:
            failed_details.append((link, reason))
            if i % 10 == 0:
                print(f"  [{i}/{len(links)}] ❌ {reason}")
        
        time.sleep(0.1)  # Небольшая пауза между проверками
    
    print(f"\n📊 Результаты:")
    print(f"  ✅ Рабочих: {len(working)}")
    print(f"  ❌ Нерабочих: {len(failed_details)}")
    
    # Показываем первые 5 нерабочих для отладки
    if failed_details:
        print(f"\n📋 Примеры нерабочих:")
        for link, reason in failed_details[:5]:
            # Извлекаем server:port для отображения
            match = re.search(r'server=([^&]+)&port=(\d+)', link)
            if match:
                print(f"  {match.group(1)}:{match.group(2)} - {reason}")
    
    # Генерация HTML
    html_links = "\n".join([f'<li><a href="{p}">Подключить #{i+1}</a></li>' for i, p in enumerate(working)])
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MTProto Прокси</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; }}
a {{ display: block; padding: 0.5rem; margin: 0.5rem 0; background: #0088cc; color: white; text-decoration: none; border-radius: 4px; }}
a:hover {{ background: #0099dd; }}
</style>
</head>
<body>
<h1>MTProto Прокси</h1>
<p>Рабочих прокси: {len(working)}</p>
<ul>{html_links}</ul>
<p><small>Обновлено: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}</small></p>
</body>
</html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    with open("proxies.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(working))
    
    print(f"\n✅ Готово! HTML обновлен.")

if __name__ == "__main__":
    main()
