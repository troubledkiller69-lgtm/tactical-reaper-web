import asyncio
import io
import logging
import os
import random
import re
import signal
import sys
import threading
import time as _time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import List, Dict, Union, Optional, Tuple, Any

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from telethon import TelegramClient, events, Button, errors as tg_errors
from eni_reper import EniReper, REPORT_TYPES
from history_manager import HistoryManager
from database import DatabaseManager
from dx_identifier import DXIdentifier
from email_flooder import launch_flood_stealth, launch_flood_multi
from ghost_sms import send_ghost_sms, send_ghost_sms_multi

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("eni_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# --- BOT CONFIG (from .env) ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

# --- VALIDATION ---
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_REGEX = re.compile(r'^\+?\d{7,15}$')
MAX_EMAIL_COUNT = 200
MAX_SMS_COUNT = 50


def validate_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))


def validate_phone(number: str) -> bool:
    return bool(PHONE_REGEX.match(number.replace("-", "").replace(" ", "")))


# ---------------------------------------------------------------------------
# PROGRESS REPORTER
# ---------------------------------------------------------------------------


class ProgressReporter:
    MIN_UPDATE_INTERVAL = 2.0

    def __init__(self, bot_client: TelegramClient, chat_id: int, operation_name: str) -> None:
        self.bot = bot_client
        self.chat_id = chat_id
        self.operation = operation_name
        self.message = None
        self.last_update = 0.0

    async def initialize(self) -> None:
        self.message = await self.bot.send_message(
            self.chat_id,
            f"**{self.operation}** -- Initializing...",
        )

    async def update(self, current: int, total: int, results: dict) -> None:
        now = _time.time()
        if now - self.last_update < self.MIN_UPDATE_INTERVAL:
            return
        self.last_update = now

        pct = (current / total * 100) if total > 0 else 0
        bar_len = 20
        filled = int(bar_len * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)

        success = results.get("success", 0)
        failed = results.get("failed", 0)

        text = (
            f"**{self.operation}**\n"
            f"`[{bar}]` {pct:.0f}%\n"
            f"Progress: {current}/{total}\n"
            f"Success: {success} | Failed: {failed}"
        )

        try:
            if self.message:
                await self.message.edit(text)
        except Exception:
            pass

    async def finalize(self, results: dict) -> None:
        success = results.get("success", 0)
        failed = results.get("failed", 0)
        total = results.get("total", success + failed)
        errors = results.get("errors", {})
        duration = results.get("duration_seconds", 0)

        text = (
            f"**{self.operation} -- Complete**\n\n"
            f"Total: {total}\n"
            f"Delivered: {success}\n"
            f"Failed: {failed}\n"
            f"Duration: {duration}s"
        )
        if errors:
            text += "\n\n**Error Breakdown:**"
            for err_type, count in errors.items():
                text += f"\n  - {err_type}: {count}"

        try:
            if self.message:
                await self.message.edit(text)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# MAIN BOT
# ---------------------------------------------------------------------------


