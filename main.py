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
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": text}]}
    response = requests.post(url, headers=headers, json=payload)
    print(response.status_code)
    print(response.text)
    response.raise_for_status()


def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def rsi_status(value):
    if value < 40:
        return "🔵 Buy Zone"
    elif value > 70:
        return "🔴 Overbought"
    else:
        return "🟢 Normal"


def get_gold_report():
    gold = yf.Ticker("GC=F").history(period="3mo", interval="1d")

    if gold.empty:
        raise ValueError("ไม่สามารถดึงข้อมูล Gold ได้")

    close = gold["Close"].dropna()

    latest = float(close.iloc[-1])
    previous = float(close.iloc[-2])
    change = (latest - previous) / previous * 100

    latest_rsi = float(calculate_rsi(close).dropna().iloc[-1])

    today = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%d/%m/%Y")

    return f"""🥇 Gold Buy Alert Test
ประจำวันที่ {today}

━━━━━━━━━━━━━━

Gold Futures
${latest:,.2f}/oz ({change:+.2f}%)

RSI (14)
{rsi_status(latest_rsi)} ({latest_rsi:.1f})

━━━━━━━━━━━━━━

System Status
✅ Gold price OK
✅ RSI OK
✅ LINE OK
"""


if __name__ == "__main__":
    send_line_message(get_gold_report())
