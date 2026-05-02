# TACTICAL REAPER | INDUSTRIAL OSINT & DISRUPTION
**[ ENI_SYSTEM_CORE // VERSION: 6.3 // STATUS: OPERATIONAL ]**

## ⚡ Overview
Tactical Reaper is a high-fidelity OSINT and tactical disruption suite. Built on a monolithic SPA architecture with a focus on stealth, precision, and immersive aesthetics. The platform combines a web-based command dashboard with a Telegram-controlled bot backend powering 47+ operational features.

## 🌐 Web Dashboard (index.html)

### Tabs
- **DASHBOARD** — BIN Intel lookup, Email Flood dispatch, Ghost SMS broadcast
- **OPS MAP** — Real-time global node monitoring with 12 data centers, particle-based transit physics, and topographical overlay
- **PORTAL RECON** — 120+ institutional DXOnline portal index with BIN mapping, infrastructure categorization (s1/s2), and direct access links
- **STORM MATRIX** — Bulk authorization charge engine with hit vault and live stats
- **TG OPS** — Telegram mass-reporting and spam engine with:
  - 🎯 **Reporter**: Target input, 6 report reasons (spam/violence/pornography/child abuse/copyright/other), per-account report volume, custom message override
  - 💀 **Spammer**: Channel flood, DM blast, mass join modes with per-account message spinning
  - ⚙️ **Account Tokens**: Import Telegram API credentials (session name, API ID, API hash, phone). Accounts persist in localStorage and render as cards with green status indicators. Add/remove accounts on the fly.
- **CHANGE LOG** — Version history stream
- **LOGS** — Real-time operation log feed

### Auth
- Operator login gate with session persistence (sessionStorage)
- Login/Register tabs

## 🤖 Telegram Bot Backend

### Core Files
| File | Purpose |
|------|---------|
| `bot_controller.py` | Main Telegram bot hub — all commands, progress reporting, scheduling, campaigns |
| `email_flooder.py` | Email flood engine — 1.5M+ template combos, SMTP pooling, PDF attachments, coherent subject-body |
| `ghost_sms.py` | SMS via carrier gateways — 16 carriers, 30+ templates, adaptive rate intelligence |
| `eni_reper.py` | Telegram mass ops — report/join/spam/DM/scrape with batch parallel, stealth mode |
| `database.py` | SQLite license key management with thread-safe transactions |
| `history_manager.py` | JSON-based operation logging with atomic writes |
| `discord_bot.py` | Discord admin bot for key generation |
| `dx_identifier.py` | DXOnline portal identification |

### Bot Commands
| Command | Description |
|---------|-------------|
| `/email` | Email flood (single or comma-separated multi-target) |
| `/ghost` | Ghost SMS blast (single or multi-target) |
| `/report` | Mass Telegram reporting with stealth mode option |
| `/flood_tg` | Telegram channel spam |
| `/dm` | DM blast to comma-separated usernames |
| `/join` | Mass join target channels |
| `/scrape` | Scrape usernames from channels/groups |
| `/campaign` | Chain multiple attack vectors sequentially |
| `/schedule` | Schedule any command to run after delay |
| `/scheduled` | List pending scheduled operations |
| `/unschedule` | Cancel a scheduled operation |
| `/addaccount` | Interactive Telegram account import wizard |
| `/cancel` | Cancel active operation |

### Engine Features
- **Email**: Subject-body coherence, SMTP connection pooling, email threading headers, PDF attachments, HTML templates, signature pool, from-name randomization, anti-detection EHLO, rate intelligence
- **SMS**: 16 carrier gateways, weighted carrier selection, warmup delays, anti-detection timing, per-message retry
- **Telegram**: Batch parallel processing, adaptive batch sizing, FloodWait auto-retry, device fingerprint rotation, proxy rotation (SOCKS5), message spinning, stealth reporting (join→browse→report), report message randomization, persistent health state
- **Operations**: Campaign chaining, operation scheduling, target file upload, result export, per-user cooldowns, live progress bars

## 📡 Deployment

### Web Dashboard
- **Local**: Open `index.html` directly or `python -m http.server 8000`
- **Production**: [https://tactical-reaper-web.vercel.app/](https://tactical-reaper-web.vercel.app/)
- **Deploy**: Push to `main` on `troubledkiller69-lgtm/tactical-reaper-web` — Vercel auto-deploys

### Bot Backend
```bash
pip install -r requirements.txt
# Configure .env with all credentials
python bot_controller.py
```

## 🔧 Environment (.env)
```
BOT_TOKEN=
API_ID=
API_HASH=
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASS=
SENDER_EMAIL=
GHOST_SENDER_EMAIL=
# Optional: SMTP_HOST_2, SMTP_PORT_2, etc. for multi-SMTP
# Optional: PROXY_LIST=socks5://user:pass@host:port
```

## 📜 Version History
- **v6.3 (TG OPS)**: New TG OPS tab — Telegram reporter/spammer interface with account token import and pool management
- **v6.2 (Precision Strike)**: Surgical offset correction for ops map node alignment
- **v6.1 (Omega Sync)**: Triangulated ground coordinates
- **v5.0 (Constellation)**: Global node expansion with shooting star trails

---
**[ ACCESS RESTRICTED // OPERATOR ID REQUIRED ]**
⚡
