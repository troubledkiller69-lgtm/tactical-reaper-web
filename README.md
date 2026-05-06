# BIFROST | Industrial OSINT & Disruption (v18.4)

BIFROST is a high-efficiency command console designed for industrial data acquisition and operational intelligence.

## 🏛️ Project Structure

| Directory | Purpose |
| :--- | :--- |
| `api/` | Consolidated serverless backend routes (Vercel). Kept to 10 functions to bypass Hobby limit. |
| `core/` | Shared logic, database models, and engines. |
| `data/` | Static datasets (CSV/JSON). |
| `utils/` | Maintenance scripts (Key Gen, Discord Bot). |
| `tests/` | Debugging and connectivity verification. |
| `archive/`| Retired legacy modules and logs. |

## 🚀 Deployment & Hosting

### Frontend
Hosted on **Vercel** for global edge performance. Supports SPA routing (e.g., `/osint`).

### Background Operations & API ("The Brain")
We are migrating heavy operations to **Hugging Face Spaces (`rxtri/bifrost`)** using a Docker SDK.
This overcomes Vercel's strict 10-second serverless execution limits and 12-function count restrictions on the Hobby tier.

## 🔑 Authentication
Authentication is managed via the **Discord-Sync Auth Bridge**. New keys are generated in Discord and synced to the `AUTH_CHANNEL_ID` vault.
Administrative access is secured via `ADMIN_KEY` giving access to the hidden Commander Console on the frontend for deploying licenses.

## 📈 Recent Changes (v18.0 -> v18.4)
- **Deep Purge**: Archived all legacy clutter.
- **Serverless Limits Bypassed**: Consolidated 14 API functions down to 10 unified endpoints (`auth`, `disruption`, `osint`) to fit Vercel Hobby plan constraints.
- **Commander Console**: Added an exclusive Admin UI directly in the dashboard to generate and deploy licenses to Discord without leaving the browser.
- **Zero-Dependency Auth**: Rewrote `api/auth.py` using pure Python `urllib` to eliminate cold-start `NameError` crashes with external libraries like `requests`. Fixed return-type `ValueError` when environment variables are missing.
- **UI State**: Grayed out the Email Flood tool (`[SYSTEM OFFLINE]`) due to Brevo account suspension.

## 📝 Current Plans
- **Hugging Face Migration**: Complete the migration of the BIFROST "Super-Server" (FastAPI backend + Discord Bot) to the new Hugging Face Space.
- **Relink Frontend**: Re-point Vercel frontend tools to call the new Hugging Face endpoints instead of Vercel serverless routes.

## ⚠️ Known Issues
- **Brevo Suspension**: The primary SMTP relay account on Brevo has been suspended, rendering the Email Flood tool inoperable for the time being.
- **Hugging Face Secrets Config**: Encountered severe UI glitches/rate limits when trying to automate adding secrets to the HF Space settings. Had to resort to manual user input.
