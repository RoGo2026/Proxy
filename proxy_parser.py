import asyncio
import os
import re
import sys
from datetime import datetime, timezone, timedelta

from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# =====================================================================
# НАСТРОЙКИ
# =====================================================================
MESSAGES_LIMIT = 5 
PROXIES_FILE = "proxies.txt"
USERS_FILE = "users.txt"

API_ID_RAW = os.getenv("TELETHON_API_ID", "").strip()
API_HASH = os.getenv("TELETHON_API_HASH", "").strip()
STRING_SESSION = os.getenv("TELETHON_SESSION", "").strip()
API_ID = int(API_ID_RAW) if API_ID_RAW.isdigit() else 0
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL = os.getenv("TELETHON_CHANNEL", "").strip()
TOPIC_ID = int(os.getenv("TELETHON_TOPIC_ID", "0").strip() or 0)

PROXY_RE = re.compile(r"tg://proxy\?[^\s<>]+")

# =====================================================================
async def collect_proxies():
    missing = []
    if not API_ID:
        missing.append("TELETHON_API_ID")
    if not API_HASH:
        missing.append("TELETHON_API_HASH")
    if not STRING_SESSION:
        missing.append("TELETHON_SESSION")
    if not CHANNEL:
        missing.append("TELETHON_CHANNEL")
    if not TOPIC_ID:
        missing.append("TELETHON_TOPIC_ID")
    if missing:
        print("❌ Ошибка: в Settings репозитория не заданы секреты:")
        for name in missing:
            print(f"   - {name}")
        return []

    print("📡 Подключаемся к Telegram...")
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()

    try:
        me = await client.get_me()
        print(f"👤 Аккаунт: {me.first_name} @{me.username}")

        channel = await client.get_entity(CHANNEL)
        print("📥 Скачиваем последние сообщения...")
        messages = await client.get_messages(channel, reply_to=TOPIC_ID, limit=MESSAGES_LIMIT)
        print(f"Скачано сообщений: {len(messages)}")

        proxies = []
        seen = set()
        proxy_msgs = 0
        for message in messages:
            text = message.text or ""
            if "tg://proxy" not in text:
                continue
            proxy_msgs += 1
            for link in PROXY_RE.findall(text):
                if link not in seen:
                    seen.add(link)
                    proxies.append(link)

        print(f"Сообщений с прокси: {proxy_msgs}")
        print(f"Уникальных прокси: {len(proxies)}")
        return proxies
    finally:
        await client.disconnect()

# =====================================================================
def save_site(links):
    with open(PROXIES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(links)))
    print(f"💾 Сохранено {len(links)} прокси в файл {PROXIES_FILE}.")

    moscow_tz = timezone(timedelta(hours=3))
    current_time = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S MSK")

    print("🌐 Генерируем index.html...")

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
        <div class="counter">Прокси: {len(links)}</div>
    </div>

    <div class="proxy-grid">
"""

    for i, proxy in enumerate(sorted(links), 1):
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
    print(f"✅ index.html сгенерирован. Время: {current_time}.")

# =====================================================================
def send_to_telegram(links):
    if not BOT_TOKEN:
        print("ℹ️ Рассылка пропущена: BOT_TOKEN не задан.")
        return

    print("🤖 Отправляем прокси в Telegram...")

    known_users = set()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            known_users = set(line.strip() for line in f if line.strip())

    import requests

    try:
        updates_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        res = requests.get(updates_url, timeout=10)
        if res.status_code == 200:
            for update in res.json().get("result", []):
                msg = update.get("message") or {}
                chat = msg.get("chat") or {}
                if "id" in chat:
                    known_users.add(str(chat["id"]))
    except Exception as e:
        print(f"⚠️ Не удалось проверить сообщения боту: {e}")

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(known_users)))

    if not links:
        print("ℹ️ Рассылка отменена: прокси нет.")
        return
    if not known_users:
        print("ℹ️ Рассылка отменена: боту еще никто не писал.")
        return

    text = f"✅ **Прокси обновлены!**\nВсего прокси: {len(links)}\n\nНажми на кнопку для подключения:"

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
            "reply_markup": keyboard,
        }
        try:
            r = requests.post(send_url, json=payload, timeout=10)
            if r.status_code == 200:
                print(f"   [+] Отправлено пользователю: {chat_id}")
            else:
                print(f"   [-] Ошибка отправки {chat_id}: {r.text}")
        except Exception as e:
            print(f"   [-] Ошибка связи при отправке {chat_id}: {e}")


async def main():
    links = await collect_proxies()
    if not links:
        print("❌ Прокси не найдены.")
        return
    save_site(links)
    send_to_telegram(links)
    print("✅ Готово!")


if __name__ == "__main__":
    asyncio.run(main())
