"""
Polymarket Bots Dashboard
Запуск: ./venv/bin/python app.py
Открыть: http://localhost:5000
"""
import time
import requests
from datetime import datetime
from flask import Flask, jsonify, render_template

app = Flask(__name__)

POLYGONSCAN_KEY = "{КЛЮЧ etherscan}}"
#Proxy_address polyscan
BOTS = [
    {"name": "Bot 1", "proxy": "0x.....................7c2"},
    {"name": "Bot 2", "proxy": "0x.....................2Fa"},
    {"name": "Bot 3", "proxy": "0x.....................EB"},
    {"name": "Bot 4", "proxy": "0x.....................98"},
    {"name": "Bot 5", "proxy": "0x.....................89"},
    {"name": "Bot 6", "proxy": "0x.....................83"},
]

USDC_CONTRACT = "0xc011a7e12a19f7b1f670d46f03b03f3342e82dfb"
POLYGONSCAN_API = "https://api.etherscan.io/v2/api"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept": "application/json",
}

balance_history = {b["proxy"]: [] for b in BOTS}


def pg_get(params):
    params["chainid"] = "137"
    """Запрос к Polygonscan с ключом и нужными заголовками."""
    if POLYGONSCAN_KEY:
        params["apikey"] = POLYGONSCAN_KEY
    r = requests.get(POLYGONSCAN_API, params=params, timeout=15,
                     allow_redirects=True, headers=HEADERS)
    print(f"  HTTP {r.status_code} | {r.url}")
    return r.json()


def get_usdc_balance(address):
    try:
        data = pg_get({
            "module": "account",
            "action": "tokenbalance",
            "contractaddress": USDC_CONTRACT,
            "address": address,
            "tag": "latest",
        })
        if data.get("status") == "1":
            return int(data["result"]) / 1_000_000
        else:
            print(f"  API error: {data.get('message')} | {data.get('result')}")
    except Exception as e:
        print(f"  Balance error {address[:10]}: {e}")
    return None


def get_matic_balance(address):
    try:
        data = pg_get({
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
        })
        if data.get("status") == "1":
            return int(data["result"]) / 1e18
    except Exception as e:
        print(f"  MATIC error {address[:10]}: {e}")
    return None


def get_recent_txns(address, limit=15):
    try:
        data = pg_get({
            "module": "account",
            "action": "tokentx",
            "contractaddress": USDC_CONTRACT,
            "address": address,
            "sort": "desc",
            "offset": limit,
            "page": 1,
        })
        if data.get("status") == "1":
            txns = []
            for tx in data["result"][:limit]:
                value = int(tx["value"]) / 1_000_000
                direction = "out" if tx["from"].lower() == address.lower() else "in"
                txns.append({
                    "hash": tx["hash"][:16] + "...",
                    "full_hash": tx["hash"],
                    "direction": direction,
                    "value": value,
                    "ts": int(tx["timeStamp"]),
                    "time": datetime.fromtimestamp(int(tx["timeStamp"])).strftime("%d.%m %H:%M"),
                })
            return txns
        else:
            print(f"  Txns error: {data.get('message')}")
    except Exception as e:
        print(f"  Txns error {address[:10]}: {e}")
    return []


@app.route("/")
def index():
    return render_template("index.html", bots=BOTS)


@app.route("/api/balances")
def api_balances():
    result = []
    for bot in BOTS:
        proxy = bot["proxy"]
        if proxy == "0x...":
            result.append({"name": bot["name"], "proxy": proxy,
                           "usdc": None, "matic": None, "history": [], "error": True, "skip": True})
            continue
        usdc = get_usdc_balance(proxy)
        matic = get_matic_balance(proxy)
        ts = int(time.time())
        if usdc is not None:
            history = balance_history.setdefault(proxy, [])
            if not history or (ts - history[-1]["ts"]) > 300:
                history.append({"ts": ts, "val": usdc})
        result.append({
            "name": bot["name"], "proxy": proxy,
            "usdc": usdc, "matic": matic,
            "history": balance_history.get(proxy, []),
            "error": usdc is None,
        })
        time.sleep(0.25)
    return jsonify(result)


@app.route("/api/txns/<proxy>")
def api_txns(proxy):
    known = [b["proxy"] for b in BOTS]
    if proxy not in known:
        return jsonify({"error": "unknown proxy"}), 403
    return jsonify(get_recent_txns(proxy))


if __name__ == "__main__":
    print("=" * 50)
    print("  Polymarket Dashboard")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)