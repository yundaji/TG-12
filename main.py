import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

print("开始测试 Telegram 发送")
print("BOT_TOKEN 是否存在：", bool(BOT_TOKEN))
print("CHAT_ID 是否存在：", bool(CHAT_ID))

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

data = {
    "chat_id": CHAT_ID,
    "text": "测试消息：如果你看到这条，说明 Telegram 连接成功。"
}

response = requests.post(url, data=data, timeout=20)

print("Telegram 返回状态码：", response.status_code)
print("Telegram 返回内容：", response.text)

response.raise_for_status()

print("测试完成")
