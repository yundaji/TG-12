import os
import json
import time
import re
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
        json.dump(list(seen)[-300:], f, ensure_ascii=False, indent=2)


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_articles():
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(SITE_URL, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html