class EniBot:
    COOLDOWN_SECONDS = {
        "email": 60,
        "ghost": 60,
        "report": 30,
        "join": 30,
        "flood_tg": 30,
        "dm": 30,
    }

    def __init__(self, token: str, api_id: int, api_hash: str) -> None:
        self.token = token
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot = TelegramClient('eni_bot_new', api_id, api_hash)
        self.reper = EniReper(api_id, api_hash)
        self.history = HistoryManager()
        self.db = DatabaseManager()
        self._dx_scanner = DXIdentifier()
        self._pending_reports: Dict[int, str] = {}
        self._cooldowns: Dict[Tuple[int, str], float] = {}
        self._active_ops: Dict[int, threading.Event] = {}
        self._active_async_ops: Dict[int, asyncio.Event] = {}
        self._account_wizard: Dict[int, dict] = {}
        self._scheduled: Dict[int, List[dict]] = {}
        self._schedule_counter = 0
        self._file_targets: Dict[int, List[str]] = {}
        self.menu = [
            [Button.text("🚀 Status", resize=True), Button.text("🎯 Report Target")],
            [Button.text("📡 Telegram Botting"), Button.text("📧 Email Flood")],
            [Button.text("📱 Ghost SMS"), Button.text("🛡 Session Health")],
            [Button.text("📜 History"), Button.text("🔍 DX Scanner")],
            [Button.text("ℹ Help")],
        ]

    async def _export_results(self, chat_id: int, operation: str, results: dict) -> None:
        lines = [
            f"=== {operation} ===",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Total: {results.get('total', 0)}",
            f"Success: {results.get('success', 0)}",
            f"Failed: {results.get('failed', 0)}",
            f"Duration: {results.get('duration_seconds', 0)}s",
        ]

        if results.get("carriers_used"):
            lines.append(f"\nCarriers Used: {', '.join(results['carriers_used'])}")

        if results.get("carrier_stats"):
            lines.append("\nCarrier Stats:")
            for gw, st in results["carrier_stats"].items():
                lines.append(f"  {gw}: {st['success']}ok / {st['failed']}fail ({st['rate']}%)")

        if results.get("errors"):
            lines.append("\nError Breakdown:")
            for err, count in results["errors"].items():
                lines.append(f"  {err}: {count}")

        if results.get("per_target"):
            lines.append("\nPer-Target:")
            for target, tr in results["per_target"].items():
                lines.append(f"  {target}: {tr.get('success', 0)}/{tr.get('total', 0)}")

        if results.get("joined"):
            lines.append(f"\nChannels Joined: {results['joined']}")

        content = "\n".join(lines)
        filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        try:
            import io
            file_bytes = io.BytesIO(content.encode("utf-8"))
            file_bytes.name = filename
            await self.bot.send_file(chat_id, file_bytes, caption=f"📊 {operation} results exported")
        except Exception as e:
            logger.warning("Failed to export results: %s", e)
            await self.bot.send_message(chat_id, f"📊 Export failed: {e}")

    def _check_cooldown(self, user_id: int, action: str) -> Optional[int]:
        key = (user_id, action)
        last_used = self._cooldowns.get(key, 0)
        cooldown = self.COOLDOWN_SECONDS.get(action, 30)
        elapsed = _time.time() - last_used
        if elapsed < cooldown:
            return int(cooldown - elapsed)
        return None

    def _set_cooldown(self, user_id: int, action: str) -> None:
        self._cooldowns[(user_id, action)] = _time.time()

    async def check_auth(self, event) -> bool:
        is_active, expiry = self.db.check_license(event.sender_id)
        if not is_active:
            await event.respond(
                "🚫 **Access Denied**. Please redeem a key.",
                buttons=[[Button.text("🔑 Redeem Key")]],
            )
            return False
        return True

    # -------------------------------------------------------------------
    # SCHEDULED COMMAND EXECUTOR
    # -------------------------------------------------------------------

    async def _execute_scheduled(self, chat_id: int, sender_id: int, command_text: str) -> None:
        parts = command_text.strip().split(maxsplit=2)
        cmd = parts[0].lower() if parts else ""

        try:
            if cmd == "/email" and len(parts) >= 3:
                targets = [t.strip() for t in parts[1].split(",")]
                count = int(parts[2])
                reporter = ProgressReporter(self.bot, chat_id, f"⏰ Scheduled Email -> {parts[1]}")
                await reporter.initialize()
                cancel_event = threading.Event()
                self._active_ops[chat_id] = cancel_event
                try:
                    loop = asyncio.get_event_loop()
                    if len(targets) > 1:
                        results = await loop.run_in_executor(None, launch_flood_multi, targets, count, 5, None, cancel_event)
                    else:
                        results = await loop.run_in_executor(None, launch_flood_stealth, targets[0], count, 5, None, cancel_event)
                    await reporter.finalize(results)
                finally:
                    self._active_ops.pop(chat_id, None)

            elif cmd == "/ghost" and len(parts) >= 3:
                numbers = [n.strip() for n in parts[1].split(",")]
                count = int(parts[2])
                reporter = ProgressReporter(self.bot, chat_id, f"⏰ Scheduled Ghost SMS -> {parts[1]}")
                await reporter.initialize()
                cancel_event = threading.Event()
                self._active_ops[chat_id] = cancel_event
                try:
                    loop = asyncio.get_event_loop()
                    if len(numbers) > 1:
                        results = await loop.run_in_executor(None, send_ghost_sms_multi, numbers, count, None, cancel_event)
                    else:
                        results = await loop.run_in_executor(None, send_ghost_sms, numbers[0], count, None, cancel_event)
                    await reporter.finalize(results)
                finally:
                    self._active_ops.pop(chat_id, None)

            elif cmd == "/report" and len(parts) >= 2:
                target = parts[1]
                reason = parts[2] if len(parts) > 2 else "spam"
                reporter = ProgressReporter(self.bot, chat_id, f"⏰ Scheduled Report -> {target}")
                await reporter.initialize()
                await self.reper.load_accounts()
                results = await self.reper.report_target(target, reason, progress_callback=reporter.update)
                await reporter.finalize(results)

            elif cmd == "/flood_tg" and len(parts) >= 3:
                target = parts[1]
                msg = parts[2]
                reporter = ProgressReporter(self.bot, chat_id, f"⏰ Scheduled Spam -> {target}")
                await reporter.initialize()
                await self.reper.load_accounts()
                results = await self.reper.spam_target(target, msg, progress_callback=reporter.update)
                await reporter.finalize(results)

            else:
                await self.bot.send_message(chat_id, f"❌ Unrecognized scheduled command: `{command_text}`")

        except Exception as e:
            logger.exception("Scheduled command failed: %s", command_text)
            await self.bot.send_message(chat_id, f"❌ Scheduled `{cmd}` failed: {e}")

    async def start(self) -> None:
        self._register_handlers()
        
        # Start the bot
        await self.bot.start(bot_token=self.token)
        logger.info("Tactical Master is online.")

        # Load accounts in background to not block events
        asyncio.create_task(self.reper.load_accounts())

        await self.bot.run_until_disconnected()

    def _register_handlers(self) -> None:
        logger.info("Registering bot handlers...")
        
        @self.bot.on(events.NewMessage())
        async def debug_handler(event):
            logger.info("MSG: [%s] %s", event.sender_id, event.message.text)

        # -------------------------------------------------------------------
        # HANDLER: Account wizard (must be first to intercept wizard inputs)
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage())
        async def wizard_handler(event):
            wizard = self._account_wizard.get(event.sender_id)
            if not wizard:
                return

            text = (event.message.text or "").strip()

            if text.startswith("/"):
                del self._account_wizard[event.sender_id]
                if "client" in wizard:
                    try:
                        await wizard["client"].disconnect()
                    except Exception:
                        pass
                await event.respond("❌ Account wizard cancelled.")
                return

            if wizard["step"] == "phone":
                phone = text
                try:
                    client = TelegramClient(
                        os.path.join("sessions", wizard["name"]),
                        self.api_id, self.api_hash,
                    )
                    await client.connect()
                    await client.send_code_request(phone)
                    wizard["client"] = client
                    wizard["phone"] = phone
                    wizard["step"] = "code"
                    await event.respond("📱 Code sent! Enter the verification code:")
                except Exception as e:
                    await event.respond(f"❌ Failed to send code: {e}")
                    del self._account_wizard[event.sender_id]
                raise events.StopPropagation

            elif wizard["step"] == "code":
                code = text.replace(" ", "").replace("-", "")
                client = wizard["client"]
                try:
                    await client.sign_in(wizard["phone"], code)
                    await event.respond(f"✅ Account **{wizard['name']}** added successfully!")
                    await client.disconnect()
                    del self._account_wizard[event.sender_id]
                    await self.reper.load_accounts(force=True)
                except tg_errors.SessionPasswordNeededError:
                    wizard["step"] = "2fa"
                    await event.respond("🔐 2FA enabled. Enter your password:")
                except Exception as e:
                    await event.respond(f"❌ Sign-in failed: {e}")
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                    del self._account_wizard[event.sender_id]
                raise events.StopPropagation

            elif wizard["step"] == "2fa":
                password = text
                client = wizard["client"]
                try:
                    await client.sign_in(password=password)
                    await event.respond(f"✅ Account **{wizard['name']}** added with 2FA!")
                    await client.disconnect()
                    del self._account_wizard[event.sender_id]
                    await self.reper.load_accounts(force=True)
                except Exception as e:
                    await event.respond(f"❌ 2FA failed: {e}")
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                    del self._account_wizard[event.sender_id]
                raise events.StopPropagation

        # -------------------------------------------------------------------
        # HANDLER: /start
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            if await self.check_auth(event):
                await event.respond(
                    "Welcome back, Commander. Your Tactical Arsenal is online.",
                    buttons=self.menu,
                )

        # -------------------------------------------------------------------
        # HANDLER: Redeem Key
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='🔑 Redeem Key'))
        async def redeem_prompt(event):
            await event.respond("Usage: `/redeem Retri-XXXX-XXXX`")

        @self.bot.on(events.NewMessage(pattern=r'/redeem(\s+.*)?'))
        async def redeem_handler(event):
            args = event.message.text.strip().split()
            if len(args) < 2:
                await event.respond("Usage: `/redeem Retri-XXXX-XXXX`")
                return

            key = args[1]
            success, expiry = self.db.redeem_key(event.sender_id, key)
            if success:
                await event.respond(
                    f"✅ **License Activated!**\nExpiry: `{expiry}`",
                    buttons=self.menu,
                )
            else:
                await event.respond(f"❌ **Failed**: {expiry}")

        # -------------------------------------------------------------------
        # HANDLER: 🚀 Status
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='🚀 Status'))
        async def status_handler(event):
            is_active, expiry = self.db.check_license(event.sender_id)
            active_keys, active_users = self.db.get_stats()
            has_op = event.chat_id in self._active_ops or event.chat_id in self._active_async_ops

            scheduled_count = len(self._scheduled.get(event.chat_id, []))

            text = (
                "🚀 **System Status**\n\n"
                f"License: {'🟢 Active' if is_active else '🔴 Expired/None'}\n"
                f"Expiry: `{expiry or 'N/A'}`\n"
                f"Active keys in system: {active_keys}\n"
                f"Total users: {active_users}\n"
                f"Active operation: {'Yes' if has_op else 'No'}\n"
                f"Scheduled operations: {scheduled_count}"
            )
            await event.respond(text)

        # -------------------------------------------------------------------
        # HANDLER: 🎯 Report Target
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='🎯 Report Target'))
        async def report_prompt(event):
            if not await self.check_auth(event):
                return
            reason_buttons = [
                [Button.inline(reason.replace("_", " ").title(), f"rr:{reason}".encode())]
                for reason in REPORT_TYPES
            ]
            reason_buttons.append([Button.inline("🥷 Stealth Mode", b"rr:stealth")])
            reason_buttons.append([Button.inline("Back to Menu", b"back")])
            await event.respond(
                "Select report reason:\n\n"
                "**Stealth Mode**: Joins target, browses messages, then reports (harder to detect)",
                buttons=reason_buttons,
            )

        @self.bot.on(events.NewMessage(pattern=r'/report(\s+.*)?'))
        async def report_handler(event):
            if not await self.check_auth(event):
                return

            remaining = self._check_cooldown(event.sender_id, "report")
            if remaining:
                await event.respond(f"⏳ Cooldown active. Try again in {remaining}s.")
                return

            args = event.message.text.strip().split()
            if len(args) < 2:
                await event.respond("Usage: `/report <target_url>`\nPick a reason from 🎯 Report Target first.")
                return

            target = args[1]
            reason = self._pending_reports.pop(event.sender_id, "spam")
            stealth = reason == "stealth"
            if stealth:
                reason = "spam"

            label = f"{'Stealth ' if stealth else ''}Report -> {target}"
            reporter = ProgressReporter(self.bot, event.chat_id, label)
            await reporter.initialize()

            cancel_event = asyncio.Event()
            self._active_async_ops[event.chat_id] = cancel_event

            try:
                await self.reper.load_accounts()
                if stealth:
                    results = await self.reper.stealth_report_target(
                        target, reason,
                        progress_callback=reporter.update,
                    )
                else:
                    results = await self.reper.report_target(
                        target, reason,
                        progress_callback=reporter.update,
                    )
                mode = "stealth" if stealth else reason
                self.history.add_to_past(target, f"report ({mode}): {results['success']} sent")
                await reporter.finalize(results)
                if results.get("total", 0) >= 5:
                    await self._export_results(event.chat_id, label, results)
                self._set_cooldown(event.sender_id, "report")
            except Exception as e:
                logger.exception("Report operation failed")
                await event.respond(f"❌ **Report Failed**: {e}")
            finally:
                self._active_async_ops.pop(event.chat_id, None)

        # -------------------------------------------------------------------
        # HANDLER: 📡 Telegram Botting
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='📡 Telegram Botting'))
        async def botting_menu(event):
            if not await self.check_auth(event):
                return
            buttons = [
                [Button.inline("Join Channel", b"join"), Button.inline("Spam Target", b"spam")],
                [Button.inline("DM Spam", b"dm"), Button.inline("Back to Menu", b"back")],
            ]
            await event.respond("Select Telegram operation:", buttons=buttons)

        # -------------------------------------------------------------------
        # HANDLER: Callback queries
        # -------------------------------------------------------------------
        @self.bot.on(events.CallbackQuery())
        async def callback_handler(event):
            data = event.data
            if data == b"back":
                await event.edit("Returning to main menu...", buttons=self.menu)
            elif data == b"join":
                await event.respond("Usage: `/join <channel_url>`")
            elif data == b"spam":
                await event.respond("Usage: `/flood_tg <target> <message>`")
            elif data == b"dm":
                await event.respond("Usage: `/dm <user1,user2,...> <message>`")
            elif data.startswith(b"rr:"):
                reason = data.decode().split(":", 1)[1]
                self._pending_reports[event.sender_id] = reason
                await event.respond(
                    f"Reason: **{reason.replace('_', ' ').title()}**\n"
                    f"Now send: `/report <target_url>`"
                )
            elif data.startswith(b"ft:"):
                action = data.decode().split(":", 1)[1]
                targets = self._file_targets.get(event.sender_id, [])
                if not targets:
                    await event.respond("❌ No uploaded targets found. Upload a .txt file first.")
                    return

                if action == "email":
                    count = min(50, MAX_EMAIL_COUNT)
                    await event.respond(
                        f"📧 {len(targets)} targets loaded.\n"
                        f"Send: `/email {','.join(targets[:5])}{',...' if len(targets) > 5 else ''} {count}`\n\n"
                        f"Or use the full target list automatically:"
                    )
                    reporter = ProgressReporter(self.bot, event.chat_id, f"File Email -> {len(targets)} targets")
                    await reporter.initialize()
                    cancel_event = threading.Event()
                    self._active_ops[event.chat_id] = cancel_event
                    try:
                        loop = asyncio.get_event_loop()
                        results = await loop.run_in_executor(
                            None, launch_flood_multi, targets, count, 5, None, cancel_event,
                        )
                        await reporter.finalize(results)
                        await self._export_results(event.chat_id, f"Email Flood ({len(targets)} targets)", results)
                        self.history.add_to_past(f"file x{len(targets)}", f"email: {results['success']}/{results['total']}")
                    except Exception as e:
                        await event.respond(f"❌ {e}")
                    finally:
                        self._active_ops.pop(event.chat_id, None)

                elif action == "sms":
                    count = min(10, MAX_SMS_COUNT)
                    reporter = ProgressReporter(self.bot, event.chat_id, f"File SMS -> {len(targets)} targets")
                    await reporter.initialize()
                    cancel_event = threading.Event()
                    self._active_ops[event.chat_id] = cancel_event
                    try:
                        loop = asyncio.get_event_loop()
                        results = await loop.run_in_executor(
                            None, send_ghost_sms_multi, targets, count, None, cancel_event,
                        )
                        await reporter.finalize(results)
                        await self._export_results(event.chat_id, f"Ghost SMS ({len(targets)} targets)", results)
                        self.history.add_to_past(f"file x{len(targets)}", f"sms: {results['success']}/{results['total']}")
                    except Exception as e:
                        await event.respond(f"❌ {e}")
                    finally:
                        self._active_ops.pop(event.chat_id, None)

                elif action == "dm":
                    await event.respond(
                        f"👤 {len(targets)} usernames loaded.\n"
                        f"Send: `/dm {','.join(targets[:5])}{',...' if len(targets) > 5 else ''} <message>`"
                    )

        # -------------------------------------------------------------------
        # HANDLER: File upload (target list)
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(func=lambda e: e.document is not None))
        async def file_upload_handler(event):
            if not await self.check_auth(event):
                return

            doc = event.document
            if not doc:
                return

            for attr in doc.attributes:
                if hasattr(attr, "file_name") and attr.file_name and attr.file_name.endswith(".txt"):
                    break
            else:
                return

            try:
                data = await event.download_media(bytes)
                text = data.decode("utf-8", errors="ignore")
                lines = [line.strip() for line in text.splitlines() if line.strip()]

                if not lines:
                    await event.respond("❌ Empty file. Upload a .txt with one target per line.")
                    return

                self._file_targets[event.sender_id] = lines

                buttons = [
                    [Button.inline(f"📧 Email Flood ({len(lines)})", b"ft:email")],
                    [Button.inline(f"📱 Ghost SMS ({len(lines)})", b"ft:sms")],
                    [Button.inline(f"👤 DM Spam ({len(lines)})", b"ft:dm")],
                ]

                preview = "\n".join(f"  {l}" for l in lines[:5])
                if len(lines) > 5:
                    preview += f"\n  ... +{len(lines) - 5} more"

                await event.respond(
                    f"📂 **Loaded {len(lines)} targets:**\n```\n{preview}\n```\n\n"
                    f"Pick an operation:",
                    buttons=buttons,
                )
            except Exception as e:
                logger.exception("File upload processing failed")
                await event.respond(f"❌ Failed to process file: {e}")

        # -------------------------------------------------------------------
        # HANDLER: /join
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='/join'))
        async def join_handler(event):
            if not await self.check_auth(event):
                return

            remaining = self._check_cooldown(event.sender_id, "join")
            if remaining:
                await event.respond(f"⏳ Cooldown active. Try again in {remaining}s.")
                return

            args = event.message.text.split()
            if len(args) < 2:
                await event.respond("Usage: `/join <channel_url>`")
                return

            reporter = ProgressReporter(self.bot, event.chat_id, f"Mass Join -> {args[1]}")
            await reporter.initialize()

            try:
                await self.reper.load_accounts()
                results = await self.reper.join_target(
                    args[1],
                    progress_callback=reporter.update,
                )
                self.history.add_to_past(args[1], f"join: {results['success']} joined")
                await reporter.finalize(results)
                self._set_cooldown(event.sender_id, "join")
            except Exception as e:
                logger.exception("Join operation failed")
                await event.respond(f"❌ **Join Failed**: {e}")

        # -------------------------------------------------------------------
        # HANDLER: /flood_tg
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='/flood_tg'))
        async def flood_tg_handler(event):
            if not await self.check_auth(event):
                return

            remaining = self._check_cooldown(event.sender_id, "flood_tg")
            if remaining:
                await event.respond(f"⏳ Cooldown active. Try again in {remaining}s.")
                return

            args = event.message.text.split(maxsplit=2)
            if len(args) < 3:
                await event.respond("Usage: `/flood_tg <target> <message>`")
                return

            reporter = ProgressReporter(self.bot, event.chat_id, f"Mass Spam -> {args[1]}")
            await reporter.initialize()

            try:
                await self.reper.load_accounts()
                results = await self.reper.spam_target(
                    args[1], args[2],
                    progress_callback=reporter.update,
                )
                self.history.add_to_past(args[1], f"spam: {results['success']} sent")
                await reporter.finalize(results)
                self._set_cooldown(event.sender_id, "flood_tg")
            except Exception as e:
                logger.exception("Spam operation failed")
                await event.respond(f"❌ **Spam Failed**: {e}")

        # -------------------------------------------------------------------
        # HANDLER: /dm
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern=r'/dm(\s+.*)?'))
        async def dm_handler(event):
            if not await self.check_auth(event):
                return

            remaining = self._check_cooldown(event.sender_id, "dm")
            if remaining:
                await event.respond(f"⏳ Cooldown active. Try again in {remaining}s.")
                return

            args = event.message.text.split(maxsplit=2)
            if len(args) < 3:
                await event.respond("Usage: `/dm <user1,user2,...> <message>`")
                return

            targets = [t.strip().lstrip("@") for t in args[1].split(",") if t.strip()]
            message = args[2]

            if not targets:
                await event.respond("❌ No valid usernames provided.")
                return

            reporter = ProgressReporter(self.bot, event.chat_id, f"DM Spam -> {len(targets)} users")
            await reporter.initialize()

            cancel_event = asyncio.Event()
            self._active_async_ops[event.chat_id] = cancel_event

            try:
                await self.reper.load_accounts()
                results = await self.reper.dm_spam(
                    targets, message,
                    progress_callback=reporter.update,
                )
                self.history.add_to_past(f"DM x{len(targets)}", f"dm: {results['success']} sent")
                await reporter.finalize(results)
                self._set_cooldown(event.sender_id, "dm")
            except Exception as e:
                logger.exception("DM spam failed")
                await event.respond(f"❌ **DM Spam Failed**: {e}")
            finally:
                self._active_async_ops.pop(event.chat_id, None)

        # -------------------------------------------------------------------
        # HANDLER: /scrape
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern=r'/scrape(\s+.*)?'))
        async def scrape_handler(event):
            if not await self.check_auth(event):
                return

            args = event.message.text.strip().split()
            if len(args) < 2:
                await event.respond(
                    "Usage: `/scrape <channel_or_group> [limit]`\n\n"
                    "Scrapes usernames from a channel/group.\n"
                    "Default limit: 200\n\n"
                    "Example: `/scrape @somechannel 100`"
                )
                return

            target = args[1]
            limit = 200
            if len(args) >= 3:
                try:
                    limit = min(int(args[2]), 1000)
                except ValueError:
                    await event.respond("❌ Limit must be a number.")
                    return

            await event.respond(f"🔍 Scraping users from `{target}` (limit: {limit})...")

            try:
                await self.reper.load_accounts()
                usernames = await self.reper.scrape_users(target, limit=limit)

                if not usernames:
                    await event.respond("❌ No users found (channel may require admin access).")
                    return

                chunks = []
                for i in range(0, len(usernames), 50):
                    batch = usernames[i:i+50]
                    chunks.append(", ".join(f"@{u}" for u in batch))

                header = f"🔍 **Scraped {len(usernames)} users from {target}:**\n\n"
                await event.respond(header + chunks[0])
                for chunk in chunks[1:]:
                    await event.respond(chunk)

                csv_list = ",".join(usernames)
                await event.respond(
                    f"\n**Quick Actions:**\n"
                    f"`/dm {csv_list[:200]}{'...' if len(csv_list) > 200 else ''} <message>`\n\n"
                    f"Total: {len(usernames)} usernames ready for DM."
                )

                self.history.add_to_past(target, f"scrape: {len(usernames)} users")

            except Exception as e:
                logger.exception("Scrape failed")
                await event.respond(f"❌ **Scrape Failed**: {e}")

        # -------------------------------------------------------------------
        # HANDLER: /campaign
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern=r'/campaign(\s+.*)?'))
        async def campaign_handler(event):
            if not await self.check_auth(event):
                return

            args = event.message.text.strip().split(maxsplit=1)
            if len(args) < 2:
                await event.respond(
                    "🎯 **Campaign Mode** -- Chain multiple vectors\n\n"
                    "Usage: `/campaign <step1> <step2> ...`\n\n"
                    "Step formats:\n"
                    "  `email:<address>:<count>`\n"
                    "  `sms:<number>:<count>`\n"
                    "  `report:<target>:<reason>`\n"
                    "  `join:<channel>`\n"
                    "  `spam:<target>:<message>`\n"
                    "  `dm:<user1,user2>:<message>`\n"
                    "  `scrape:<channel>:<limit>`\n\n"
                    "Example:\n"
                    "`/campaign email:vic@mail.com:50 sms:5551234:20 report:@target:spam`"
                )
                return

            steps_raw = args[1].split()
            steps = []
            for step_raw in steps_raw:
                parts = step_raw.split(":", 2)
                if len(parts) < 2:
                    await event.respond(f"❌ Invalid step: `{step_raw}` (use type:arg1:arg2)")
                    return
                steps.append({
                    "type": parts[0].lower(),
                    "arg1": parts[1] if len(parts) > 1 else "",
                    "arg2": parts[2] if len(parts) > 2 else "",
                })

            await event.respond(
                f"🎯 **Campaign Initiated** -- {len(steps)} vectors queued\n"
                + "\n".join(f"  {i+1}. {s['type'].upper()}: {s['arg1']}" for i, s in enumerate(steps))
            )

            cancel_event_sync = threading.Event()
            cancel_event_async = asyncio.Event()
            self._active_ops[event.chat_id] = cancel_event_sync
            self._active_async_ops[event.chat_id] = cancel_event_async

            campaign_results = []

            try:
                for i, step in enumerate(steps):
                    if cancel_event_sync.is_set() or cancel_event_async.is_set():
                        await event.respond(f"⏹ Campaign cancelled at step {i+1}/{len(steps)}")
                        break

                    stype = step["type"]
                    arg1 = step["arg1"]
                    arg2 = step["arg2"]

                    reporter = ProgressReporter(
                        self.bot, event.chat_id,
                        f"Campaign [{i+1}/{len(steps)}] {stype.upper()}"
                    )
                    await reporter.initialize()

                    try:
                        if stype == "email":
                            targets = [t.strip() for t in arg1.split(",")]
                            count = int(arg2) if arg2 else 50
                            loop = asyncio.get_event_loop()
                            if len(targets) > 1:
                                result = await loop.run_in_executor(
                                    None, launch_flood_multi, targets, count, 5, None, cancel_event_sync,
                                )
                            else:
                                result = await loop.run_in_executor(
                                    None, launch_flood_stealth, targets[0], count, 5, None, cancel_event_sync,
                                )
                            await reporter.finalize(result)
                            campaign_results.append({"step": stype, "result": result})

                        elif stype == "sms":
                            numbers = [n.strip() for n in arg1.split(",")]
                            count = int(arg2) if arg2 else 20
                            loop = asyncio.get_event_loop()
                            if len(numbers) > 1:
                                result = await loop.run_in_executor(
                                    None, send_ghost_sms_multi, numbers, count, None, cancel_event_sync,
                                )
                            else:
                                result = await loop.run_in_executor(
                                    None, send_ghost_sms, numbers[0], count, None, cancel_event_sync,
                                )
                            await reporter.finalize(result)
                            campaign_results.append({"step": stype, "result": result})

                        elif stype == "report":
                            reason = arg2 if arg2 else "spam"
                            await self.reper.load_accounts()
                            result = await self.reper.report_target(
                                arg1, reason, progress_callback=reporter.update,
                            )
                            await reporter.finalize(result)
                            campaign_results.append({"step": stype, "result": result})

                        elif stype == "join":
                            await self.reper.load_accounts()
                            result = await self.reper.join_target(
                                arg1, progress_callback=reporter.update,
                            )
                            await reporter.finalize(result)
                            campaign_results.append({"step": stype, "result": result})

                        elif stype == "spam":
                            msg = arg2 if arg2 else "."
                            await self.reper.load_accounts()
                            result = await self.reper.spam_target(
                                arg1, msg, progress_callback=reporter.update,
                            )
                            await reporter.finalize(result)
                            campaign_results.append({"step": stype, "result": result})

                        elif stype == "dm":
                            user_targets = [t.strip().lstrip("@") for t in arg1.split(",")]
                            msg = arg2 if arg2 else "."
                            await self.reper.load_accounts()
                            result = await self.reper.dm_spam(
                                user_targets, msg, progress_callback=reporter.update,
                            )
                            await reporter.finalize(result)
                            campaign_results.append({"step": stype, "result": result})

                        elif stype == "scrape":
                            limit = int(arg2) if arg2 else 200
                            await self.reper.load_accounts()
                            usernames = await self.reper.scrape_users(arg1, limit=limit)
                            await reporter.finalize({"total": limit, "success": len(usernames), "failed": 0})
                            campaign_results.append({"step": stype, "result": {"scraped": len(usernames), "usernames": usernames}})

                        else:
                            await event.respond(f"⚠️ Unknown step type: `{stype}` -- skipping")

                    except Exception as e:
                        logger.exception("Campaign step %d failed: %s", i+1, e)
                        await event.respond(f"⚠️ Step {i+1} ({stype}) failed: {e}")

                    await asyncio.sleep(random.uniform(2.0, 5.0))

                summary_lines = ["🎯 **Campaign Complete**\n"]
                total_success = 0
                total_failed = 0
                for cr in campaign_results:
                    r = cr["result"]
                    s = r.get("success", r.get("scraped", 0))
                    f = r.get("failed", 0)
                    total_success += s
                    total_failed += f
                    summary_lines.append(f"  {cr['step'].upper()}: {s} success / {f} failed")
                summary_lines.append(f"\n**Totals: {total_success} success / {total_failed} failed**")

                await event.respond("\n".join(summary_lines))
                self.history.add_to_past(f"campaign x{len(steps)}", f"campaign: {total_success} success")

            finally:
                self._active_ops.pop(event.chat_id, None)
                self._active_async_ops.pop(event.chat_id, None)

        # -------------------------------------------------------------------
        # HANDLER: 📧 Email Flood (with multi-target)
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='📧 Email Flood'))
        async def email_prompt(event):
            await event.respond(
                "Usage: `/email <address> <count>`\n"
                "Multi-target: `/email addr1,addr2,addr3 <count>`"
            )

        @self.bot.on(events.NewMessage(pattern=r'/email(\s+.*)?'))
        async def email_handler(event):
            if not await self.check_auth(event):
                return

            remaining = self._check_cooldown(event.sender_id, "email")
            if remaining:
                await event.respond(f"⏳ Cooldown active. Try again in {remaining}s.")
                return

            args = event.message.text.strip().split()
            if len(args) < 3:
                await event.respond("Usage: `/email <address> <count>`\nMulti: `/email a@b.com,c@d.com <count>`")
                return

            targets = [t.strip() for t in args[1].split(",")]
            for t in targets:
                if not validate_email(t):
                    await event.respond(f"❌ Invalid email: `{t}`")
                    return

            try:
                count = int(args[2])
            except ValueError:
                await event.respond("❌ Count must be a number.")
                return

            if count < 1 or count > MAX_EMAIL_COUNT:
                await event.respond(f"❌ Count must be between 1 and {MAX_EMAIL_COUNT}.")
                return

            label = args[1] if len(targets) == 1 else f"{len(targets)} targets"
            reporter = ProgressReporter(self.bot, event.chat_id, f"Email Flood -> {label}")
            await reporter.initialize()

            cancel_event = threading.Event()
            self._active_ops[event.chat_id] = cancel_event

            def sync_progress(current, total, last_result):
                try:
                    asyncio.run_coroutine_threadsafe(
                        reporter.update(current, total, {"success": current}),
                        self.bot.loop,
                    )
                except Exception:
                    pass

            try:
                loop = asyncio.get_event_loop()
                if len(targets) > 1:
                    results = await loop.run_in_executor(
                        None, launch_flood_multi, targets, count, 5, sync_progress, cancel_event,
                    )
                else:
                    results = await loop.run_in_executor(
                        None, launch_flood_stealth, targets[0], count, 5, sync_progress, cancel_event,
                    )
                self.history.add_to_past(args[1], f"email: {results['success']}/{results['total']}")
                await reporter.finalize(results)
                if results.get("total", 0) >= 20:
                    await self._export_results(event.chat_id, f"Email Flood -> {label}", results)
                self._set_cooldown(event.sender_id, "email")
            except Exception as e:
                logger.exception("Email flood failed")
                await event.respond(f"❌ **Email Flood Failed**: {e}")
            finally:
                self._active_ops.pop(event.chat_id, None)

        # -------------------------------------------------------------------
        # HANDLER: 📱 Ghost SMS (with multi-target)
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='📱 Ghost SMS'))
        async def ghost_prompt(event):
            await event.respond(
                "Usage: `/ghost <number> <count>`\n"
                "Multi-target: `/ghost num1,num2,num3 <count>`"
            )

        @self.bot.on(events.NewMessage(pattern=r'/ghost(\s+.*)?'))
        async def ghost_handler(event):
            if not await self.check_auth(event):
                return

            remaining = self._check_cooldown(event.sender_id, "ghost")
            if remaining:
                await event.respond(f"⏳ Cooldown active. Try again in {remaining}s.")
                return

            args = event.message.text.strip().split()
            if len(args) < 3:
                await event.respond("Usage: `/ghost <number> <count>`\nMulti: `/ghost 5551234567,5559876543 <count>`")
                return

            numbers = [n.strip() for n in args[1].split(",")]
            for n in numbers:
                if not validate_phone(n):
                    await event.respond(f"❌ Invalid phone number: `{n}`")
                    return

            try:
                count = int(args[2])
            except ValueError:
                await event.respond("❌ Count must be a number.")
                return

            if count < 1 or count > MAX_SMS_COUNT:
                await event.respond(f"❌ Count must be between 1 and {MAX_SMS_COUNT}.")
                return

            label = args[1] if len(numbers) == 1 else f"{len(numbers)} targets"
            reporter = ProgressReporter(self.bot, event.chat_id, f"Ghost SMS -> {label}")
            await reporter.initialize()

            cancel_event = threading.Event()
            self._active_ops[event.chat_id] = cancel_event

            def sync_progress(current, total, last_result):
                try:
                    asyncio.run_coroutine_threadsafe(
                        reporter.update(current, total, {"success": current}),
                        self.bot.loop,
                    )
                except Exception:
                    pass

            try:
                loop = asyncio.get_event_loop()
                if len(numbers) > 1:
                    results = await loop.run_in_executor(
                        None, send_ghost_sms_multi, numbers, count, sync_progress, cancel_event,
                    )
                else:
                    results = await loop.run_in_executor(
                        None, send_ghost_sms, numbers[0], count, sync_progress, cancel_event,
                    )
                self.history.add_to_past(args[1], f"sms: {results['success']}/{results['total']}")
                await reporter.finalize(results)
                if results.get("total", 0) >= 10:
                    await self._export_results(event.chat_id, f"Ghost SMS -> {label}", results)
                self._set_cooldown(event.sender_id, "ghost")
            except Exception as e:
                logger.exception("Ghost SMS failed")
                await event.respond(f"❌ **Ghost SMS Failed**: {e}")
            finally:
                self._active_ops.pop(event.chat_id, None)

        # -------------------------------------------------------------------
        # HANDLER: 🛡 Session Health
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='🛡 Session Health'))
        async def health_handler(event):
            if not await self.check_auth(event):
                return

            await event.respond("🔍 Checking session health...")
            try:
                count = await self.reper.load_accounts(force=True)
                report = self.reper.get_health_report()

                lines = [
                    f"🛡 **Session Health Report**\n",
                    f"Total accounts loaded: **{count}**",
                    f"Status: {'🟢 Ready' if count > 0 else '🔴 No accounts loaded'}\n",
                ]

                if report:
                    for acct in report:
                        icon = "🟢" if acct["healthy"] else "🔴"
                        line = f"{icon} `{acct['name']}` | actions: {acct['actions']} | errors: {acct['errors']}"
                        if acct["banned"]:
                            line += " | **BANNED**"
                        elif acct["cooldown_remaining"] > 0:
                            line += f" | cooldown: {acct['cooldown_remaining']}s"
                        lines.append(line)

                await event.respond("\n".join(lines))
            except Exception as e:
                logger.exception("Health check failed")
                await event.respond(f"❌ **Health check failed**: {e}")

        # -------------------------------------------------------------------
        # HANDLER: 📜 History
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='📜 History'))
        async def history_handler(event):
            if not await self.check_auth(event):
                return
            entries = self.history.get_past(limit=10)
            if not entries:
                await event.respond("📜 No operation history found.")
                return
            lines = ["📜 **Operation History** (last 10):\n"]
            for i, entry in enumerate(reversed(entries), 1):
                lines.append(
                    f"{i}. `{entry['target']}` | {entry['reason']} | {entry['timestamp']}"
                )
            await event.respond("\n".join(lines))

        # -------------------------------------------------------------------
        # HANDLER: ℹ Help
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='ℹ Help'))
        async def help_handler(event):
            help_text = (
                "ℹ **Command Reference**\n\n"
                "🔑 `/redeem Retri-XXXX-XXXX` - Activate license\n"
                "🎯 `/report <target>` - Mass report (pick reason first)\n"
                "🥷 Stealth mode: join + browse + report (from menu)\n"
                "📡 `/join <channel_url>` - Mass join channel\n"
                "📡 `/flood_tg <target> <msg>` - Mass spam\n"
                "📡 `/dm <user1,user2> <msg>` - DM spam users\n"
                "🔍 `/scrape <channel> [limit]` - Scrape usernames\n"
                "📧 `/email <addr> <count>` - Email flood (max 200)\n"
                "📧 Multi: `/email a@b,c@d <count>`\n"
                "📱 `/ghost <number> <count>` - Ghost SMS (max 50)\n"
                "📱 Multi: `/ghost num1,num2 <count>`\n"
                "🎯 `/campaign <steps>` - Multi-vector campaign\n"
                "⏰ `/schedule <min> <command>` - Schedule operation\n"
                "⏰ `/scheduled` - View pending schedules\n"
                "⏰ `/unschedule <id>` - Cancel scheduled op\n"
                "👤 `/addaccount <name>` - Add Telegram account\n"
                "❌ `/cancel` - Cancel active operation\n\n"
                "**File upload:** Send a .txt file with targets (one per line)\n"
                "**Auto-export:** Results exported as .txt for large operations\n"
                "**Campaign format:** `/campaign email:a@b:50 sms:555:20 report:@ch:spam`\n"
                "Use the menu buttons for guided operations."
            )
            await event.respond(help_text)

        # -------------------------------------------------------------------
        # HANDLER: /addaccount
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern=r'/addaccount(\s+.*)?'))
        async def addaccount_handler(event):
            if not await self.check_auth(event):
                return

            args = event.message.text.strip().split()
            if len(args) < 2:
                await event.respond("Usage: `/addaccount <session_name>`")
                return

            name = args[1]

            session_path = os.path.join("sessions", f"{name}.session")
            if os.path.exists(session_path):
                await event.respond(f"❌ Session `{name}` already exists.")
                return

            self._account_wizard[event.sender_id] = {
                "name": name,
                "step": "phone",
            }
            await event.respond(
                f"👤 **Adding Account: {name}**\n\n"
                f"Send the phone number (with country code, e.g. +12125551234):\n\n"
                f"Type any /command to cancel."
            )

        # -------------------------------------------------------------------
        # HANDLER: /schedule
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern=r'/schedule(\s+.*)?'))
        async def schedule_handler(event):
            if not await self.check_auth(event):
                return

            raw = event.message.text.strip()
            parts = raw.split(maxsplit=2)
            if len(parts) < 3:
                await event.respond(
                    "Usage: `/schedule <minutes> <command>`\n\n"
                    "Examples:\n"
                    "  `/schedule 30 /email target@mail.com 50`\n"
                    "  `/schedule 60 /ghost 5551234567 20`\n"
                    "  `/schedule 10 /flood_tg @target spam msg`"
                )
                return

            try:
                delay_min = int(parts[1])
            except ValueError:
                await event.respond("❌ Delay must be a number of minutes.")
                return

            if delay_min < 1 or delay_min > 1440:
                await event.respond("❌ Delay must be between 1 and 1440 minutes (24h).")
                return

            command = parts[2]
            self._schedule_counter += 1
            schedule_id = self._schedule_counter
            run_at = datetime.now() + timedelta(minutes=delay_min)

            async def run_scheduled():
                await asyncio.sleep(delay_min * 60)
                await self.bot.send_message(event.chat_id, f"⏰ **Scheduled operation #{schedule_id} starting:** `{command}`")
                await self._execute_scheduled(event.chat_id, event.sender_id, command)
                if event.chat_id in self._scheduled:
                    self._scheduled[event.chat_id] = [
                        s for s in self._scheduled[event.chat_id] if s["id"] != schedule_id
                    ]

            task = asyncio.create_task(run_scheduled())

            if event.chat_id not in self._scheduled:
                self._scheduled[event.chat_id] = []
            self._scheduled[event.chat_id].append({
                "id": schedule_id,
                "task": task,
                "command": command,
                "run_at": run_at.strftime("%Y-%m-%d %H:%M:%S"),
            })

            await event.respond(
                f"⏰ **Scheduled #{schedule_id}**\n"
                f"Command: `{command}`\n"
                f"Runs at: `{run_at.strftime('%H:%M:%S')}` ({delay_min} min)"
            )

        # -------------------------------------------------------------------
        # HANDLER: /scheduled
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='/scheduled'))
        async def scheduled_list_handler(event):
            entries = self._scheduled.get(event.chat_id, [])
            active = [s for s in entries if not s["task"].done()]

            if not active:
                await event.respond("⏰ No pending scheduled operations.")
                return

            lines = ["⏰ **Scheduled Operations:**\n"]
            for s in active:
                lines.append(f"  #{s['id']} | `{s['command']}` | at {s['run_at']}")
            lines.append(f"\nUse `/unschedule <id>` to cancel.")
            await event.respond("\n".join(lines))

        # -------------------------------------------------------------------
        # HANDLER: DX Scanner Menu
        # -------------------------------------------------------------------
        @self.bot.on(events.CallbackQuery(data=b'dx_menu'))
        async def dx_menu_handler(event):
            await event.edit(
                "🔍 **DXOnline Scanner**\n\n"
                "Detect if a BIN belongs to a Credit Union using the DXOnline platform.\n\n"
                "Type `/dx <bin>` to scan directly.",
                buttons=[
                    [Button.inline("⬅️ Back", b"main_menu")]
                ]
            )

        # -------------------------------------------------------------------
        # HANDLER: DX Scanner Menu
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='🔍 DX Scanner'))
        async def dx_prompt(event):
            if not await self.check_auth(event):
                return
            await event.respond(
                "🔍 **DXOnline Scanner**\n\n"
                "Detect if a BIN belongs to a Credit Union using the DXOnline platform.\n\n"
                "Usage: `/dx <bin>`"
            )

        @self.bot.on(events.NewMessage(pattern=r'/dx\s+(\d+)'))
        async def dx_scan_handler(event):
            if not await self.check_auth(event):
                return
            bin_num = event.pattern_match.group(1)
            msg = await event.respond(f"🔍 Scanning `{bin_num}` for DX compatibility...")
            
            res = await self._dx_scanner.scan_bin(bin_num)
            
            if res["status"] == "error":
                await msg.edit(f"❌ **Error:** {res['message']}")
            elif res["status"] == "incompatible":
                await msg.edit(
                    f"🏦 **Bank:** `{res['bank']}`\n"
                    f"❌ **Status:** Incompatible\n"
                    f"Reason: {res['reason']}"
                )
            else:
                await msg.edit(
                    f"🏦 **Bank:** `{res['bank']}`\n"
                    f"🌍 **Country:** `{res['country']}`\n"
                    f"💳 **Card:** `{res['scheme']} {res['type']}` ({res['level']})\n\n"
                    f"✅ **DX Compatibility:** Verified\n"
                    f"🔗 **Portal:** {res['portal']}\n\n"
                    f"_{res['message']}_"
                )

        # -------------------------------------------------------------------
        # HANDLER: /unschedule
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern=r'/unschedule(\s+.*)?'))
        async def unschedule_handler(event):
            args = event.message.text.strip().split()
            if len(args) < 2:
                await event.respond("Usage: `/unschedule <id>`")
                return

            try:
                target_id = int(args[1])
            except ValueError:
                await event.respond("❌ ID must be a number.")
                return

            entries = self._scheduled.get(event.chat_id, [])
            for s in entries:
                if s["id"] == target_id:
                    s["task"].cancel()
                    entries.remove(s)
                    await event.respond(f"✅ Cancelled scheduled operation #{target_id}")
                    return

            await event.respond(f"❌ No scheduled operation with ID #{target_id}")

        # -------------------------------------------------------------------
        # HANDLER: /cancel
        # -------------------------------------------------------------------
        @self.bot.on(events.NewMessage(pattern='/cancel'))
        async def cancel_handler(event):
            sync_event = self._active_ops.get(event.chat_id)
            async_event = self._active_async_ops.get(event.chat_id)

            if sync_event:
                sync_event.set()
                await event.respond("⏹ **Cancellation requested** for active operation...")
            elif async_event:
                async_event.set()
                await event.respond("⏹ **Cancellation requested** for active operation...")
            else:
                await event.respond("No active operation to cancel.")




# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------


async def shutdown(bot: EniBot) -> None:
    logger.info("Shutting down gracefully...")
    for client in bot.reper.clients:
        try:
            await client.disconnect()
        except Exception:
            pass
    await bot.bot.disconnect()


async def main() -> None:
    bot_instance = EniBot(BOT_TOKEN, API_ID, API_HASH)
    await bot_instance.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt.")
