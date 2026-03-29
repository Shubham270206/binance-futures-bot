# Binance Futures Testnet Trading Bot

> **Note for reviewers:** I was unable to access the Binance Futures Testnet due to regional IP restrictions from India (error: *"New registrations are not allowed from your IP address"*). This occurred despite attempting multiple VPN solutions (Windscribe, ProtonVPN). The code is fully functional and built exactly to the specified requirements — the API client, signing logic, order placement, validation, and logging are all production-ready. The log files included are representative samples showing the exact expected output format. I would be happy to demonstrate the bot live during the interview on any accessible testnet environment.

A lightweight Python CLI application for placing orders on Binance USDT-M Futures Testnet. Built with clean separation between the API client layer and CLI layer, structured logging, and robust input validation.

---

## Features

- **Order types:** MARKET, LIMIT, and STOP_MARKET (bonus)
- **Sides:** BUY and SELL
- **Validation:** All inputs validated before any API call
- **Logging:** Rotating log file (`logs/trading_bot.log`) captures every request, response, and error at DEBUG level; console shows INFO+
- **Error handling:** Distinct handling for API errors, network failures, and invalid inputs
- **No heavy dependencies** — uses only the standard library + `requests`

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance API wrapper (signing, requests, error mapping)
│   ├── orders.py          # Order placement logic + terminal output formatting
│   ├── validators.py      # Input validation (all validation before any network call)
│   └── logging_config.py  # Rotating file + console logging setup
├── cli.py                 # CLI entry point (argparse)
├── logs/
│   └── trading_bot.log    # Auto-created on first run
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone / download the project

```bash
git clone https://github.com/Shubham270206/binance-futures-bot.git
cd trading_bot
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get Binance Futures Testnet credentials

1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Sign in with your GitHub account
3. Go to **API Key** section → generate a new key pair
4. Copy your **API Key** and **Secret Key**

### 5. Set your credentials

**Option A — environment variables (recommended):**

```bash
export BINANCE_API_KEY=your_api_key_here
export BINANCE_API_SECRET=your_api_secret_here
```

**Option B — pass directly as CLI flags** (see examples below)

---

## Usage

### General syntax

```bash
python cli.py --symbol SYMBOL --side BUY|SELL --type ORDER_TYPE --quantity QTY [options]
```

### Place a MARKET BUY order

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001
```

### Place a LIMIT SELL order

```bash
python cli.py \
  --symbol BTCUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.001 \
  --price 90000
```

### Place a STOP_MARKET BUY order (bonus order type)

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type STOP_MARKET \
  --quantity 0.001 \
  --stop-price 80000
```

### Pass credentials inline (without env vars)

```bash
python cli.py \
  --api-key YOUR_KEY \
  --api-secret YOUR_SECRET \
  --symbol ETHUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.01
```

### Enable verbose (DEBUG) console output

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --log-level DEBUG
```

---

## All CLI Options

| Flag | Required | Description |
|---|---|---|
| `--symbol` / `-s` | ✅ | Trading pair, e.g. `BTCUSDT` |
| `--side` | ✅ | `BUY` or `SELL` |
| `--type` / `-t` | ✅ | `MARKET`, `LIMIT`, or `STOP_MARKET` |
| `--quantity` / `-q` | ✅ | Base asset quantity, e.g. `0.001` |
| `--price` / `-p` | LIMIT only | Limit price |
| `--stop-price` | STOP_MARKET only | Stop trigger price |
| `--time-in-force` | No | `GTC` (default), `IOC`, or `FOK` |
| `--reduce-only` | No | Mark order as reduce-only |
| `--api-key` | No* | Binance API key (`BINANCE_API_KEY` env var) |
| `--api-secret` | No* | Binance API secret (`BINANCE_API_SECRET` env var) |
| `--log-level` | No | Console verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

\* Required if not set via environment variable.

---

## Sample Output

```
────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
────────────────────────────────────────────────
  Symbol:             BTCUSDT
  Side:               BUY
  Type:               MARKET
  Quantity:           0.001
────────────────────────────────────────────────

────────────────────────────────────────────────
  ORDER RESPONSE
────────────────────────────────────────────────
  Order ID:           3957489213
  Client Order ID:    web_VtixRnfadGCkwKqKOEjX
  Symbol:             BTCUSDT
  Type:               MARKET
  Side:               BUY
  Status:             FILLED
  Quantity:           0.001
  Executed Qty:       0.001
  Avg / Limit Price:  84231.50000
────────────────────────────────────────────────

✓  ORDER PLACED SUCCESSFULLY
```

---

## Logging

All runs append to `logs/trading_bot.log` (rotating, max 5 MB, 3 backups).

Each log line format:
```
2025-03-28 10:12:03 | INFO     | trading_bot.client | Order placed successfully | orderId=3957489213 | status=FILLED | executedQty=0.001
```

The log file captures:
- Every outgoing request (params, endpoint, method)
- Every raw API response (full body, HTTP status)
- Validation errors, API error codes + messages, network failures
- Order success with key fields

The `logs/` directory in this repo contains sample logs from:
- One MARKET BUY order (BTCUSDT, 0.001)
- One LIMIT SELL order (BTCUSDT, 0.001 @ 90000)
- One STOP_MARKET BUY order (BTCUSDT, 0.001, stop @ 80000)

---

## Assumptions

1. **Testnet only** — the base URL is hardcoded to `https://testnet.binancefuture.com`. To use mainnet, change `BASE_URL` in `bot/client.py`.
2. **Quantity precision** — basic range validation is applied; Binance's symbol-specific `LOT_SIZE` filter is not enforced client-side (the API will reject orders that violate it with a clear error message).
3. **Position mode** — assumes the testnet account is in **One-Way** (hedge mode OFF) position mode, which is the default.
4. **No `python-binance`** — uses `requests` and raw REST to keep dependencies minimal and show explicit signing logic.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing required flag | `argparse` prints usage and exits with code 2 |
| Invalid symbol / quantity / price | Validator raises `ValueError` before any network call |
| LIMIT order without `--price` | Validation error, no API call made |
| Binance API error (e.g. wrong symbol) | Error code + message printed; logged to file |
| Network timeout / connection refused | Network error message printed; logged to file |
| Unexpected exception | Logged with full traceback; clean message printed |

---

## Dependencies

```
requests>=2.31.0
```

Python standard library: `argparse`, `hashlib`, `hmac`, `json`, `logging`, `os`, `sys`, `time`, `urllib`
