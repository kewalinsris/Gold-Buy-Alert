import os
import requests
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo

LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_USER_ID = os.environ["LINE_USER_ID"]


def send_line_message(text):
    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }

    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": text,
            }
        ],
    }

    response = requests.post(url, headers=headers, json=payload)

    print(response.status_code)
    print(response.text)

    response.raise_for_status()


def get_gold_report():

    # ใช้ Gold Futures จาก Yahoo Finance
    gold = yf.Ticker("GC=F").history(period="5d")

    if gold.empty:
        raise ValueError("ไม่สามารถดึงข้อมูล Gold ได้")

    close = gold["Close"].dropna()

    latest = float(close.iloc[-1])
    previous = float(close.iloc[-2])

    change = (latest - previous) / previous * 100

    today = datetime.now(
        ZoneInfo("Asia/Bangkok")
    ).strftime("%d/%m/%Y")

    message = f"""🥇 Gold Buy Alert

ประจำวันที่ {today}

━━━━━━━━━━━━━━

Gold Futures

${latest:,.2f}/oz

Change

{change:+.2f}%

━━━━━━━━━━━━━━

System Status

✅ Yahoo Finance Connected
✅ LINE Connected

"""

    return message


if __name__ == "__main__":

    report = get_gold_report()

    print(report)

    send_line_message(report)
