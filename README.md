# BIFROST | Industrial OSINT & Disruption (v19.0)

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

## 📈 Recent Changes (v18.4 -> v19.0)
- **Vercel API Migration Pivot**: Moved the BIFROST Auth Engine and Disruption API back to Vercel. Discovered a hard firewall block on Hugging Face that prevented outgoing Python `requests` to Discord APIs (resulting in persistent HTTP 500 crashes).
- **Mandatory Access Control (MAC)**: Hardened the Commander Console. Non-admin operators are instantly redirected to the dashboard if they attempt to bypass UI navigation and hit `/admin` directly.
- **Cinematic UI Overhaul**: Re-engineered the main header to be a full-width edge-to-edge band, improving visual balance for widescreen displays while maintaining centered content alignment.
- **Extreme Diagnostic Tracing**: Added verbose exception propagation to the frontend to accurately trace network failures during the HF debugging phase.

## 📝 Current Plans
- **Operational Expansion**: Begin building out the Storm Matrix and Sniper tools.
- **Bot Persistence**: Ensure the Hugging Face Space maintains the persistent Discord Bot connection independently from the Vercel API routes.

## ⚠️ Known Issues
- **Brevo Suspension**: The primary SMTP relay account on Brevo has been suspended, rendering the Email Flood tool inoperable for the time being.
- **Hugging Face Discord Block**: Hugging Face Spaces block direct outbound HTTP requests to discord.com/api, meaning all vault and logging APIs must reside on Vercel.
