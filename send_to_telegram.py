import os
import requests

# Забираем ключи из настроек GitHub
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TARGET_FILE = "proxies.txt"

def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("[-] Ошибка: BOT_TOKEN или CHAT_ID не заданы в переменных окружения.")
        return

    if not os.path.exists(TARGET_FILE):
        print(f"[-] Ошибка: Файл {TARGET_FILE} не найден.")
        return

    # Читаем готовый файл с отчеканными прокси
    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        # Убираем пустые строки
        links = [line.strip() for line in f if line.strip()]

    if not links:
        print("[-] В файле не найдено рабочих прокси. Отправлять нечего.")
        return

    # Берем первые 10 ссылок, чтобы сообщение в Telegram выглядело аккуратно
    top_links = links[:10]

    # Формируем текст
    text = f"✅ **Прокси обновлены!**\nВсего найдено рабочих: {len(links)}\nВот свежие ссылки для подключения:"
    
    # Создаем инлайн-кнопки
    keyboard = {"inline_keyboard": []}
    for i, link in enumerate(top_links, 1):
        keyboard["inline_keyboard"].append([{"text": f"🔌 Подключить прокси #{i}", "url": link}])

    # Отправляем запрос к API Telegram
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": keyboard
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"[+] Успешно отправлено {len(top_links)} прокси в Telegram!")
    except Exception as e:
        print(f"[-] Ошибка при отправке в Telegram: {e}")

if __name__ == "__main__":
    main()
