import os
import json
import hashlib
import secrets
import time
import requests as http_client
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# BIFROST CARD SHOP ENGINE (v20.0)
# Unified serverless handler for marketplace + merchant operations.

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
ADMIN_KEY = os.getenv("ADMIN_KEY", "").strip()
PLISIO_KEY = os.getenv("PLISIO_KEY", "").strip()
REST = f"{SUPABASE_URL}/rest/v1"
PLISIO_API = "https://plisio.net/api/v1"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ─── Crypto helpers ───

def hash_password(password, salt=None):
    if not salt:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return h.hex(), salt

def verify_password(password, stored_hash, salt):
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return h.hex() == stored_hash

# ─── Supabase helpers ───

def sb_get(table, params=""):
    r = http_client.get(f"{REST}/{table}?{params}", headers=HEADERS, timeout=10)
    return r.status_code, r.json() if r.status_code == 200 else r.text

def sb_post(table, data):
    r = http_client.post(f"{REST}/{table}", json=data, headers=HEADERS, timeout=10)
    return r.status_code, r.json() if r.status_code in [200, 201] else r.text

def sb_patch(table, match, data):
    h = {**HEADERS, "Prefer": "return=representation"}
    r = http_client.patch(f"{REST}/{table}?{match}", json=data, headers=h, timeout=10)
    return r.status_code, r.json() if r.status_code == 200 else r.text

def sb_delete(table, match):
    r = http_client.delete(f"{REST}/{table}?{match}", headers=HEADERS, timeout=10)
    return r.status_code, r.text

# ─── RPC helper for atomic transactions ───

