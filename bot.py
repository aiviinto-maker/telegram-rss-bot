import os
import json
import hashlib
import re
import html
import requests
import feedparser

BOT_TOKEN = os.environ["8934676482:AAEW_fm6ou1CoVLFCAoVxslU08oQK3lsEtk"]
CHANNEL = os.environ["@cryptonews_400"]

FEEDS_FILE = "feeds.txt"
SEEN_FILE = "seen.json"

MAX_DESCRIPTION = 700
MAX_MESSAGE = 3900


def load_feeds():
    feeds = []

    if not os.path.exists(FEEDS_FILE):
        return feeds

    with open(FEEDS_FILE, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "|" not in line:
                continue

            name, url = line.split("|", 1)

            feeds.append({
                "name": name.strip(),
                "url": url.strip()
            })

    return feeds


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()

    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as file:
            return set(json.load(file))
    except Exception:
        return set()


def save_seen(seen):
    # Keep the database reasonably small.
    recent = list(seen)[-5000:]

    with open(SEEN_FILE, "w", encoding="utf-8") as file:
        json.dump(recent, file)


def clean_text(text):
    if not text:
        return ""

    text = html.unescape(text)

    # Remove HTML
    text = re.sub(r"<[^>]+>", "", text)

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_id(entry):
    value = (
        entry.get("id")
        or entry.get("guid")
        or entry.get("link")
        or entry.get("title")
        or ""
    )

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def create_message(source, entry):
    title = clean_text(entry.get("title", "Untitled"))

    description = clean_text(
        entry.get("summary")
        or entry.get("description")
        or ""
    )

    link = entry.get("link", "")

    if len(description) > MAX_DESCRIPTION:
        description = description[:MAX_DESCRIPTION].rstrip() + "..."

    message = f"📰 {title}\n\n"

    if description:
        message += description + "\n\n"

    if link:
        message += f"🔗 Read more: {link}\n\n"

    message += f"📡 Source: {source}"

    if len(message) > MAX_MESSAGE:
        message = message[:MAX_MESSAGE - 3] + "..."

    return message


def send_telegram(message):
    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    data = {
        "chat_id": CHANNEL,
        "text": message,
        "disable_web_page_preview": False
    }

    response = requests.post(
        url,
        data=data,
        timeout=30
    )

    if not response.ok:
        print("Telegram error:", response.text)
        return False

    return True


def check_feed(feed, seen):
    source = feed["name"]
    url = feed["url"]

    print(f"Checking {source}")

    try:
        parsed = feedparser.parse(url)

        if not parsed.entries:
            print("No entries found.")
            return

        # Only process the latest few items.
        entries = list(parsed.entries[:10])
        entries.reverse()

        for entry in entries:
            item_id = get_id(entry)

            if item_id in seen:
                continue

            message = create_message(source, entry)

            if send_telegram(message):
                seen.add(item_id)
                print("Posted:", entry.get("title", "Untitled"))

    except Exception as error:
        print(f"Error: {error}")


def main():
    feeds = load_feeds()
    seen = load_seen()

    if not feeds:
        print("No RSS feeds configured.")
        return

    for feed in feeds:
        check_feed(feed, seen)

    save_seen(seen)

    print("Finished.")


if __name__ == "__main__":
    main()
