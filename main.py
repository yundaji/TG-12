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
    text = re.sub(r"https?://\S+", "", text or "")
    text = text.replace("www.zaobao.com.sg", "")
    text = text.replace("zaobao.com.sg", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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

        if "story" not in link:
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


def format_summary(paragraphs):
    clean_paragraphs = []

    total_len = 0

    for p in paragraphs:
        p = clean_text(p)

        if not p:
            continue

        if len(p) < 10:
            continue

        # 最多控制在600字以内
        if total_len + len(p) > 600:
            remaining = 600 - total_len

            if remaining >= 80:
                cut_text = p[:remaining]

                last_punc = max(
                    cut_text.rfind("。"),
                    cut_text.rfind("！"),
                    cut_text.rfind("？")
                )

                if last_punc > 50:
                    cut_text = cut_text[:last_punc + 1]

                clean_paragraphs.append(cut_text)

            break

        clean_paragraphs.append(p)
        total_len += len(p)

        # 满300字以上就可以停止
        if total_len >= 300:
            break

    if not clean_paragraphs:
        return "暂无更多内容。"

    return "\n\n".join(clean_paragraphs)


def get_summary(article_url):
    try:
        html = get_html(article_url)
        soup = BeautifulSoup(html, "html.parser")

        paragraphs = []

        # 优先抓文章正文里的段落
        article_tag = soup.find("article")
        if article_tag:
            for p in article_tag.find_all("p"):
                text = clean_text(p.get_text())
                if len(text) >= 20:
                    paragraphs.append(text)

        # 如果 article 里没抓到，就抓全页 p 标签
        if not paragraphs:
            for p in soup.find_all("p"):
                text = clean_text(p.get_text())
                if len(text) >= 20:
                    paragraphs.append(text)

        if paragraphs:
            return format_summary(paragraphs)

        # 如果正文抓不到，再用网页描述
        desc = soup.find("meta", attrs={"name": "description"})
        if desc and desc.get("content"):
            return format_summary([desc.get("content")])

        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            return format_summary([og_desc.get("content")])

        return "暂无更多内容。"

    except Exception as e:
        print("获取内容失败：", e)
        return "暂无更多内容。"


def get_image(article_url):
    try:
        html = get_html(article_url)
        soup = BeautifulSoup(html, "html.parser")

        # 优先抓正文里的图片
        article_tag = soup.find("article")
        if article_tag:
            for img in article_tag.find_all("img"):
                img_url = img.get("src") or img.get("data-src") or img.get("data-original")

                if not img_url:
                    continue

                img_url = urljoin(BASE_URL, img_url)

                bad_words = ["logo", "icon", "avatar", "default", "placeholder", "social-share"]
                if any(word in img_url.lower() for word in bad_words):
                    continue

                return img_url

        # 再抓 og:image
        og_image = soup.find("meta", attrs={"property": "og:image"})
        if og_image and og_image.get("content"):
            img_url = og_image.get("content")

            if "social-share" not in img_url.lower():
                return img_url

        # 再抓 twitter:image
        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            img_url = twitter_image.get("content")

            if "social-share" not in img_url.lower():
                return img_url

        return None

    except Exception as e:
        print("获取图片失败：", e)
        return None


def send_to_telegram(title, summary, image_url=None):
    caption = f"""📰 {title}

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
    if not BOT_TOKEN:
        print("错误：没有设置 BOT_TOKEN")
        return

    if not CHAT_ID:
        print("错误：没有设置 CHAT_ID")
        return

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

        print("标题：", title)
        print("内容字数：", len(summary.replace("\n", "")))
        print("图片：", image_url)

        send_to_telegram(title, summary, image_url)

        seen.add(link)
        count += 1

    save_seen(seen)

    print(f"完成，本次发布 {count} 篇")


if __name__ == "__main__":
    main()
