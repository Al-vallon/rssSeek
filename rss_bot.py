


import os, requests

TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"].strip()
BASE = f"https://api.telegram.org/bot{TOKEN}"

print("Longueur CHAT_ID:", len(CHAT_ID), "| commence par:", CHAT_ID[:5])

# 1. Le bot existe-t-il ?
print("getMe:", requests.get(f"{BASE}/getMe").text)

# 2. Quels chats le bot voit-il ? (aide à trouver le bon id)
print("getUpdates:", requests.get(f"{BASE}/getUpdates").text)

# 3. Envoi du message de test
r = requests.post(f"{BASE}/sendMessage", json={"chat_id": CHAT_ID, "text": "test"})
print("sendMessage:", r.status_code, r.text)
