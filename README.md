# Trading Bot Frontend

Next.js web interface for placing orders and viewing account data on **Binance USDT-M Futures Testnet**.

## Live Demo
https://tradingbot-frontend-gamma.vercel.app/

The frontend provides two pages:

- **Order Ticket** — submit MARKET and LIMIT orders
- **Dashboard** — view balances, positions, open orders, and recent order history

Binance API credentials stay on the Python backend. The browser never receives API keys. All trading requests go through Next.js API routes, which forward requests to the backend.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Locally](#running-locally)
- [Pages and Routes](#pages-and-routes)
- [Backend Integration](#backend-integration)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Related Backend](#related-backend)

---

## Features

- Place **MARKET** and **LIMIT** orders with **BUY** / **SELL** sides
- Live request preview before submission
- Structured success and error responses from the backend
- Dashboard with account summary cards
- Asset balances, open positions, open orders, and recent order history
- Symbol search/filter on the dashboard
- Responsive trading-style UI with Lucide icons
- Two backend connection modes: HTTP API (production) and local Python bridge (development)

---

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| [Next.js](https://nextjs.org/) | 16.x | App Router, API routes, production build |
| [React](https://react.dev/) | 19.x | UI components |
| [TypeScript](https://www.typescriptlang.org/) | 5.9.x | Type safety |
| [Lucide React](https://lucide.dev/) | 0.468.x | Icons |

---

## Project Structure

```text
frontend/
├── app/
│   ├── api/
│   │   ├── _lib/
│   │   │   └── backend.ts       # Backend forwarding logic
│   │   ├── dashboard/
│   │   │   └── route.ts         # POST /api/dashboard
│   │   └── orders/
│   │       └── route.ts         # POST /api/orders
│   ├── dashboard/
│   │   └── page.tsx             # Dashboard page
│   ├── globals.css              # Global styles
│   ├── layout.tsx               # Root layout and metadata
│   └── page.tsx                 # Order Ticket page
├── .env.example                 # Environment variable template
├── .gitignore
├── next.config.ts
├── package.json
├── tsconfig.json
└── README.md
```

---

## Prerequisites

- **Node.js 18+** (recommended: latest LTS)
- **npm** (comes with Node.js)
- A running Python backend (`trading_bot/`) for order and dashboard data

---

## Installation

Move into the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Copy the environment template:

```bash
cp .env.example .env.local
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env.local
```

---

## Configuration

Create `.env.local` in the `frontend/` directory.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BACKEND_API_URL` | Production: yes | Base URL of the deployed FastAPI backend |
| `TRADING_BOT_BACKEND_DIR` | Local dev only | Absolute path to the `trading_bot` folder when using Python subprocess mode |

### Local development (recommended)

**Option A — HTTP mode (matches production)**

1. Start the backend:

   ```bash
   cd ../trading_bot
   uvicorn server:app --reload --host 0.0.0.0 --port 8000
   ```

2. Configure the frontend:

   ```env
   BACKEND_API_URL=http://127.0.0.1:8000
   ```

**Option B — Python subprocess mode**

If `BACKEND_API_URL` is not set, the frontend spawns `api_order.py` and `api_dashboard.py` directly. This requires Python installed locally.

```env
TRADING_BOT_BACKEND_DIR=D:\path\to\trading_bot
```

On macOS/Linux:

```env
TRADING_BOT_BACKEND_DIR=/path/to/trading_bot
```

If `TRADING_BOT_BACKEND_DIR` is omitted, the app looks for a sibling `../trading_bot` directory relative to the frontend project root.

### Production

Set only the backend URL. Do **not** set `TRADING_BOT_BACKEND_DIR` on Vercel or similar platforms.

```env
BACKEND_API_URL=https://your-backend.example.com
```

Also set `FRONTEND_ORIGIN=https://your-frontend-domain.com` on the backend for CORS.

---

## Running Locally

Start the development server:

```bash
npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

Dashboard:

```text
http://127.0.0.1:3000/dashboard
```

### Available scripts

| Script | Command | Description |
|--------|---------|-------------|
| Dev server | `npm run dev` | Start Next.js in development mode |
| Production build | `npm run build` | Create an optimized production build |
| Production server | `npm start` | Run the production build locally |
| Lint | `npm run lint` | Run ESLint |

---

## Pages and Routes

### Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Order Ticket | Submit MARKET/LIMIT orders |
| `/dashboard` | Dashboard | View account and trading data |

### Order Ticket

Default form values:

- Symbol: `BTCUSDT`
- Side: `BUY`
- Type: `MARKET`
- Quantity: `0.001`

On submit, the page calls `POST /api/orders` and displays:

- **Success:** order ID, status, executed quantity, average price, client order ID
- **Failure:** backend error message (for example insufficient margin)

### Dashboard

Loads data for the selected symbol via `POST /api/dashboard`.

Sections:

- Account summary cards (wallet balance, available balance, margin, PnL)
- Asset balances
- Open positions
- Open orders
- Recent order history

Use the symbol input and refresh control to reload data for a different pair.

### Next.js API routes

| Route | Method | Forwards to backend |
|-------|--------|---------------------|
| `/api/orders` | POST | `/api/orders` |
| `/api/dashboard` | POST | `/api/dashboard` |

These routes are server-side only. The browser never talks to the Python backend directly.

---

## Backend Integration

Request flow:

```text
Browser
  |
  v
Next.js page (page.tsx / dashboard/page.tsx)
  |
  v
Next.js API route (/api/orders or /api/dashboard)
  |
  v
app/api/_lib/backend.ts
  |
  +-- if BACKEND_API_URL is set --> HTTP POST to FastAPI backend
  |
  +-- otherwise --> spawn Python bridge script locally
```

### Order request payload

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "quantity": "0.001"
}
```

For limit orders, include `"price"`.

### Dashboard request payload

```json
{
  "symbol": "BTCUSDT"
}
```

### Success order response

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

### Error response

```json
{
  "success": false,
  "error": "Binance API error: Margin is insufficient."
}
```

---

## Deployment

Deploy the **backend first**, then the frontend.

### Step 1: Deploy backend

Deploy `trading_bot/` to Railway, Render, or another Python host.

See `trading_bot/README.md` for backend deployment details.

Verify:

```bash
curl https://your-backend.example.com/health
```

### Step 2: Deploy frontend to Vercel

1. Import the repository into [Vercel](https://vercel.com)
2. Set **Root Directory** to `frontend`
3. Add environment variable:

   ```env
   BACKEND_API_URL=https://your-backend.example.com
   ```

4. Deploy

Vercel auto-detects Next.js and runs `npm run build`.

### Step 3: Update backend CORS

On the backend platform, set:

```env
FRONTEND_ORIGIN=https://your-frontend.vercel.app
```

Redeploy the backend so browser requests from the frontend are allowed.

### Deployment checklist

- [ ] Backend deployed and `/health` returns `{"status":"ok"}`
- [ ] `BACKEND_API_URL` set on Vercel
- [ ] `FRONTEND_ORIGIN` set on backend
- [ ] Testnet API keys configured on backend only
- [ ] Order Ticket and Dashboard tested in production

### What not to deploy

These are ignored via `.gitignore` and should not be committed:

- `node_modules/`
- `.next/`
- `.env.local`
- `.env`

Use Vercel project environment variables instead of committing secrets.

---

## Troubleshooting

### `Unable to start Python process`

You are in local subprocess mode without a working Python installation, or `TRADING_BOT_BACKEND_DIR` is wrong.

**Fix:** Set `BACKEND_API_URL` to a running FastAPI backend instead.

### `Backend request failed` / network errors

The frontend cannot reach the backend URL.

**Fix:**

- Confirm `BACKEND_API_URL` is correct
- Confirm the backend is running and publicly accessible
- Remove trailing slashes if the URL was copied incorrectly

### CORS error in browser console

The backend does not allow your frontend origin.

**Fix:** Set `FRONTEND_ORIGIN` on the backend to your exact Vercel URL and redeploy.

### `Binance API error: Margin is insufficient`

The request reached Binance successfully, but the testnet account lacks margin for the order size.

**Fix:**

- Use a smaller quantity such as `0.001`
- Add testnet funds from the Binance Futures Testnet site
- Check available balance on the Dashboard page

### Dashboard shows no data

Confirm backend credentials are valid and the selected symbol exists on testnet.

### Build fails on Vercel

- Ensure root directory is set to `frontend`
- Confirm Node.js 18+ is selected in project settings
- Run `npm run build` locally to reproduce the error

### Orders work locally but not in production

Production requires `BACKEND_API_URL`. Subprocess mode does not work on Vercel.

---

## Related Backend

The Python backend lives in `trading_bot/` at the repository root.

See `trading_bot/README.md` for:

- CLI usage
- FastAPI server setup
- Binance configuration
- API reference
- Backend deployment on Railway/Render

### Recommended local workflow

Terminal 1 — backend:

```bash
cd trading_bot
uvicorn server:app --reload --port 8000
```

Terminal 2 — frontend:

```bash
cd frontend
npm run dev
```

With `BACKEND_API_URL=http://127.0.0.1:8000` in `.env.local`.
