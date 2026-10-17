import asyncio
import html
import os
import re
import socket
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

import requests
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# =====================================================================
# НАСТРОЙКИ
# =====================================================================
MESSAGES_LIMIT = 200
PROXIES_FILE = "proxies.txt"
POOL_FILE = "proxies_pool.txt"
USERS_FILE = "users.txt"

MIN_PROXIES = 20
MAX_PROXIES = 30
CHECK_LIMIT = 90
PING_TIMEOUT = 4
PING_WORKERS = 24

MTPROXY_API = "https://mtprotoproxy.app/api/proxies"
MTPROXY_PAGES = 10
PUBLIC_CHANNELS = [
    "proxyknight",
    "mtproxies",
    "tgproxylist",
    "freemtproxyru",
    "proxyfree",
    "mtproxyserver",
]

API_ID_RAW = os.getenv("TELETHON_API_ID", "").strip()
API_HASH = os.getenv("TELETHON_API_HASH", "").strip()
STRING_SESSION = os.getenv("TELETHON_SESSION", "").strip()
API_ID = int(API_ID_RAW) if API_ID_RAW.isdigit() else 0
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL = os.getenv("TELETHON_CHANNEL", "").strip()
TOPIC_ID = int(os.getenv("TELETHON_TOPIC_ID", "0").strip() or 0)
USERS_RAW = os.getenv("TELETHON_USERS", "").strip()
BROADCAST = os.getenv("BROADCAST", "1").strip().lower() not in ("", "0", "false", "no")

