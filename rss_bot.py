import os, json, time, feedparser, requests

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STATE = "seen.json"
API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# --- BLOC DE TEST : à supprimer une fois que ça marche ---
#r = requests.post(API, json={"chat_id": CHAT_ID, "text": "test"})
#print("TEST:", r.status_code, r.text)
# ----------------------------------------------------------

seen = set(json.load(open(STATE))) if os.path.exists(STATE) else set()
first_run = not seen

for url in open("feeds.txt").read().split():
    feed = feedparser.parse(url)
    for e in reversed(feed.entries):
        uid = e.get("id") or e.get("link")
        if uid in seen:
            continue
        seen.add(uid)
        if not first_run:
            r = requests.post(
                API,
                json={
                    "chat_id": CHAT_ID,
                    "text": f"{feed.feed.get('title', 'RSS')}\n{e.get('title')}\n{e.get('link')}",
                },
            )
            print(r.status_code, e.get("link"))
            time.sleep(1)  # évite la limite d'envoi de Telegram

json.dump(sorted(seen), open(STATE, "w"))
