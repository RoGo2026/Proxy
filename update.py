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

    # Отфильтровываем пустые строки сразу, чтобы узнать точное количество рабочих ссылок
    proxies = [line.strip() for line in lines if line.strip()]
    total_count = len(proxies)

    # Формируем HTML-каркас
    html_content = f"""<!DOCTYPE html>
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
        /* Шапка с названием и счетчиком по бокам */
        .header-container {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #ddd;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            margin: 0;
            color: #333;
            font-size: 20px;
        }}
        .counter {{
            background-color: #222;
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }}
        /* Горизонтальная сетка для кнопок */
        .proxy-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .proxy-link {{
            display: block;
            /* Рассчитываем ширину: по умолчанию 3 колонки на больших экранах */
            flex: 1 1 calc(33.333% - 10px);
            min-width: 130px;
            background-color: #0088cc;
            color: white;
            padding: 12px 8px;
            text-decoration: none;
            border-radius: 6px;
            text-align: center;
            font-weight: bold;
            font-size: 14px;
            box-sizing: border-box;
            transition: background-color 0.2s;
        }}
        .proxy-link:active {{
            background-color: #006699;
        }}
        /* Класс, который сделает кнопку красной после нажатия */
        .proxy-link.clicked {{
            background-color: #d9534f;
        }}
        /* Адаптивность под мобильные устройства */
        @media (max-width: 600px) {{
            .proxy-link {{
                flex: 1 1 calc(50% - 10px); /* По 2 кнопки в ряд на телефонах */
            }}
        }}
        @media (max-width: 360px) {{
            .proxy-link {{
                flex: 1 1 100%; /* По 1 кнопке, если экран совсем крошечный */
            }}
        }}
    </style>
</head>
<body>

    <div class="header-container">
        <h2>MTProto Прокси</h2>
        <div class="counter">Всего: {total_count}</div>
    </div>

    <div class="proxy-grid">
"""

    # Добавляем каждую ссылку с её порядковым номером
    for index, link in enumerate(proxies, start=1):
        html_content += f'        <a href="{link}" class="proxy-link">#{index} Подключить</a>\n'

    # Закрываем сетку и добавляем JavaScript для отслеживания кликов
    html_content += """    </div>

    <script>
        // Скрипт отслеживает клики по кнопкам
        document.querySelectorAll('.proxy-link').forEach(button => {
            button.addEventListener('click', function() {
                // Добавляем класс, который перекрасит кнопку в красный цвет
                this.classList.add('clicked');
            });
        });
    </script>
</body>
</html>"""

    # Записываем результат в index.html
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Файл index.html успешно обновлен! Найдено прокси: {total_count}")

if __name__ == "__main__":
    fetch_and_generate()