PROXY_RE = re.compile(r"(?:tg://|https://t\.me/)proxy\?[^\s<>\"']+", re.IGNORECASE)
SERVER_RE = re.compile(r"^[A-Za-z0-9._\-]+$")
SECRET_RE = re.compile(r"^[A-Za-z0-9_\-+/=]+$")
HTML_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/json,*/*",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

# =====================================================================
def parse_link(raw_link):
    link = html.unescape(raw_link).strip().rstrip(".,;)]}")
    if "?" not in link:
        return None

    params = {}
    for chunk in link.split("?", 1)[1].split("&"):
        if "=" in chunk:
            key, value = chunk.split("=", 1)
            params[key.strip().lower()] = value.strip()

    server = params.get("server", "").strip().rstrip(".").lower()
    port_raw = params.get("port", "").strip()
    secret = params.get("secret", "").strip()

    if not server or not SERVER_RE.match(server):
        return None
    if not port_raw.isdigit() or not 0 < int(port_raw) < 65536:
        return None
    if len(secret) < 16 or not SECRET_RE.match(secret):
        return None

    port = int(port_raw)
    link = f"tg://proxy?server={server}&port={port}&secret={secret}"
    return {"link": link, "server": server, "port": port, "secret": secret}


def load_pool():
    if not os.path.exists(POOL_FILE):
        return []
    with open(POOL_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def build_entries(topic_links, public_links):
    items = {}

    def add(raw_link, rank):
        parsed = parse_link(raw_link)
        if not parsed:
            return
        link = parsed["link"]
        current = items.get(link)
        if current is None:
            items[link] = {**parsed, "rank": rank, "order": len(items)}
        elif rank < current["rank"]:
            current["rank"] = rank
            current["order"] = len(items)

    for link in topic_links:
        add(link, 0)
    for link in public_links:
        add(link, 1)
    for link in load_pool():
        add(link, 2)

    ordered = sorted(items.values(), key=lambda item: (item["rank"], item["order"]))

    seen_secrets = set()
    seen_hosts = set()
    unique = []
    for item in ordered:
        host = f'{item["server"]}:{item["port"]}'
        if item["secret"] in seen_secrets or host in seen_hosts:
            continue
        seen_secrets.add(item["secret"])
        seen_hosts.add(host)
        unique.append(item)

    return unique


def is_alive(item):
    try:
        with socket.create_connection((item["server"], item["port"]), timeout=PING_TIMEOUT):
            return True
    except OSError:
        return False


def check_alive(items):
    with ThreadPoolExecutor(max_workers=PING_WORKERS) as pool:
        flags = list(pool.map(is_alive, items))

    alive = []
    dead = []
    for item, ok in zip(items, flags):
        (alive if ok else dead).append(item)

    return alive, dead


def interleave(groups):
    merged = []
    for i in range(max((len(group) for group in groups), default=0)):
        for group in groups:
            if i < len(group):
                merged.append(group[i])
    return merged


def build_pool(topic_links, public_links):
    unique = build_entries(topic_links, public_links)
    print(f"🧹 Уникальных ссылок после дедупликации: {len(unique)}")

    groups = [[item for item in unique if item["rank"] == rank] for rank in (0, 1, 2)]

    alive, dead = check_alive(interleave(groups)[:CHECK_LIMIT])
    print(f"🔌 Отвечают: {len(alive)} | Не отвечают: {len(dead)}")

    key = lambda item: (item["rank"], item["order"])
    alive = sorted(alive, key=key)
    dead = sorted(dead, key=key)

    if len(alive) >= MIN_PROXIES:
        pool = alive[:MAX_PROXIES]
    else:
        pool = alive + dead[: MIN_PROXIES - len(alive)]

    if len(pool) < MIN_PROXIES:
        print(f"❌ Набралось только {len(pool)} ссылок, нужно минимум {MIN_PROXIES}.")
        return []

    return pool

# =====================================================================
async def collect_topic():
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
        print("ℹ️ Тема Telegram пропущена, нет секретов: " + ", ".join(missing))
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
        for message in messages:
            text = message.text or ""
            if "proxy" not in text:
                continue
            for link in PROXY_RE.findall(text):
                link = link.replace("https://t.me/proxy?", "tg://proxy?")
                if link not in seen:
                    seen.add(link)
                    proxies.append(link)

        print(f"Уникальных прокси в теме: {len(proxies)}")
        return proxies
    except Exception as e:
        print(f"⚠️ Не удалось прочитать тему Telegram: {e}")
        return []
    finally:
        await client.disconnect()

# =====================================================================
def collect_public():
    links = []

    page = 1
    while page <= MTPROXY_PAGES:
        try:
            response = requests.get(
                f"{MTPROXY_API}?page={page}",
                headers={**HTML_HEADERS, "Referer": "https://mtprotoproxy.app/ru/"},
                timeout=20,
            )
            if response.status_code != 200:
                print(f"⚠️ mtprotoproxy.app page {page}: статус {response.status_code}")
                break

            data = response.json()
            if not data.get("ok"):
                break

            items = data.get("items") or []
            if not items:
                break

            for item in items:
                links.append(
                    f"tg://proxy?server={item.get('server', '')}"
                    f"&port={item.get('port', '')}"
                    f"&secret={item.get('secret', '')}"
                )

            if not data.get("has_more"):
                break
            page += 1
        except Exception as e:
            print(f"⚠️ mtprotoproxy.app page {page}: {e}")
            break

    print(f"🌐 mtprotoproxy.app: {len(links)} ссылок")

    for name in PUBLIC_CHANNELS:
        try:
            response = requests.get(f"https://t.me/s/{name}", headers=HTML_HEADERS, timeout=20)
            found = [
                link.replace("https://t.me/proxy?", "tg://proxy?")
                for link in PROXY_RE.findall(html.unescape(response.text))
            ]
            print(f"📢 t.me/{name}: {len(found)} ссылок")
            links.extend(found)
        except Exception as e:
            print(f"⚠️ t.me/{name}: {e}")

    return links

# =====================================================================
def save_site(links):
    with open(PROXIES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(links))
    with open(POOL_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(links))
    print(f"💾 Сохранено {len(links)} прокси в {PROXIES_FILE} и {POOL_FILE}.")

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

    for i, proxy in enumerate(links, 1):
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
    print(f"✅ index.html сгенерирован. Прокси: {len(links)}. Время: {current_time}.")

# =====================================================================
def collect_users():
    known_users = set()
    for part in re.split(r"[\s,;]+", USERS_RAW):
        if part:
            known_users.add(part)

    if not BOT_TOKEN:
        return known_users

    try:
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", timeout=10)
        if response.status_code == 200:
            for update in response.json().get("result", []):
                msg = update.get("message") or {}
                chat = msg.get("chat") or {}
                if "id" in chat:
                    known_users.add(str(chat["id"]))
    except Exception as e:
        print(f"⚠️ Не удалось проверить сообщения боту: {e}")

    return known_users


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(users)))
    print(f"👥 Пользователей в базе: {len(users)}")


def send_to_telegram(links, known_users):
    if not BROADCAST:
        print("ℹ️ Рассылка отключена (BROADCAST=0) — обновлён только сайт.")
        return
    if not BOT_TOKEN:
        print("ℹ️ Рассылка пропущена: BOT_TOKEN не задан.")
        return
    if not links:
        print("ℹ️ Рассылка отменена: прокси нет.")
        return
    if not known_users:
        print("ℹ️ Рассылка отменена: боту еще никто не писал.")
        return

    print("🤖 Отправляем прокси в Telegram...")
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    CHUNK_SIZE = 20

    def chunks(items, size):
        for i in range(0, len(items), size):
            yield items[i:i + size]

    for chat_id in sorted(known_users):
        parts = list(chunks(links, CHUNK_SIZE))
        total = len(parts)

        for idx, chunk_links in enumerate(parts, 1):
            if idx == 1:
                text = f"✅ **Прокси обновлены!**\nВсего прокси: {len(links)}\n\nНажми на кнопку для подключения:"
            else:
                text = f"Прокси ({idx}/{total}):"

            keyboard = {"inline_keyboard": []}
            row = []
            for i, link in enumerate(chunk_links, 1):
                row.append({"text": f"🔌 #{i}", "url": link})
                if len(row) == 3 or i == len(chunk_links):
                    keyboard["inline_keyboard"].append(row)
                    row = []

            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard,
            }
            try:
                r = requests.post(send_url, json=payload, timeout=10)
                if r.status_code == 200:
                    print(f"   [+] Отправлено пользователю: {chat_id} (часть {idx}/{total})")
                else:
                    print(f"   [-] Ошибка отправки {chat_id} (часть {idx}/{total}): {r.text}")
            except Exception as e:
                print(f"   [-] Ошибка связи при отправке {chat_id}: {e}")


async def main():
    topic_links = await collect_topic()
    public_links = collect_public()

    pool = build_pool(topic_links, public_links)
    if not pool:
        print("❌ Прокси недостаточно — сайт и рассылка пропущены.")
        return

    links = [item["link"] for item in pool]
    save_site(links)

    known_users = collect_users()
    save_users(known_users)
    send_to_telegram(links, known_users)

    print("✅ Готово!")


if __name__ == "__main__":
    asyncio.run(main())
