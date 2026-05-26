const { checkProxy } = require('telegram-mtproto-proxy-checker');
const fs = require('fs');

const INPUT_FILE = 'all_proxies.txt';
const OUTPUT_FILE = 'proxies.txt';
const HTML_FILE = 'index.html';

async function main() {
    console.log('🔍 Читаем список всех прокси из', INPUT_FILE);
    const content = fs.readFileSync(INPUT_FILE, 'utf-8');
    const lines = content.split(/\r?\n/).filter(l => l.trim().length > 0);
    console.log(`📦 Загружено прокси: ${lines.length}`);

    const working = [];
    let total = lines.length;
    let checked = 0;

    for (const proxyLink of lines) {
        checked++;
        process.stdout.write(`   [${checked}/${total}] Проверка ${proxyLink.substring(0, 70)}... `);
        try {
            const result = await checkProxy(proxyLink, { timeout: 5000 });
            if (result && result.ok) {
                console.log('✅ РАБОТАЕТ');
                working.push(proxyLink);
            } else {
                console.log('❌ НЕ РАБОТАЕТ');
            }
        } catch (err) {
            console.log('❌ ОШИБКА:', err.message);
        }
    }

    console.log(`\n🏆 Рабочих прокси: ${working.length} из ${total}`);
    fs.writeFileSync(OUTPUT_FILE, working.join('\n'), 'utf-8');
    console.log(`💾 Рабочие прокси сохранены в ${OUTPUT_FILE}`);
    generateHtml(working);
}

function generateHtml(proxies) {
    let html = `<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MTProto Proxies</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            padding: 15px;
            max-width: 800px;
            margin: 0 auto;
        }
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #ddd;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        h2 { margin: 0; color: #333; font-size: 20px; }
        .counter {
            background-color: #2e7d32;
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }
        .proxy-grid { display: flex; flex-wrap: wrap; gap: 10px; }
        .proxy-link {
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
        }
        .ping-text { display: none; }
        .proxy-link:active { background-color: #006699; }
        .proxy-link.clicked { background-color: #d9534f; }
        @media (max-width: 600px) { .proxy-link { flex: 1 1 calc(50% - 10px); } }
        @media (max-width: 360px) { .proxy-link { flex: 1 1 100%; } }
    </style>
</head>
<body>

    <div class="header-container">
        <h2>MTProto Прокси</h2>
        <div class="counter">Работает: ${proxies.length}</div>
    </div>

    <div class="proxy-grid">
`;
    for (let i = 0; i < proxies.length; i++) {
        const proxy = proxies[i];
        html += `        <a href="${proxy}" class="proxy-link"><span>#${i+1} Подключить</span><span class="ping-text"></span></a>\n`;
    }
    html += `    </div>
    <script>
        document.querySelectorAll('.proxy-link').forEach(button => {
            button.addEventListener('click', function() {
                this.classList.add('clicked');
            });
        });
    </script>
</body>
</html>`;
    fs.writeFileSync(HTML_FILE, html, 'utf-8');
    console.log(`🌐 Сгенерирован ${HTML_FILE} с ${proxies.length} прокси`);
}

main().catch(console.error);
