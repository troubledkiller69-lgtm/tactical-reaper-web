# BIFROST | Industrial OSINT & Disruption (v20.0)

BIFROST is a high-efficiency command console designed for industrial data acquisition and operational intelligence.

## 🏛️ Project Structure

| Directory | Purpose |
| :--- | :--- |
| `api/` | Consolidated serverless backend routes (Vercel). Kept under 12 functions to bypass Hobby limit. |
| `core/` | Shared logic, database models, and engines. |
| `data/` | Static datasets (CSV/JSON). |
| `utils/` | Maintenance scripts (Key Gen, Discord Bot). |
| `tests/` | Debugging and connectivity verification. |
| `archive/`| Retired legacy modules and logs. |
| `hf_space/`| Dockerized Hugging Face Space for long-running bots and heavy background processes. |

## 🚀 Deployment & Hosting

### Frontend & Core APIs
Hosted on **Vercel** for global edge performance. The primary Auth Engine, Disruption Suite, and SPA routing run here to bypass external firewall restrictions.

### Background Operations ("The Brain")
Long-running processes (e.g., the persistent Discord Bot) are hosted on **Hugging Face Spaces (`rxtri/bifrost`)** using a Docker SDK.

## 🔑 Authentication
Authentication is managed via the **Discord-Sync Auth Bridge** hosted on Vercel. New keys are generated in Discord and synced to the `AUTH_CHANNEL_ID` vault.
Administrative access is secured via `ADMIN_KEY` giving access to the hidden Commander Console on the frontend for deploying licenses.
**Security:** Mandatory Access Control (MAC) enforces role-based access (`commander`) to prevent unauthorized URL bypasses into the admin deck.

## 📈 Recent Changes (v19.0 -> v20.0)
- **"Black Ice" Aesthetic Overhaul**: Fully transitioned the visual identity to a high-fidelity "Black Ice" theme. Features include custom radial gradients, atmospheric light rays, and a unified arctic-noir palette across all application views.
- **Credits & Operations Hub**: Replaced the legacy map with a high-density Credits module. Features a non-scrolling two-column grid for contributors and a dedicated "Operational Links" section for verified contacts (Telegram/Discord).
- **Consolidated Data Architecture**: Integrated real-time system stats (Active Proxies, Intel Hits, API UPTIME) directly into the "Intel Data Stream" card for a more efficient operational layout.
- **Vendor Dashboard 2.0**: Re-engineered the Vendor/Merchant interface with absolute top-level positioning, a clean registration approval flow, and a simplified minimalist footer.
- **Brand Finalization**: Removed all legacy "Tactical Reaper" identifiers, including branding in the footer and internal heartbeat telemetry logs.

## 📝 Current Plans
- **Operational Expansion**: Finalize the "Checker" (formerly Storm Matrix) and "Sniper" tools.
- **Bot Persistence**: Maintain stable Discord Bot integration via Hugging Face.

## ⚠️ Known Issues
- **Brevo Suspension**: The primary SMTP relay account on Brevo has been suspended, rendering the Email Flood tool inoperable.
- **Hugging Face Discord Block**: Outbound Discord API requests remain locked to Vercel due to HF firewall restrictions.
