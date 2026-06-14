import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TARGET_FILE = "proxies.txt"

def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("[-] Ошибка: BOT_TOKEN или CHAT_ID не заданы.")
        return

    if not os.path.exists(TARGET_FILE):
        print(f"[-] Ошибка: Файл {TARGET_FILE} не найден.")
        return

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]

    if not links:
        print("[-] В файле не найдено рабочих прокси.")
        return

    # Формируем текст сообщения
    text = f"✅ **Прокси обновлены!**\nВсего найдено рабочих: {len(links)}\nНажми для подключения:"
    
    # Создаем инлайн-клавиатуру: по 3 кнопки в один ряд
    keyboard = {"inline_keyboard": []}
    row = []
    
    for i, link in enumerate(links, 1):
        row.append({"text": f"🔌 #{i}", "url": link})
        
        # Как только набралось 3 кнопки в ряд или ссылки закончились — добавляем ряд
        if len(row) == 3 or i == len(links):
            keyboard["inline_keyboard"].append(row)
            row = []

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
        print(f"[+] Успешно отправлено все {len(links)} прокси в Telegram!")
    except Exception as e:
        print(f"[-] Ошибка при отправке в Telegram: {e}")

if __name__ == "__main__":
    main()
