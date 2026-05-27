import os
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SITE_URL = "https://www.zaobao.com.sg/realtime"
BASE_URL = "https://www.zaobao.com.sg"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SEEN_FILE = "seen.json"


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()

    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen)[-200:], f, ensure_ascii=False, indent=2)


def get_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.text


def fetch_articles():
    html = get_html(SITE_URL)
    soup = BeautifulSoup(html, "html.parser")

    articles = []

    for a in soup.find_all("a", href=True):
        title = clean_text(a.get_text())
        href = a.get("href", "")

        if len(title) < 8:
            continue

        link = urljoin(BASE_URL, href)

        if "/realtime/" not in link and "/news/" not in link:
            continue

        articles.append({
            "title": title,
            "link": link
        })

    unique = []
    used = set()

    for item in articles:
        if item["link"] not in used:
            unique.append(item)
            used.add(item["link"])

    print(f"找到 {len(unique)} 篇文章")
    return unique[:5]


def get_summary(article_url):
    try:
        html = get_html(article_url)
        soup = BeautifulSoup(html, "html.parser")

        desc = soup.find("meta", attrs={"name": "description"})
        if desc and desc.get("content"):
            return clean_text(desc.get("content"))[:300]

        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            return clean_text(og_desc.get("content"))[:300]

        paragraphs = []

        for p in soup.find_all("p"):
            text = clean_text(p.get_text())
            if len(text) >= 20:
                paragraphs.append(text)

        if paragraphs:
            return " ".join(paragraphs[:2])[:300]

        return "暂无更多内容。"

    except Exception as e:
        print("获取大概内容失败：", e)
        return "暂无更多内容。"


def get_image(article_url):
    try:
        html = get_html(article_url)
        soup = BeautifulSoup(html, "html.parser")

        og_image = soup.find("meta", attrs={"property": "og:image"})
        if og_image and og_image.get("content"):
            return og_image.get("content")

        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            return twitter_image.get("content")

        return None

    except Exception as e:
        print("获取图片失败：", e)
        return None


def send_to_telegram(title, summary, image_url=None):
    caption = f"""📰 {title}

大概内容：
{summary}
"""

    if image_url:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

        response = requests.post(url, data={
            "chat_id": CHAT_ID,
            "photo": image_url,
            "caption": caption[:1000]
        }, timeout=20)

    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        response = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": caption,
            "disable_web_page_preview": True
        }, timeout=20)

    print("Telegram 状态：", response.status_code)
    print("Telegram 返回：", response.text)

    response.raise_for_status()


def main():
    seen = load_seen()
    articles = fetch_articles()

    count = 0

    for article in reversed(articles):
        title = article["title"]
        link = article["link"]

        if link in seen:
            continue

        summary = get_summary(link)
        image_url = get_image(link)

        send_to_telegram(title, summary, image_url)

        seen.add(link)
        count += 1

    save_seen(seen)

    print(f"完成，本次发布 {count} 篇")


if __name__ == "__main__":
    main()
