import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SITE_URL = "https://www.zaobao.com.sg/realtime"
BASE_URL = "https://www.zaobao.com.sg"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SEEN_FILE = "seen.json"


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen)[-200:], f, ensure_ascii=False, indent=2)


def fetch_articles():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(SITE_URL, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    articles = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        title = a.get_text(strip=True)

        if not title:
            continue

        if "/realtime/" in href or "/news/" in href:
            link = urljoin(BASE_URL, href)

            if len(title) >= 8:
                articles.append({
                    "title": title,
                    "link": link
                })

    # 去重
    unique = []
    used_links = set()

    for item in articles:
        if item["link"] not in used_links:
            unique.append(item)
            used_links.add(item["link"])

    return unique[:10]


def send_to_telegram(title, link):
    text = f"📰 {title}\n\n阅读全文：\n{link}"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": False
    }

    response = requests.post(url, data=data, timeout=20)
    response.raise_for_status()


def main():
    if not BOT_TOKEN or not CHAT_ID:
        raise ValueError("BOT_TOKEN 或 CHAT_ID 没有设置")

    seen = load_seen()
    articles = fetch_articles()

    new_count = 0

    # 反过来发，避免最新文章顺序乱掉
    for article in reversed(articles):
        link = article["link"]
        title = article["title"]

        if link not in seen:
            send_to_telegram(title, link)
            seen.add(link)
            new_count += 1

    save_seen(seen)

    print(f"完成。本次发布 {new_count} 篇新文章。")


if __name__ == "__main__":
    main()
