import requests
import os
from dotenv import load_dotenv

from utils.envs import get_envs

load_dotenv()

# envs
IGNORE_STABLE_COINS = get_envs("IGNORE_STABLE_COINS", True) == True

PROXY = get_envs("PROXY", False) == True
PROXY_URL = get_envs("PROXY_URL", None)
PROXY_SETTINGS = {}

CMC_API_KEY = get_envs("CMC_API_KEY")

if PROXY and PROXY_URL:
    PROXY_SETTINGS = {
        "http": PROXY_URL,
        "https": PROXY_URL
    }


def fetch_top_coins(limit=10):
    try:
        request = requests.get(
            url="https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest",
            params={
                "start": 1,
                "limit": limit,
                "convert": "USD"
            },
            headers={
                "Accepts": "application/json",
                "X-CMC_PRO_API_KEY": CMC_API_KEY,
            },
            proxies=PROXY_SETTINGS
        )

        request.raise_for_status()

        data = request.json()

        results = []
        for coin in data['data']:
            if IGNORE_STABLE_COINS and coin['symbol'].lower() in ['usdt', 'usdc', 'usde', 'usd1', 'dai', 'usdd']:
                continue

            results.append({
                'rank': coin['cmc_rank'],
                'name': coin['name'],
                'symbol': coin['symbol'],
                'price': coin['quote']['USD']['price'] if 'quote' in coin else 0,
                'percent_change_24h': coin['quote']['USD']['percent_change_24h'] if 'quote' in coin else 0
            })

        print(f"✅ Successfully fetched {len(data['data'])} coins from CoinMarketCap")
        return results
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching coins: {e}")
