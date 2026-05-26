import requests
import time
import re

def fetch_proxies(file_path):
    links = set()

    print("📁 Собираем прокси с нуля.")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/html, */*",
        "Referer": "https://mtprotoproxy.app/ru/",
        "Accept-Language": "ru-RU,ru;q=0.9"
    }

    # Главная страница
    try:
        main_page = requests.get(
            "https://mtprotoproxy.app/ru/",
            headers=headers,
            timeout=20
        )

        featured = re.findall(
            r'tg://proxy\?[^"\'\s<>]+',
            main_page.text
        )

        for link in featured:
            links.add(link)

        print(f"🌟 Найдено с главной: {len(featured)}")

    except Exception as e:
        print(f"❌ Ошибка главной страницы: {e}")

    # API
    page = 1

    while True:
        try:
            url = f"https://mtprotoproxy.app/api/proxies?page={page}"

            print(f"➡️ API page {page}")

            response = requests.get(
                url,
                headers=headers,
                timeout=20
            )

            if response.status_code != 200:
                print(f"❌ Status: {response.status_code}")
                break

            data = response.json()

            if not data.get("ok"):
                break

            items = data.get("items", [])

            if not items:
                break

            for item in items:
                link = (
                    f"tg://proxy?"
                    f"server={item['server']}"
                    f"&port={item['port']}"
                    f"&secret={item['secret']}"
                )

                links.add(link)

            print(f"✅ Страница {page}: {len(items)}")

            if not data.get("has_more"):
                break

            page += 1

            time.sleep(1.5)

        except Exception as e:
            print(f"❌ API ошибка: {e}")
            break

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(links)))

    print(f"🎯 Всего прокси: {len(links)}")


if __name__ == "__main__":
    fetch_proxies("proxies.txt")
