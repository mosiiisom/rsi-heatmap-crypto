import sqlite3
import time
from datetime import datetime, timedelta
import random

from tradingview_ta import TA_Handler

from utils.envs import get_envs
from utils.fetch_data import fetch_top_coins
from dotenv import load_dotenv
import os
import streamlit as st

load_dotenv()

# envs
DB_PATH = get_envs("DB_PATH", "data/rsi_data.db")
DEFAULT_RSI_INTERVAL = get_envs("DEFAULT_RSI_INTERVAL", "1d")
UPDATE_LIMIT = int(get_envs("UPDATE_LIMIT", 30))
MIN_UPDATE_INTERVAL_MINUTES = int(get_envs("MIN_UPDATE_INTERVAL_MINUTES", 30))

PROXY = get_envs("PROXY", False) == True
PROXY_URL = get_envs("PROXY_URL", None)
PROXY_SETTINGS = {}

if PROXY and PROXY_URL:
    PROXY_SETTINGS = {
        "http": PROXY_URL,
        "https": PROXY_URL
    }


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS rsi_data (
            symbol TEXT PRIMARY KEY,
            rank INTEGER,
            name TEXT,
            rsi REAL,
            price REAL,
            percent_change_24h REAL,
            rsi_last REAL,
            last_updated TEXT
        )
    ''')
    conn.commit()
    conn.close()


def should_update(last_updated_str: str) -> bool:
    """
    check if coin needs to be updated.
    :param last_updated_str:
    :return:
    """
    if not last_updated_str:
        return True

    try:
        last_updated = datetime.fromisoformat(last_updated_str)
        minutes_passed = (datetime.now() - last_updated).total_seconds() / 60
        return minutes_passed >= MIN_UPDATE_INTERVAL_MINUTES
    except:
        return True


def update_rsi_data():
    init_db()
    conn = sqlite3.connect(DB_PATH)

    coins = fetch_top_coins(limit=UPDATE_LIMIT)
    data = []

    print(f"Starting RSI update for {len(coins)} coins... (Min interval: {MIN_UPDATE_INTERVAL_MINUTES} minutes)")

    for idx, coin in enumerate(coins, 1):
        try:
            cursor = conn.execute("SELECT last_updated FROM rsi_data WHERE symbol = ?", (coin['symbol'],))
            row = cursor.fetchone()
            last_updated = row[0] if row else None

            if last_updated and not should_update(last_updated):
                print(f"⏭️  Skipping {coin['symbol']} (updated recently)")
                continue

            # get analysis from TradingView
            analysis = TA_Handler(
                symbol=f"{coin['symbol']}USDT",
                screener="crypto",
                exchange="binance",
                interval=DEFAULT_RSI_INTERVAL,
                timeout=15,
                proxies=PROXY_SETTINGS,
            ).get_analysis()

            rsi_current = round(analysis.indicators.get('RSI', 0.0), 2)
            rsi_previous = round(analysis.indicators.get('RSI[1]', 0.0), 2)

            record = {
                'symbol': coin['symbol'],
                'rank': coin.get('rank', idx),
                'name': coin['name'],
                'rsi': rsi_current,
                'price': coin.get('price', 0.0),
                'percent_change_24h': coin.get('percent_change_24h', 0.0),
                'rsi_last': rsi_previous,
                'last_updated': datetime.now().isoformat()
            }

            data.append(record)
            print(f"✓ {idx:2d}/{len(coins)} - {coin['symbol']:6} | RSI: {rsi_current:6.2f} | Prev: {rsi_previous:6.2f}")

            time.sleep(random.uniform(2.0, 3.5))  # avoid tradingview rate limit

        except Exception as e:
            print(f"✗ Failed {coin['symbol']}: {e}")
            if "HTTP status code: 429" in str(e):
                print("✗ rate limit reached please try again later.")
                break
            continue

    if data:
        cursor = conn.cursor()

        for row in data:
            cursor.execute("""
                INSERT INTO rsi_data (
                    symbol, rank, name, rsi, price, percent_change_24h, rsi_last, last_updated
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    rank=excluded.rank,
                    name=excluded.name,
                    rsi=excluded.rsi,
                    price=excluded.price,
                    percent_change_24h=excluded.percent_change_24h,
                    rsi_last=excluded.rsi_last,
                    last_updated=excluded.last_updated
            """, (
                row['symbol'],
                row['rank'],
                row['name'],
                row['rsi'],
                row['price'],
                row['percent_change_24h'],
                row['rsi_last'],
                row['last_updated']
            ))

        conn.commit()

        print(f"\n✅ Successfully upserted {len(data)} coins at {datetime.now().strftime('%H:%M:%S')}")
    else:
        print("⚠️ No new data was updated.")

    conn.close()

# if __name__ == "__main__":
#     update_rsi_data()
