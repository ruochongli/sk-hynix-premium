"""
SK Hynix / 7709.HK 实时溢价查询网页
后端：Flask
数据源：
  - 7709.HK 实时价格：Yahoo Finance
  - SK Hynix(000660.KS) 实时价格：Yahoo Finance
  - 7709 最新官方资产净值(NAV)：南方东英官网 API
"""
import os
import time
import json
from datetime import datetime, timezone, timedelta
from functools import wraps

import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# 缓存时间（秒）
CACHE_TTL = 10

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

CSOP_API = "https://website-api.csopasset.com/cmsApi/NAV/product"
CSOP_PRODUCT_NAME = "CSOP SK Hynix Daily (2x) Leveraged Product"

_cache = {"ts": 0, "data": None, "error": None}


def hk_time(ts=None):
    """把 Unix 时间戳转成香港时间字符串"""
    tz = timezone(timedelta(hours=8))
    if ts is None:
        dt = datetime.now(tz)
    else:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(tz)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fetch_yahoo(symbol):
    """从 Yahoo Finance v8 chart API 获取最新价格和上一交易日收盘价"""
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{symbol}?interval=1d&range=10d&includePrePost=false"
    )
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    result = data["chart"]["result"][0]
    meta = result["meta"]

    price = meta.get("regularMarketPrice")
    market_time = meta.get("regularMarketTime")
    currency = meta.get("currency", "")

    # 取日线序列的倒数第二根收盘价作为“上一交易日收盘价”，
    # 与南方东英 T-1 NAV 口径保持一致。
    timestamps = result.get("timestamp", [])
    closes = result["indicators"]["quote"][0].get("close", [])
    if len(closes) >= 2 and all(c is not None for c in closes[-2:]):
        prev_close = closes[-2]
    else:
        prev_close = meta.get("chartPreviousClose")

    if price is None or prev_close is None:
        raise ValueError(f"Yahoo 返回数据不完整: {symbol}")

    change_pct = (price - prev_close) / prev_close * 100

    return {
        "symbol": symbol,
        "price": price,
        "prevClose": prev_close,
        "changePct": round(change_pct, 2),
        "marketTime": market_time,
        "marketTimeStr": hk_time(market_time),
        "currency": currency,
    }


def fetch_csop_nav():
    """从南方东英官网 API 获取最新 NAV（HKD / USD）"""
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
    }
    payload = {"productName": CSOP_PRODUCT_NAME}
    resp = requests.post(CSOP_API, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    rows = resp.json()

    hkd = next((r for r in rows if r.get("Currency") == "HKD"), None)
    usd = next((r for r in rows if r.get("Currency") == "USD"), None)

    if not hkd or not usd:
        raise ValueError("CSOP NAV API 未返回 HKD/USD 数据")

    return {
        "hkdNav": float(hkd["NAV"]),
        "usdNav": float(usd["NAV"]),
        "hkdClose": float(hkd.get("closePrice") or 0),
        "dateTc": hkd.get("HstDateTc", ""),
        "date": hkd.get("HstDateFormat", ""),
        "ticker": hkd.get("Ticker", "7709 HK"),
    }


def build_data():
    """汇总所有数据源并计算溢价"""
    hk_7709 = fetch_yahoo("7709.HK")
    sk_hynix = fetch_yahoo("000660.KS")
    nav = fetch_csop_nav()

    # SK 海力士自上一收盘以来的收益率
    sk_return = (sk_hynix["price"] - sk_hynix["prevClose"]) / sk_hynix["prevClose"]

    # 2x 杠杆产品的估算 NAV（以 SK 海力士上一收盘为基准）
    estimated_hkd_nav = nav["hkdNav"] * (1 + 2 * sk_return)
    estimated_usd_nav = nav["usdNav"] * (1 + 2 * sk_return)

    # 实时溢价（用估算 NAV）
    premium_pct = (hk_7709["price"] - estimated_hkd_nav) / estimated_hkd_nav * 100

    # 以官方 NAV 计算的昨日收盘溢价
    last_close_premium_pct = None
    if nav["hkdClose"]:
        last_close_premium_pct = (nav["hkdClose"] - nav["hkdNav"]) / nav["hkdNav"] * 100

    return {
        "hk7709": hk_7709,
        "skHynix": sk_hynix,
        "nav": {
            "hkdNav": round(nav["hkdNav"], 4),
            "usdNav": round(nav["usdNav"], 4),
            "hkdClose": round(nav["hkdClose"], 3) if nav["hkdClose"] else None,
            "date": nav["date"],
            "dateTc": nav["dateTc"],
        },
        "estimatedNav": {
            "hkd": round(estimated_hkd_nav, 4),
            "usd": round(estimated_usd_nav, 4),
        },
        "premiumPct": round(premium_pct, 2),
        "lastClosePremiumPct": round(last_close_premium_pct, 2) if last_close_premium_pct is not None else None,
        "lastUpdated": hk_time(),
    }


def get_cached_data():
    now = time.time()
    if now - _cache["ts"] < CACHE_TTL and (_cache["data"] or _cache["error"]):
        if _cache["error"]:
            raise _cache["error"]
        return _cache["data"]

    try:
        _cache["data"] = build_data()
        _cache["error"] = None
    except Exception as e:
        _cache["error"] = e
        _cache["data"] = None
    _cache["ts"] = now

    if _cache["error"]:
        raise _cache["error"]
    return _cache["data"]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    try:
        data = get_cached_data()
        return jsonify({"ok": True, **data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    # 开发服务器，默认端口 5000
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
