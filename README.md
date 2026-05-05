# BIFROST | Industrial OSINT & Disruption (v18.0)

BIFROST is a high-efficiency command console designed for industrial data acquisition and operational intelligence.

## 🏛️ Project Structure

| Directory | Purpose |
| :--- | :--- |
| `api/` | Serverless backend routes (Vercel). |
| `core/` | Shared logic, database models, and engines. |
| `data/` | Static datasets (CSV/JSON). |
| `utils/` | Maintenance scripts (Key Gen, Discord Bot). |
| `tests/` | Debugging and connectivity verification. |
| `archive/`| Retired legacy modules and logs. |

## 🚀 Deployment & Hosting

### Frontend/API
Hosted on **Vercel** for global edge performance. Supports SPA routing (e.g., `/osint`).

### Background Operations (Key Gen / Discord Bot)
For persistent background tasks, we recommend:
1.  **Oracle Cloud (Always Free)**: 4 OCPUs, 24GB RAM. Ideal for high-volume Discord bots.
2.  **Google Cloud (Free Tier)**: e2-micro instance for lightweight Python services.

## 🔑 Authentication
Authentication is managed via the **Discord-Sync Auth Bridge**. New keys are generated in Discord and synced to the `AUTH_CHANNEL_ID` vault.

---
**DEVELOPER NOTE**: v18.0 Deep Purge completed. All legacy clutter archived.
