# Trading Bot Backend

Python backend for placing orders and viewing account data on **Binance USDT-M Futures Testnet**.

The project provides three ways to use the same core logic:

- **CLI** — place orders from the terminal
- **FastAPI server** — HTTP API for the Next.js frontend in production
- **JSON bridge scripts** — stdin/stdout helpers used for local frontend development

All paths share validation, Binance client code, order formatting, logging, and error handling. API keys never appear in source code; they are loaded from environment variables.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [CLI](#cli)
  - [FastAPI Server](#fastapi-server)
  - [JSON Bridge Scripts](#json-bridge-scripts)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Logging](#logging)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)
- [Assumptions](#assumptions)
- [Related Frontend](#related-frontend)

---

## Features

- Place **MARKET** and **LIMIT** orders on Binance Futures Testnet
- Support **BUY** and **SELL** sides
- Validate symbol, side, order type, quantity, and limit price before submission
- Fetch dashboard data: account summary, balances, positions, open orders, order history
- Automatic server time sync and retry on Binance timestamp drift (`-1021`)
- Structured error messages for validation, configuration, API, and network failures
- Rotating file logs with request/response details and stack traces
- CORS support for a deployed frontend via `FRONTEND_ORIGIN`
- Health check endpoint for deployment platforms

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                        Entry Points                          │
├──────────────┬────────────────────┬─────────────────────────┤
│   cli.py     │     server.py      │  api_order.py           │
│              │    (FastAPI)       │  api_dashboard.py       │
└──────┬───────┴─────────┬──────────┴───────────┬─────────────┘
       │                 │                      │
       └─────────────────┼──────────────────────┘
                         ▼
              ┌──────────────────────┐
              │  bot/validators.py   │
              │  bot/orders.py       │
              │  bot/client.py       │
              └──────────┬───────────┘
                         ▼
              ┌──────────────────────┐
              │  Binance Futures     │
              │  Testnet REST API    │
              └──────────────────────┘
```

| Layer | Responsibility |
|-------|----------------|
| `cli.py` | Argument parsing and terminal output via `rich` |
| `server.py` | HTTP routes, CORS, request/response models |
| `api_order.py` / `api_dashboard.py` | JSON stdin/stdout bridge for local frontend dev |
| `bot/validators.py` | Input validation and normalization |
| `bot/orders.py` | Order placement and response formatting |
| `bot/client.py` | `python-binance` wrapper with logging and retries |
| `bot/config.py` | Environment variable loading |
| `bot/logging_config.py` | Rotating file logger setup |
| `bot/exceptions.py` | Typed application errors |

---

## Project Structure

```text
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py           # Binance Futures client wrapper
│   ├── config.py           # Settings from environment variables
│   ├── exceptions.py       # Custom exception types
│   ├── logging_config.py   # File logging configuration
│   ├── orders.py           # Order service and result formatting
│   └── validators.py       # Input validation helpers
├── logs/
│   └── app.log             # Application log file (gitignored)
├── sample_logs/
│   ├── example_success.log
│   └── example_error.log
├── api_dashboard.py        # Dashboard JSON bridge
├── api_order.py            # Order JSON bridge
├── cli.py                  # Command-line interface
├── server.py               # FastAPI HTTP server
├── .env.example            # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Prerequisites

- **Python 3.11+**
- **Binance Futures Testnet account** and API credentials
- Internet access to `https://testnet.binancefuture.com`

Create testnet API keys at the [Binance Futures Testnet](https://testnet.binancefuture.com) site. Testnet keys are separate from live Binance keys.

---

## Installation

Clone the repository and move into the backend directory:

```bash
cd trading_bot
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

On Windows, if `python` is unavailable but the Python launcher is installed:

```powershell
py -m pip install -r requirements.txt
```

---

## Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and add your credentials:

```env
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
BINANCE_BASE_URL=https://testnet.binancefuture.com
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BINANCE_API_KEY` | Yes | — | Binance Futures Testnet API key |
| `BINANCE_API_SECRET` | Yes | — | Binance Futures Testnet API secret |
| `BINANCE_BASE_URL` | No | `https://testnet.binancefuture.com` | Futures REST base URL |
| `FRONTEND_ORIGIN` | No | `http://localhost:3000` | Allowed CORS origin for the frontend (used by `server.py`) |

When deploying the FastAPI server, set `FRONTEND_ORIGIN` to your deployed frontend URL (for example `https://your-app.vercel.app`).

---

## Usage

Run all commands from inside the `trading_bot` directory.

### CLI

#### MARKET order

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

#### LIMIT order

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 120000
```

The CLI prints a request summary, submits the order, and displays either:

- **Success:** order ID, status, executed quantity, average price, client order ID
- **Failure:** a readable error message

#### CLI arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--symbol` | Yes | Trading pair, uppercase (for example `BTCUSDT`) |
| `--side` | Yes | `BUY` or `SELL` |
| `--type` | Yes | `MARKET` or `LIMIT` |
| `--quantity` | Yes | Positive decimal quantity |
| `--price` | LIMIT only | Limit price |

### FastAPI Server

Start the HTTP API locally:

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Open the interactive docs:

```text
http://127.0.0.1:8000/docs
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status": "ok"}
```

When running the frontend locally against this server, set in `frontend/.env.local`:

```env
BACKEND_API_URL=http://127.0.0.1:8000
```

### JSON Bridge Scripts

These scripts read JSON from stdin and write JSON to stdout. They are used automatically by the frontend when `BACKEND_API_URL` is not set.

#### Place an order

```bash
echo '{"symbol":"BTCUSDT","side":"BUY","type":"MARKET","quantity":"0.001"}' | python api_order.py
```

#### Load dashboard data

```bash
echo '{"symbol":"BTCUSDT"}' | python api_dashboard.py
```

Success responses include `"success": true`. Failures include `"success": false` and an `"error"` message.

---

## API Reference

Base URL when running locally: `http://127.0.0.1:8000`

### `GET /health`

Returns service health for deployment checks.

**Response**

```json
{"status": "ok"}
```

### `POST /api/orders`

Place a Binance Futures Testnet order.

**Request body**

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "quantity": "0.001",
  "price": null
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `symbol` | string | Yes | Uppercase symbol |
| `side` | string | Yes | `BUY` or `SELL` |
| `type` | string | Yes | `MARKET` or `LIMIT` |
| `quantity` | string | Yes | Positive decimal |
| `price` | string \| null | LIMIT only | Required for limit orders |

**Success response (`200`)**

```json
{
  "success": true,
  "order": {
    "order_id": "123456789",
    "status": "FILLED",
    "executed_qty": "0.001",
    "average_price": "95000.5",
    "client_order_id": "abc123"
  }
}
```

**Error response (`400` / `500`)**

```json
{
  "detail": "Binance API error: Margin is insufficient."
}
```

### `POST /api/dashboard`

Return account, balance, position, and order data for a symbol.

**Request body**

```json
{
  "symbol": "BTCUSDT"
}
```

**Success response (`200`)**

```json
{
  "success": true,
  "dashboard": {
    "symbol": "BTCUSDT",
    "summary": {
      "total_wallet_balance": "1000",
      "available_balance": "950",
      "total_margin_balance": "1000",
      "unrealized_pnl": "0",
      "initial_margin": "50",
      "maintenance_margin": "10"
    },
    "balances": [],
    "positions": [],
    "open_orders": [],
    "recent_orders": []
  }
}
```

---

## Deployment

Deploy the **backend first**, then the frontend, then update CORS on the backend.

### Railway / Render / similar platforms

| Setting | Value |
|---------|-------|
| Root directory | `trading_bot` |
| Start command | `uvicorn server:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |

### Required platform environment variables

```env
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
BINANCE_BASE_URL=https://testnet.binancefuture.com
FRONTEND_ORIGIN=https://your-frontend-domain.com
```

### Deployment checklist

1. Deploy backend and generate a public URL
2. Verify `GET /health`
3. Deploy frontend with `BACKEND_API_URL` pointing to the backend URL
4. Set `FRONTEND_ORIGIN` on the backend to the frontend URL
5. Redeploy backend if CORS was not configured initially

### Verify deployed backend

```bash
curl https://your-backend.example.com/health
```

```bash
curl -X POST https://your-backend.example.com/api/orders \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","side":"BUY","type":"MARKET","quantity":"0.001"}'
```

No code changes are required before deployment. Configuration is handled through environment variables and the platform start command.

---

## Logging

Logs are written to:

```text
logs/app.log
```

The logger records:

- API request payloads
- Binance API responses
- Recoverable errors
- Full stack traces for unexpected exceptions

Log files rotate at 1 MB with up to 5 backups. Sample log output is available in `sample_logs/`.

On cloud platforms, use the platform deploy logs for runtime visibility. File logs on ephemeral disks may not persist across restarts.

---

## Error Handling

| Exception | When it occurs |
|-----------|----------------|
| `ConfigurationError` | Missing or invalid environment variables |
| `ValidationError` | Invalid user input |
| `OrderExecutionError` | Binance API rejection or network failure |
| `TradingBotError` | Base class for recoverable application errors |

Common Binance API messages surfaced to callers:

- `Invalid symbol`
- `Margin is insufficient`
- `Network timeout while contacting Binance`

Validation happens before any API call. Binance enforces quantity/price precision and account balance limits.

---

## Troubleshooting

### `Missing required environment variable(s)`

Ensure `.env` exists in `trading_bot/` and contains both `BINANCE_API_KEY` and `BINANCE_API_SECRET`. On deployed platforms, set these in the service environment variables panel.

### `Price is required for LIMIT orders`

Provide `--price` for CLI usage or include `"price"` in the JSON/API body for limit orders.

### `Price is only accepted for LIMIT orders`

Remove `--price` or the `price` field when placing market orders.

### `Binance API error: Invalid symbol`

Confirm the symbol exists on Binance USDT-M Futures Testnet and is uppercase, for example `BTCUSDT`.

### `Binance API error: Margin is insufficient`

Your testnet account does not have enough available margin for the requested quantity. Try a smaller quantity such as `0.001`, or add testnet funds from the Binance Futures Testnet site. Check balances on the frontend Dashboard page.

### `Network timeout while contacting Binance`

Check your internet connection and confirm the testnet endpoint is reachable from your network or hosting provider.

### CORS errors in the browser

Set `FRONTEND_ORIGIN` on the backend to the exact frontend URL, including protocol (`https://`). Redeploy after updating the variable.

### Frontend cannot reach backend

Confirm the frontend has `BACKEND_API_URL` set to the deployed backend URL with no trailing path segments beyond the base URL.

---

## Assumptions

- The application targets **Binance USDT-M Futures Testnet only**, not live trading
- LIMIT orders use **GTC** (Good Till Cancelled) time in force
- Quantity and price precision are ultimately enforced by Binance; the app validates positive decimal values only
- Average price is calculated from `cumQuote / executedQty` when execution quantity is present; open unfilled limit orders show `0`
- The HTTP API is intended for use with the companion frontend and is not authenticated beyond CORS browser restrictions

---

## Related Frontend

The Next.js frontend lives in the sibling `frontend/` directory at the repository root.

See `frontend/README.md` for:

- Local development setup
- Frontend environment variables
- Vercel deployment
- Order Ticket and Dashboard UI usage
