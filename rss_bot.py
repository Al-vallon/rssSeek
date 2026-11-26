import os, re, sys, json, time, html
import feedparser, requests

TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
DEFAULT_CHAT = os.environ["TELEGRAM_CHAT_ID"].strip()
API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
STATE_FILE = "seen.json"
UA = "Mozilla/5.0 (compatible; rssSeek/1.0)"
KEEP_PER_FEED = 500
MAX_PER_RUN = 30


def chat_for(section):
    key = "TELEGRAM_CHAT_ID_" + re.sub(r"\W", "_", section).upper()
    return (os.environ.get(key) or DEFAULT_CHAT).strip()


def parse_config(path):
    sections, cur = [], None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            cur = {"name": line[1:-1].strip().lower(), "include": [], "exclude": [], "feeds": []}
            sections.append(cur)
            continue
        if cur is None:
            cur = {"name": "default", "include": [], "exclude": [], "feeds": []}
            sections.append(cur)
        low = line.lower()
        if low.startswith("include:") or low.startswith("exclude:"):
            kind, _, words = line.partition(":")
            cur[kind.lower()] = [w.strip() for w in words.split(",") if w.strip()]
        else:
            cur["feeds"].append(line)
    return sections


def matches(words, text):
    return any(re.search(r"\b" + re.escape(w) + r"\b", text, re.IGNORECASE) for w in words)


def passes(entry, sec):
    text = f"{entry.get('title', '')} {entry.get('summary', '')}"
    if sec["include"] and not matches(sec["include"], text):
        return False
    if sec["exclude"] and matches(sec["exclude"], text):
        return False
    return True


def fetch_feed(url):
    for attempt in range(2):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            r.raise_for_status()
            return feedparser.parse(r.content)
        except Exception as ex:
            print(f"  essai {attempt + 1} échoué ({type(ex).__name__}): {url}")
            time.sleep(2)
    return None


def load_state():
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def send(chat_id, text):
    for _ in range(3):
        try:
            r = requests.post(API, json={
                "chat_id": chat_id,
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
    sent, failed = 0, False

    for sec in parse_config("feeds.txt"):
        chat_id = chat_for(sec["name"])
        for url in sec["feeds"]:
            feed = fetch_feed(url)
            if feed is None or not feed.entries:
                print(f"[WARN] [{sec['name']}] flux illisible ou vide: {url}")
                continue

            title = html.escape(feed.feed.get("title", url))
            ids = state.get(url)
            first_time = ids is None
            ids = ids or []
            known = set(ids)

            for e in reversed(feed.entries):
                uid = e.get("id") or e.get("link")
                if not uid or uid in known:
                    continue
                if first_time or not passes(e, sec):
                    ids.append(uid); known.add(uid)
                    continue
                if sent >= MAX_PER_RUN:
                    break
                text = f"<b>{title}</b>\n{html.escape(e.get('title', '(sans titre)'))}\n{e.get('link', '')}"
                if send(chat_id, text):
                    ids.append(uid); known.add(uid)
                    sent += 1
                    time.sleep(1)
                else:
                    failed = True
                    break

            state[url] = ids[-KEEP_PER_FEED:]
            print(f"[{sec['name']}] {url}: ok")

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=1)
    print(f"{sent} message(s) envoyé(s)")
    sys.exit(1 if failed else 0)


main()
