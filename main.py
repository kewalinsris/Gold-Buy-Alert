import os
import json
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_USER_ID = os.environ["LINE_USER_ID"]

STATE_FILE = "gold_alert_state.json"


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


def calculate_atr(high, low, close, period=14):
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def get_data(ticker, period="2y"):
    data = yf.Ticker(ticker).history(period=period, interval="1d")
    if data.empty:
        raise ValueError(f"ไม่สามารถดึงข้อมูล {ticker} ได้")
    return data


def get_real_yield():
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10"
    df = pd.read_csv(url)
    df["DFII10"] = pd.to_numeric(df["DFII10"], errors="coerce")
    return df["DFII10"].dropna()


def is_downtrend(series, span=20, lookback=5):
    ema = series.ewm(span=span, adjust=False).mean()
    return series.iloc[-1] < ema.iloc[-1] and ema.iloc[-1] < ema.iloc[-lookback]


def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(price):
    today = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d")
    with open(STATE_FILE, "w") as f:
        json.dump({"last_alert_date": today, "last_alert_price": price}, f)


def cooldown_ok(price):
    state = load_state()
    if not state:
        return True

    last_date = datetime.strptime(state["last_alert_date"], "%Y-%m-%d")
    last_price = float(state["last_alert_price"])
    today = datetime.now(ZoneInfo("Asia/Bangkok")).replace(tzinfo=None)

    days_passed = (today - last_date).days
    price_dropped_more = price <= last_price * 0.95

    return days_passed >= 30 or price_dropped_more


def build_gold_alert():
    gold = get_data("GC=F", "2y")
    dxy = get_data("DX-Y.NYB", "1y")
    real_yield = get_real_yield()

    close = gold["Close"].dropna()
    high = gold["High"].dropna()
    low = gold["Low"].dropna()

    price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2])
    change_pct = (price - prev_price) / prev_price * 100

    rsi = float(calculate_rsi(close).dropna().iloc[-1])
    ma200 = float(close.rolling(200).mean().iloc[-1])

    ath = float(close.max())
    drawdown = (price - ath) / ath * 100

    atr_series = calculate_atr(high, low, close).dropna()
    atr_percentile = atr_series.tail(252).rank(pct=True).iloc[-1] * 100

    dxy_close = dxy["Close"].dropna()

    dxy_down = is_downtrend(dxy_close)
    real_yield_down = is_downtrend(real_yield)

    macro_ok = dxy_down and real_yield_down

    trigger_count = 0
    reasons = []

    if rsi < 40:
        trigger_count += 1
        reasons.append("✓ RSI ต่ำกว่า 40 ตลาดเริ่มอ่อนตัว")

    if drawdown <= -8:
        trigger_count += 1
        reasons.append("✓ ราคาย่อตัวมากกว่า 8% จากจุดสูงสุด")

    if price > ma200:
        trigger_count += 1
        reasons.append("✓ ราคาอยู่เหนือ 200 DMA แนวโน้มระยะยาวยังแข็งแรง")

    if not macro_ok or trigger_count < 2:
        print("No gold alert today")
        return None

    if not cooldown_ok(price):
        print("Cooldown active")
        return None

    reasons.append("✓ ดอลลาร์สหรัฐอยู่ในแนวโน้มอ่อนค่า")
    reasons.append("✓ US 10Y Real Yield อยู่ในแนวโน้มลดลง")

    if price > ma200:
        title = "🟢 Strong Buy Opportunity"
        recommendation = "🔵 Buy the Dip"
    else:
        title = "🟡 Buy Opportunity"
        recommendation = "🟡 ทยอยสะสมเป็นหลายไม้"
        reasons.append("✓ ราคาอยู่ต่ำกว่า 200 DMA จึงควรทยอยซื้อ ไม่ควรใส่เงินก้อนทีเดียว")

    warning = ""
    if atr_percentile >= 80:
        warning = "\n\n⚠️ ตลาดยังผันผวนสูง\nควรทยอยสะสมเป็นหลายไม้"

    date_th = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%d/%m/%Y")

    message = f"""🥇 Gold Buy Alert
ประจำวันที่ {date_th}

{title}

Gold Futures
${price:,.2f}/oz ({change_pct:+.2f}%)

เหตุผล
{chr(10).join(reasons)}{warning}

Recommendation

{recommendation}
"""

    save_state(price)
    return message


if __name__ == "__main__":
    alert = build_gold_alert()

    if alert:
        print(alert)
        send_line_message(alert)
    else:
        print("No LINE message sent.")
