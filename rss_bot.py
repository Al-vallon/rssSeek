import os, sys, json, time, html
import feedparser, requests

TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"].strip()
API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
STATE_FILE = "seen.json"
UA = "rssSeek/1.0 (+github actions)"
KEEP_PER_FEED = 500   # ids mémorisés par flux
MAX_PER_RUN = 30      # plafond d'envois par exécution

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def send(text):
    for _ in range(3):
        try:
            r = requests.post(API, json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
            }, timeout=15)
        except requests.RequestException as ex:
            print("  réseau:", ex)
            time.sleep(3)
            continue
        if r.status_code == 200:
            return True
        if r.status_code == 429:
            wait = r.json().get("parameters", {}).get("retry_after", 5)
            time.sleep(wait + 1)
            continue
        print("  Telegram:", r.status_code, r.text)
        return False
    return False

def main():
    state = load_state()
    feeds = [l.strip() for l in open("feeds.txt") if l.strip() and not l.startswith("#")]
    sent, failed = 0, False

    for url in feeds:
        feed = feedparser.parse(url, agent=UA)
        if not feed.entries:
            print(f"[WARN] aucun article ou flux illisible: {url}")
            continue

        title = html.escape(feed.feed.get("title", url))
        ids = state.get(url)
        first_time = ids is None
        ids = ids or []
        known = set(ids)

        for e in reversed(feed.entries):  # du plus ancien au plus récent
            uid = e.get("id") or e.get("link")
            if not uid or uid in known:
                continue
            if first_time:                # nouveau flux: on mémorise sans poster
                ids.append(uid); known.add(uid)
                continue
            if sent >= MAX_PER_RUN:
                break                     # le reste sera envoyé au prochain run
            text = f"<b>{title}</b>\n{html.escape(e.get('title', '(sans titre)'))}\n{e.get('link', '')}"
            if send(text):
                ids.append(uid); known.add(uid)
                sent += 1
                time.sleep(1)
            else:
                failed = True
                break                     # on réessaiera au prochain run

        state[url] = ids[-KEEP_PER_FEED:]
        print(f"{url}: ok")

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=1)
    print(f"{sent} message(s) envoyé(s)")
    sys.exit(1 if failed else 0)

main()
