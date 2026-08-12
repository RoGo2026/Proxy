import base64
import json
import os
import sys
import urllib.request

from nacl import encoding, public

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = "RoGo2026/Proxy"
SECRET_NAME = "PROXIES"
PROXIES_FILE = "proxies.txt"


def encrypt(public_key: str, secret_value: str) -> str:
    pub = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed = public.SealedBox(pub)
    return base64.b64encode(sealed.encrypt(secret_value.encode("utf-8"))).decode("utf-8")


def main():
    token = os.getenv("PAT_TOKEN", "").strip()
    if not token:
        print("ℹ️ PAT_TOKEN не задан — обновление секрета пропущено.")
        return

    if not os.path.exists(PROXIES_FILE):
        print("ℹ️ proxies.txt не найден — обновление секрета пропущено.")
        return

    with open(PROXIES_FILE, "r", encoding="utf-8") as f:
        proxies = sorted({line.strip() for line in f if line.strip()})

    if not proxies:
        print("ℹ️ Список прокси пуст — обновление секрета пропущено.")
        return

    value = "\n".join(proxies)
    base = f"https://api.github.com/repos/{REPO}/actions/secrets"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    req = urllib.request.Request(f"{base}/public-key", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        key_data = json.loads(resp.read().decode("utf-8"))

    payload = json.dumps({
        "encrypted_value": encrypt(key_data["key"], value),
        "key_id": key_data["key_id"],
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base}/{SECRET_NAME}",
        data=payload,
        headers={**headers, "Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"✅ Секрет {SECRET_NAME} обновлён: прокси: {len(proxies)}")


if __name__ == "__main__":
    main()
