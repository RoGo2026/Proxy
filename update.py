import urllib.request

# Прямая ссылка на сырой текстовый файл
URL = "https://raw.githubusercontent.com/SoliSpirit/mtproto/master/all_proxies.txt"

def fetch_and_generate():
    try:
        # Скачиваем содержимое
        response = urllib.request.urlopen(URL)
        lines = response.read().decode('utf-8').splitlines()
    except Exception as e:
        print(f"Ошибка при скачивании файла: {e}")
        return

    # Формируем HTML-каркас (с адаптацией под мобильные устройства)
    html_content = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MTProto Proxies</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            padding: 20px;
            max-width: 600px;
            margin: 0 auto;
        }
        h2 {
            text-align: center;
            color: #333;
        }
        .proxy-link {
            display: block;
            background-color: #0088cc;
            color: white;
            padding: 15px;
            margin-bottom: 12px;
            text-decoration: none;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
            word-wrap: break-word;
        }
        .proxy-link:active {
            background-color: #006699;
        }
    </style>
</head>
<body>
    <h2>Свежие MTProto Прокси</h2>
"""

    # Добавляем каждую ссылку как кликабельную кнопку
    for line in lines:
        line = line.strip()
        if line:
            # Ссылка вида tg://... или https://t.me/... автоматически подхватится телеграмом
            html_content += f'    <a href="{line}" class="proxy-link">Подключить прокси</a>\n'

    # Закрываем HTML
    html_content += """</body>
</html>"""

    # Записываем результат в index.html
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("Файл index.html успешно обновлен!")

if __name__ == "__main__":
    fetch_and_generate()
