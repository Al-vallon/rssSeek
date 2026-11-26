import os, json, time, feedparser, requests

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STATE = "seen.json"

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
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={
                    "chat_id": CHAT_ID,
                    "text": f"{feed.feed.get('title', 'RSS')}\n{e.get('title')}\n{e.get('link')}",
                },
            )
            time.sleep(1)  # évite la limite d'envoi de Telegram

json.dump(sorted(seen), open(STATE, "w"))
