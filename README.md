# TACTICAL REAPER | INDUSTRIAL OSINT & DISRUPTION
**[ ENI_SYSTEM_CORE // VERSION: 6.3 // STATUS: OPERATIONAL ]**

## ⚡ Overview
Tactical Reaper is a high-fidelity OSINT and tactical disruption suite. Built on a serverless SPA architecture with a focus on stealth, precision, and immersive aesthetics. The platform combines a web-based command dashboard with cloud-hosted backends powering 47+ operational features, utilizing Vercel Edge functions and Supabase.

## 🌐 Web Dashboard (index.html)

### Tabs
- **DASHBOARD** — BIN Intel lookup, Email Flood dispatch, Ghost SMS broadcast
- **OPS MAP** — Real-time global node monitoring with 12 data centers, absolute geospatial mapping, and topographical overlay
- **PORTAL RECON** — 120+ institutional DXOnline portal index with BIN mapping, infrastructure categorization (s1/s2), and direct access links
- **STORM MATRIX** — Bulk authorization charge engine with hit vault and live stats
- **TG OPS** — Telegram mass-reporting and spam engine with:
  - 🎯 **Reporter**: Target input, 6 report reasons, custom message override
  - 💀 **Spammer**: Channel flood, DM blast, mass join modes with per-account message spinning
  - ⚙️ **Account Tokens**: Import Telegram API credentials. Accounts persist in localStorage and render as cards.
- **CHANGE LOG** — Version history stream
- **LOGS** — Real-time operation log feed

### Auth (Identity-Bound Login)
- Strict Operator ID + Access Key model.
- Validation handled via Supabase API ensuring keys are active and bound to the specific operator.
- Session persistence via sessionStorage.

## 🤖 Serverless Infrastructure & Discord

The platform has migrated away from local bot scripts to a 24/7 cloud architecture.

### Discord Bot (api/discord.py)
Hosted entirely as a Vercel Serverless Function serving Discord Interactions.
- `/genkey operator_id:X hours:Y` — Generates identity-bound keys and pushes them to Supabase.
- `/revoke key:X` — Instantly severs access by setting the key status to 'revoked' in the database.

### Supabase Backend
- **Keys Table**: Stores `key`, `operator_id`, `status` (active/revoked), and `duration_hours`.
- Handled via Row Level Security (RLS) configured to allow seamless client-side verification and secure server-side mutation.

## 🚧 In Development: DX Dumper (dx_dumper.py)
The Tactical Reaper Arsenal is expanding with a dedicated DXOnline infrastructure dumper.
**Planned Features:**
- **Multi-Threaded Architecture**: High-speed concurrent scraping of DXOnline portals.
- **Proxy Rotation**: Native SOCKS5/HTTP proxy integration to prevent IP bans during mass data acquisition.
- **Automated Captcha Resolution**: Integration with third-party solvers (or headless bypass techniques) to seamlessly slip through hCaptcha/reCAPTCHA gates on s1/s2 portals.
- **Data Extraction**: Automated harvesting of BINs, routing numbers, and institutional metadata directly into the tactical suite.

## 📡 Deployment

### Architecture
- **Frontend & API**: Hosted on Vercel (`vercel.json` configured for Python runtimes).
- **Database**: Hosted on Supabase.

### URLs
- **Production Dashboard**: [https://tactical-reaper-web.vercel.app/](https://tactical-reaper-web.vercel.app/)
- **Discord Endpoint**: `https://tactical-reaper-web.vercel.app/api/discord`

## 🔧 Environment (.env / Vercel Vars)
```
DISCORD_PUBLIC_KEY=
SUPABASE_URL=
SUPABASE_KEY=
# Legacy Telegram Configs
BOT_TOKEN=
API_ID=
API_HASH=
```

## 📜 Version History
- **v7.0 (Serverless Shift)**: Full migration to Vercel Edge functions, Supabase Identity-Bound Auth, and Discord Interactions Endpoint.
- **v6.3 (TG OPS)**: New TG OPS tab — Telegram reporter/spammer interface.
- **v6.2 (Precision Strike)**: Surgical offset correction for ops map node alignment.

---
**[ ACCESS RESTRICTED // OPERATOR ID REQUIRED ]**
⚡
