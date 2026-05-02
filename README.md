# TACTICAL REAPER | INDUSTRIAL OSINT & DISRUPTION
**[ ENI_SYSTEM_CORE // VERSION: 7.0 // STATUS: OPERATIONAL ]**

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

## 🚧 Roadmap & Architecture Plan

The Tactical Reaper Arsenal is expanding into a comprehensive, multi-layered disruption and OSINT suite. 

### 📡 The Signal: SMTP & SMS Expansion
- **SMS Spamming**: Sourcing high-throughput, low-filter international gateways (TBomb multi-nodes) to bypass aggressive US WAFs.
- **SMTP Relay**: Deploying iron-clad email infrastructure (SendGrid/Mailgun) for high-volume delivery.

### 🎯 The Sniper: High-Fidelity Acquisition
- **Multi-Threaded Monitor**: Sniping site updates and securing targets instantly using stored credentials.
- **Captcha Bypass**: Deep integration with solver APIs (CapSolver) for zero-friction automation.

### 🕵️ The Dumpers: Infrastructure Reversal
- **DXO Dumper**: A specialized multi-threaded crawler designed to enumerate and dump all DXOnline portals (`dxonline-apps-*-cloud.pscu.com`) with proxy rotation and captcha solvers.
- **CardValet Dumper**: Reversing the Fiserv/CardValet ecosystem to build a searchable database of the PSCU/Fiserv landscape.
- **Cross-Referencing**: Automated mapping of BINs directly to their respective DXO portals.

### 🛰️ Signal Intel & Tracking
- **Link Tracer**: Custom tracking link generation to capture IP, User-Agent, and metadata.
- **Geo Locator**: Instant IP-to-Geolocation reversal (city, country, ISP, physical coordinates).

### 💰 Monetization: The Gatekeeper
- **License Key System**: Multi-tier licensing gate (Daily/Weekly/Monthly/Lifetime) with crypto-only payment integration.
- **Telegram Licensing Bot**: Automated purchasing, redeeming, and managing of operator licenses.

### 🛡️ Hardening: DDoS Protection & Stealth
- **Mitigation Layer**: Integrating specialized protection (Cloudflare, DDoS-Guard) to absorb malicious traffic.
- **Reverse Proxy**: Multi-layered architecture to keep the backend infrastructure entirely hidden.
- **Rate Limiting**: Real-time traffic scrubbing on all API endpoints.

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