def sb_rpc(fn_name, params):
    r = http_client.post(
        f"{SUPABASE_URL}/rest/v1/rpc/{fn_name}",
        json=params, headers=HEADERS, timeout=10
    )
    return r.status_code, r.json() if r.status_code == 200 else r.text


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Key, X-Merchant-Token, X-Operator-Id")
        self.end_headers()

    def do_GET(self):
        self._route()

    def do_POST(self):
        self._route()

    def do_DELETE(self):
        self._route()

    def _route(self):
        query = parse_qs(urlparse(self.path).query)
        action = query.get("action", [""])[0]
        body = {}
        if self.command == "POST":
            try:
                cl = int(self.headers.get("Content-Length", 0))
                if cl > 0:
                    body = json.loads(self.rfile.read(cl))
            except:
                body = {}

        routes = {
            # Operator-facing
            "browse": self.browse_bases,
            "preview": self.preview_base,
            "acquire": self.acquire_cards,
            "wallet": self.get_wallet,
            "my_cards": self.my_cards,
            "create_deposit": self.create_deposit,
            "check_payment": self.check_payment,
            # Plisio callback
            "payment_callback": self.payment_callback,
            # Admin
            "deposit": self.admin_deposit,
            "list_vendors": self.list_vendors,
            "approve_vendor": self.approve_vendor,
            # Merchant-facing
            "merchant_register": self.merchant_register,
            "merchant_login": self.merchant_login,
            "merchant_bases": self.merchant_bases,
            "merchant_stats": self.merchant_stats,
            "merchant_balance": self.merchant_balance,
            "upload_base": self.upload_base,
            "update_base": self.update_base,
            "delete_base": self.delete_base_action,
        }

        fn = routes.get(action)
        if fn:
            fn(query, body)
        else:
            self._json(400, {"error": f"Unknown action: {action}"})

    # ═══════════════════════════════════════════
    # OPERATOR ENDPOINTS
    # ═══════════════════════════════════════════

    def browse_bases(self, q, body):
        """List all active bases with merchant info. No raw card data."""
        params = "status=eq.active&select=id,name,bin,bank,country,card_type,card_level,price_per_card,quantity_available,uploaded_at,merchant_id,merchants(display_name)&order=uploaded_at.desc"

        # Optional filters
        bin_filter = q.get("bin", [""])[0]
        country_filter = q.get("country", [""])[0]
        bank_filter = q.get("bank", [""])[0]

        if bin_filter:
            params += f"&bin=ilike.{bin_filter}*"
        if country_filter:
            params += f"&country=ilike.*{country_filter}*"
        if bank_filter:
            params += f"&bank=ilike.*{bank_filter}*"

        code, data = sb_get("bases", params)
        if code == 200:
            # Flatten merchant name
            for base in data:
                m = base.pop("merchants", {})
                base["merchant_name"] = m.get("display_name", "Unknown") if m else "Unknown"
            self._json(200, {"bases": data, "count": len(data)})
        else:
            self._json(500, {"error": str(data)})

    def preview_base(self, q, body):
        """Show masked sample cards from a base."""
        base_id = q.get("base_id", [""])[0]
        if not base_id:
            self._json(400, {"error": "base_id required"})
            return

        code, cards = sb_get("cards", f"base_id=eq.{base_id}&status=eq.available&select=number,exp_month,exp_year,holder_name,country,city,state,zip&limit=5")
        if code == 200:
            masked = []
            for c in cards:
                num = c.get("number", "")
                masked_num = num[:6] + "XX" * ((len(num) - 10) // 2) + num[-4:] if len(num) >= 10 else "XXXX"
                masked.append({
                    "number": masked_num,
                    "exp": f"{c.get('exp_month','??')}/{c.get('exp_year','??')}",
                    "holder": c.get("holder_name", "")[:3] + "***" if c.get("holder_name") else "N/A",
                    "location": f"{c.get('city','')}, {c.get('state','')} {c.get('country','')}"
                })
            self._json(200, {"samples": masked, "base_id": base_id})
        else:
            self._json(500, {"error": str(cards)})

    def acquire_cards(self, q, body):
        """Purchase N cards from a base. Deducts operator wallet, credits merchant."""
        operator_id = self.headers.get("X-Operator-Id", "")
        base_id = body.get("base_id", "")
        count = int(body.get("count", 1))

        if not operator_id or not base_id:
            self._json(400, {"error": "operator_id and base_id required"})
            return

        # 1. Get base info + price
        code, bases = sb_get("bases", f"id=eq.{base_id}&status=eq.active&select=*")
        if code != 200 or not bases:
            self._json(404, {"error": "Base not found or inactive"})
            return
        base = bases[0]
        price = float(base["price_per_card"])
        total_cost = price * count
        merchant_id = base["merchant_id"]

        # 2. Check operator wallet
        wcode, wallets = sb_get("wallets", f"operator_id=eq.{operator_id}&select=*")
        if wcode != 200 or not wallets:
            self._json(400, {"error": "No wallet found. Contact admin for deposit."})
            return
        wallet = wallets[0]
        current_balance = float(wallet["balance"])

        if current_balance < total_cost:
            self._json(400, {"error": f"Insufficient balance. Need ${total_cost:.2f}, have ${current_balance:.2f}"})
            return

        # 3. Grab N available cards from this base
        ccode, available = sb_get("cards", f"base_id=eq.{base_id}&status=eq.available&select=*&limit={count}")
        if ccode != 200 or len(available) < count:
            actual = len(available) if ccode == 200 else 0
            self._json(400, {"error": f"Only {actual} cards available in this base."})
            return

        # 4. Mark cards as sold
        card_ids = [c["id"] for c in available]
        for cid in card_ids:
            sb_patch("cards", f"id=eq.{cid}", {"status": "sold"})

        # 5. Deduct operator balance
        new_balance = current_balance - total_cost
        sb_patch("wallets", f"operator_id=eq.{operator_id}", {
            "balance": new_balance,
            "total_spent": float(wallet["total_spent"]) + total_cost,
            "updated_at": "now()"
        })

        # 6. Credit merchant balance
        mcode, merchants = sb_get("merchants", f"id=eq.{merchant_id}&select=balance")
        if mcode == 200 and merchants:
            new_merch_balance = float(merchants[0]["balance"]) + total_cost
            sb_patch("merchants", f"id=eq.{merchant_id}", {"balance": new_merch_balance})

        # 7. Log transactions
        for c in available:
            sb_post("transactions", {
                "operator_id": operator_id,
                "merchant_id": merchant_id,
                "card_id": c["id"],
                "base_id": base_id,
                "tx_type": "purchase",
                "amount": price
            })

        # 8. Update base quantity
        sb_patch("bases", f"id=eq.{base_id}", {
            "quantity_available": max(0, int(base["quantity_available"]) - count)
        })

        # 9. Return full card data to buyer
        purchased = []
        for c in available:
            purchased.append({
                "number": c["number"],
                "exp": f"{c['exp_month']}/{c['exp_year']}",
                "cvv": c["cvv"],
                "holder": c.get("holder_name", ""),
                "address": c.get("address", ""),
                "zip": c.get("zip", ""),
                "city": c.get("city", ""),
                "state": c.get("state", ""),
                "country": c.get("country", "")
            })

        self._json(200, {
            "status": "acquired",
            "cards": purchased,
            "total_charged": total_cost,
            "new_balance": new_balance
        })

    def get_wallet(self, q, body):
        """Get operator's wallet balance."""
        operator_id = self.headers.get("X-Operator-Id", "") or q.get("operator_id", [""])[0]
        if not operator_id:
            self._json(400, {"error": "operator_id required"})
            return

        code, wallets = sb_get("wallets", f"operator_id=eq.{operator_id}&select=*")
        if code == 200 and wallets:
            w = wallets[0]
            self._json(200, {
                "balance": float(w["balance"]),
                "total_deposited": float(w["total_deposited"]),
                "total_spent": float(w["total_spent"])
            })
        else:
            # Auto-create wallet with 0 balance
            sb_post("wallets", {"operator_id": operator_id, "balance": 0, "total_deposited": 0, "total_spent": 0})
            self._json(200, {"balance": 0.00, "total_deposited": 0.00, "total_spent": 0.00})

    # ═══════════════════════════════════════════
    # PLISIO CRYPTO DEPOSITS
    # ═══════════════════════════════════════════

    def create_deposit(self, q, body):
        """Create a Plisio invoice for crypto deposit."""
        operator_id = self.headers.get("X-Operator-Id", "") or body.get("operator_id", "")
        amount = float(body.get("amount", 0))
        currency = body.get("currency", "BTC").upper()

        if not operator_id or amount < 5:
            self._json(400, {"error": "Operator ID and minimum $5 deposit required"})
            return

        if currency not in ["BTC", "LTC", "ETH"]:
            self._json(400, {"error": "Supported currencies: BTC, LTC, ETH"})
            return

        # Generate unique order ID
        order_id = f"BIFROST-{operator_id}-{secrets.token_hex(4)}-{int(time.time())}"

        # Determine callback URL (same API route)
        # Vercel auto-detects host from the request
        host = self.headers.get("Host", "")
        scheme = "https" if host else "http"
        callback_url = f"{scheme}://{host}/api/shop?action=payment_callback&json=true"

        try:
            resp = http_client.get(f"{PLISIO_API}/invoices/new", params={
                "source_currency": "USD",
                "source_amount": str(amount),
                "order_number": order_id,
                "order_name": f"BIFROST Deposit - {operator_id}",
                "currency": currency,
                "api_key": PLISIO_KEY,
                "callback_url": callback_url,
                "email": "noreply@bifrost.local",
            }, timeout=15)

            data = resp.json()

            if data.get("status") == "success" and data.get("data"):
                invoice = data["data"]
                # Store pending deposit in transactions
                sb_post("transactions", {
                    "operator_id": operator_id,
                    "tx_type": "deposit",
                    "amount": amount,
                })

                self._json(200, {
                    "status": "invoice_created",
                    "invoice_url": invoice.get("invoice_url", ""),
                    "amount_crypto": invoice.get("amount", ""),
                    "currency": currency,
                    "wallet_address": invoice.get("wallet_hash", ""),
                    "order_id": order_id,
                    "txn_id": invoice.get("txn_id", ""),
                    "amount_usd": amount,
                    "expires_at": invoice.get("expire_utc", ""),
                })
            else:
                error_msg = data.get("data", {}).get("message", "") if isinstance(data.get("data"), dict) else str(data)
                self._json(500, {"error": f"Plisio error: {error_msg}"})

        except Exception as e:
            self._json(500, {"error": f"Payment gateway error: {str(e)}"})

    def payment_callback(self, q, body):
        """Plisio IPN callback — auto-credit wallet on confirmed payment."""
        # Plisio sends POST with payment data
        cb = body if body else {}
        # Also check query params (Plisio sometimes sends as GET params)
        if not cb:
            cb = {k: v[0] for k, v in q.items()}

        status = cb.get("status", "")
        order_number = cb.get("order_number", "")
        amount_usd = cb.get("source_amount", cb.get("amount", "0"))

        if not order_number:
            self._json(400, {"error": "Missing order_number"})
            return

        # Parse operator_id from order: BIFROST-{operator_id}-{hex}-{ts}
        parts = order_number.split("-")
        if len(parts) < 3:
            self._json(400, {"error": "Invalid order format"})
            return
        operator_id = parts[1]

        # Only credit on completed/confirmed status
        if status in ["completed", "confirmed"]:
            try:
                amt = float(amount_usd)
            except:
                amt = 0

            if amt <= 0:
                self._json(400, {"error": "Invalid amount"})
                return

            # Credit wallet
            code, wallets = sb_get("wallets", f"operator_id=eq.{operator_id}&select=*")
            if code == 200 and wallets:
                w = wallets[0]
                new_bal = float(w["balance"]) + amt
                new_dep = float(w["total_deposited"]) + amt
                sb_patch("wallets", f"operator_id=eq.{operator_id}", {
                    "balance": new_bal,
                    "total_deposited": new_dep,
                    "updated_at": "now()"
                })
            else:
                sb_post("wallets", {
                    "operator_id": operator_id,
                    "balance": amt,
                    "total_deposited": amt,
                    "total_spent": 0
                })

            self._json(200, {"status": "credited", "operator": operator_id, "amount": amt})
        elif status in ["pending", "confirming"]:
            self._json(200, {"status": "pending", "message": "Waiting for confirmations"})
        else:
            self._json(200, {"status": "ignored", "payment_status": status})

    def check_payment(self, q, body):
        """Check payment status via Plisio."""
        txn_id = q.get("txn_id", [""])[0]
        if not txn_id:
            self._json(400, {"error": "txn_id required"})
            return
        try:
            resp = http_client.get(f"{PLISIO_API}/operations/{txn_id}", params={
                "api_key": PLISIO_KEY
            }, timeout=10)
            data = resp.json()
            if data.get("status") == "success":
                op = data.get("data", {})
                self._json(200, {
                    "status": op.get("status", "unknown"),
                    "amount": op.get("source_amount", "0"),
                    "currency": op.get("currency", ""),
                    "confirmations": op.get("confirmations", 0),
                })
            else:
                self._json(500, {"error": str(data)})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def my_cards(self, q, body):
        """Get operator's purchased cards."""
        operator_id = self.headers.get("X-Operator-Id", "") or q.get("operator_id", [""])[0]
        if not operator_id:
            self._json(400, {"error": "operator_id required"})
            return

        code, txs = sb_get("transactions", f"operator_id=eq.{operator_id}&tx_type=eq.purchase&select=card_id,amount,created_at,cards(number,exp_month,exp_year,cvv,holder_name,address,zip,city,state,country),bases(name,bin,bank)&order=created_at.desc&limit=100")
        if code == 200:
            results = []
            for tx in txs:
                c = tx.get("cards", {}) or {}
                b = tx.get("bases", {}) or {}
                results.append({
                    "number": c.get("number", ""),
                    "exp": f"{c.get('exp_month','')}/{c.get('exp_year','')}",
                    "cvv": c.get("cvv", ""),
                    "holder": c.get("holder_name", ""),
                    "address": c.get("address", ""),
                    "zip": c.get("zip", ""),
                    "city": c.get("city", ""),
                    "state": c.get("state", ""),
                    "country": c.get("country", ""),
                    "base_name": b.get("name", ""),
                    "bin": b.get("bin", ""),
                    "bank": b.get("bank", ""),
                    "price": float(tx.get("amount", 0)),
                    "purchased_at": tx.get("created_at", "")
                })
            self._json(200, {"cards": results, "count": len(results)})
        else:
            self._json(500, {"error": str(txs)})

    # ═══════════════════════════════════════════
    # ADMIN ENDPOINTS
    # ═══════════════════════════════════════════

    def admin_deposit(self, q, body):
        """Admin-only: credit an operator's wallet."""
        if self.headers.get("X-Admin-Key") != ADMIN_KEY:
            self._json(401, {"error": "UNAUTHORIZED"})
            return

        operator_id = body.get("operator_id", "")
        amount = float(body.get("amount", 0))

        if not operator_id or amount <= 0:
            self._json(400, {"error": "operator_id and positive amount required"})
            return

        # Check if wallet exists
        code, wallets = sb_get("wallets", f"operator_id=eq.{operator_id}&select=*")
        if code == 200 and wallets:
            w = wallets[0]
            new_bal = float(w["balance"]) + amount
            new_dep = float(w["total_deposited"]) + amount
            sb_patch("wallets", f"operator_id=eq.{operator_id}", {
                "balance": new_bal,
                "total_deposited": new_dep,
                "updated_at": "now()"
            })
        else:
            new_bal = amount
            sb_post("wallets", {
                "operator_id": operator_id,
                "balance": amount,
                "total_deposited": amount,
                "total_spent": 0
            })

        # Log transaction
        sb_post("transactions", {
            "operator_id": operator_id,
            "tx_type": "deposit",
            "amount": amount
        })

        self._json(200, {"status": "deposited", "new_balance": new_bal})

    def list_vendors(self, q, body):
        """Admin-only: list all merchant accounts."""
        if self.headers.get("X-Admin-Key") != ADMIN_KEY:
            self._json(401, {"error": "UNAUTHORIZED"})
            return
        status_filter = q.get("status", [""])[0]
        params = "select=id,username,display_name,jabber,status,balance,created_at&order=created_at.desc"
        if status_filter:
            params += f"&status=eq.{status_filter}"
        code, vendors = sb_get("merchants", params)
        if code == 200:
            self._json(200, {"vendors": vendors})
        else:
            self._json(500, {"error": str(vendors)})

    def approve_vendor(self, q, body):
        """Admin-only: approve or reject a vendor."""
        if self.headers.get("X-Admin-Key") != ADMIN_KEY:
            self._json(401, {"error": "UNAUTHORIZED"})
            return
        vendor_id = body.get("vendor_id", "")
        new_status = body.get("status", "active")  # active, suspended, banned
        if not vendor_id:
            self._json(400, {"error": "vendor_id required"})
            return
        code, result = sb_patch("merchants", f"id=eq.{vendor_id}", {"status": new_status})
        if code == 200:
            self._json(200, {"status": "updated", "vendor_id": vendor_id, "new_status": new_status})
        else:
            self._json(500, {"error": str(result)})

    # ═══════════════════════════════════════════
    # MERCHANT ENDPOINTS
    # ═══════════════════════════════════════════

    def merchant_register(self, q, body):
        """Register a new merchant account (pending approval)."""
        username = body.get("username", "").strip().lower()
        password = body.get("password", "")
        display_name = body.get("display_name", username)
        jabber = body.get("jabber", "")
        telegram = body.get("telegram", "")

        if not username or not password or len(password) < 6:
            self._json(400, {"error": "Username and password (6+ chars) required"})
            return

        # Check if username exists
        code, existing = sb_get("merchants", f"username=eq.{username}&select=id")
        if code == 200 and existing:
            self._json(409, {"error": "Username already taken"})
            return

        pw_hash, salt = hash_password(password)

        code, result = sb_post("merchants", {
            "username": username,
            "password_hash": pw_hash,
            "salt": salt,
            "display_name": display_name,
            "jabber": jabber or telegram,
            "status": "pending",
            "session_token": ""
        })

        if code in [200, 201]:
            self._json(200, {
                "status": "pending",
                "message": "Application submitted. Contact admin on Telegram for approval."
            })
        else:
            self._json(500, {"error": str(result)})

    def merchant_login(self, q, body):
        """Authenticate merchant and return session token."""
        username = body.get("username", "").strip().lower()
        password = body.get("password", "")

        if not username or not password:
            self._json(400, {"error": "Username and password required"})
            return

        code, merchants = sb_get("merchants", f"username=eq.{username}&select=*")
        if code != 200 or not merchants:
            self._json(401, {"error": "Invalid credentials"})
            return

        m = merchants[0]
        if m["status"] == "pending":
            self._json(403, {"error": "PENDING_APPROVAL: Your application is awaiting admin review. Contact @your_telegram for faster processing."})
            return
        if m["status"] != "active":
            self._json(403, {"error": "Account suspended or banned"})
            return

        if not verify_password(password, m["password_hash"], m["salt"]):
            self._json(401, {"error": "Invalid credentials"})
            return

        # Generate new session token
        token = secrets.token_hex(32)
        sb_patch("merchants", f"id=eq.{m['id']}", {"session_token": token})

        self._json(200, {
            "status": "authenticated",
            "token": token,
            "merchant_id": m["id"],
            "display_name": m["display_name"],
            "balance": float(m["balance"])
        })

    def _auth_merchant(self):
        """Validate merchant token from header. Returns merchant dict or None."""
        token = self.headers.get("X-Merchant-Token", "")
        if not token:
            return None
        code, merchants = sb_get("merchants", f"session_token=eq.{token}&status=eq.active&select=*")
        if code == 200 and merchants:
            return merchants[0]
        return None

    def merchant_bases(self, q, body):
        """List merchant's own bases with counts."""
        m = self._auth_merchant()
        if not m:
            self._json(401, {"error": "Invalid merchant token"})
            return

        code, bases = sb_get("bases", f"merchant_id=eq.{m['id']}&select=*&order=uploaded_at.desc")
        if code == 200:
            self._json(200, {"bases": bases})
        else:
            self._json(500, {"error": str(bases)})

    def merchant_stats(self, q, body):
        """Get merchant sales stats."""
        m = self._auth_merchant()
        if not m:
            self._json(401, {"error": "Invalid merchant token"})
            return

        # Total sold cards
        code, txs = sb_get("transactions", f"merchant_id=eq.{m['id']}&tx_type=eq.purchase&select=amount")
        total_sales = 0
        total_count = 0
        if code == 200:
            total_count = len(txs)
            total_sales = sum(float(t["amount"]) for t in txs)

        self._json(200, {
            "total_sales": total_sales,
            "total_sold": total_count,
            "balance": float(m["balance"]),
            "display_name": m["display_name"]
        })

    def merchant_balance(self, q, body):
        """Get merchant balance and recent transactions."""
        m = self._auth_merchant()
        if not m:
            self._json(401, {"error": "Invalid merchant token"})
            return

        code, txs = sb_get("transactions", f"merchant_id=eq.{m['id']}&select=*&order=created_at.desc&limit=50")
        self._json(200, {
            "balance": float(m["balance"]),
            "transactions": txs if code == 200 else []
        })

    def upload_base(self, q, body):
        """Upload a new base. Accepts bulk text or JSON array."""
        m = self._auth_merchant()
        if not m:
            self._json(401, {"error": "Invalid merchant token"})
            return

        name = body.get("name", "Unnamed Base")
        price = float(body.get("price", 5.00))
        raw_data = body.get("data", "")

        if not raw_data:
            self._json(400, {"error": "No card data provided"})
            return

        # Parse bulk text: NUMBER|MM|YY|CVV|HOLDER|ADDR|ZIP|CITY|ST|COUNTRY
        cards = []
        lines = raw_data.strip().split("\n")
        for line in lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 4:
                continue
            card = {
                "number": parts[0],
                "exp_month": parts[1],
                "exp_year": parts[2],
                "cvv": parts[3],
                "holder_name": parts[4] if len(parts) > 4 else "",
                "address": parts[5] if len(parts) > 5 else "",
                "zip": parts[6] if len(parts) > 6 else "",
                "city": parts[7] if len(parts) > 7 else "",
                "state": parts[8] if len(parts) > 8 else "",
                "country": parts[9] if len(parts) > 9 else "",
            }
            cards.append(card)

        if not cards:
            self._json(400, {"error": "No valid cards parsed from input"})
            return

        # Auto-detect BIN from first card
        first_bin = cards[0]["number"][:6] if cards[0]["number"] else ""

        # Create base record
        bcode, base_result = sb_post("bases", {
            "merchant_id": m["id"],
            "name": name,
            "bin": first_bin,
            "price_per_card": price,
            "quantity_total": len(cards),
            "quantity_available": len(cards),
            "status": "active"
        })

        if bcode not in [200, 201]:
            self._json(500, {"error": f"Failed to create base: {base_result}"})
            return

        base = base_result[0] if isinstance(base_result, list) else base_result
        base_id = base["id"]

        # Insert cards in batches of 50
        inserted = 0
        for i in range(0, len(cards), 50):
            batch = cards[i:i+50]
            for c in batch:
                c["base_id"] = base_id
                c["merchant_id"] = m["id"]
                c["status"] = "available"

            ccode, _ = sb_post("cards", batch)
            if ccode in [200, 201]:
                inserted += len(batch)

        self._json(200, {
            "status": "uploaded",
            "base_id": base_id,
            "base_name": name,
            "cards_inserted": inserted,
            "price_per_card": price
        })

    def update_base(self, q, body):
        """Update base pricing or status."""
        m = self._auth_merchant()
        if not m:
            self._json(401, {"error": "Invalid merchant token"})
            return

        base_id = body.get("base_id", "")
        if not base_id:
            self._json(400, {"error": "base_id required"})
            return

        updates = {}
        if "price" in body:
            updates["price_per_card"] = float(body["price"])
        if "status" in body:
            updates["status"] = body["status"]
        if "name" in body:
            updates["name"] = body["name"]

        if not updates:
            self._json(400, {"error": "No fields to update"})
            return

        code, result = sb_patch("bases", f"id=eq.{base_id}&merchant_id=eq.{m['id']}", updates)
        if code == 200:
            self._json(200, {"status": "updated", "base_id": base_id})
        else:
            self._json(500, {"error": str(result)})

    def delete_base_action(self, q, body):
        """Soft-delete a base (set status to deleted)."""
        m = self._auth_merchant()
        if not m:
            self._json(401, {"error": "Invalid merchant token"})
            return

        base_id = q.get("base_id", [""])[0] or body.get("base_id", "")
        if not base_id:
            self._json(400, {"error": "base_id required"})
            return

        code, result = sb_patch("bases", f"id=eq.{base_id}&merchant_id=eq.{m['id']}", {"status": "deleted"})
        if code == 200:
            self._json(200, {"status": "deleted", "base_id": base_id})
        else:
            self._json(500, {"error": str(result)})

    # ─── Response helper ───

    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
