import asyncio
import json
import logging
import os
import sys
import random
import argparse
import time as _time
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse
from dotenv import load_dotenv
from telethon import TelegramClient, functions, types, errors as tg_errors
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from rich.prompt import Prompt
from rich import print as rprint
from typing import List, Dict, Union, Optional, Tuple, Any

load_dotenv()

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import socks
except ImportError:
    socks = None

console = Console()

BANNER = """
[bold cyan]
  ______       _ _____
 |  ____|     (_)  __ \\
 | |__   _ __  _| |__) |___ _ __   ___ _ __
 |  __| | '_ \\| |  _  // _ \\ '_ \\ / _ \\ '__|
 | |____| | | | | | \\ \\  __/ |_) |  __/ |
 |______|_| |_|_|_|  \\_\\___| .__/ \\___|_|
                           | |
                           |_|
[/bold cyan]
[italic magenta]Retri x Yuntoe Reaper - Tactical Arsenal[/italic magenta]
"""

DEFAULT_API_ID = int(os.environ.get("API_ID", "0"))
DEFAULT_API_HASH = os.environ.get("API_HASH", "")

REPORT_TYPES = {
    'spam': types.InputReportReasonSpam(),
    'violence': types.InputReportReasonViolence(),
    'child_abuse': types.InputReportReasonChildAbuse(),
    'pornography': types.InputReportReasonPornography(),
    'fake': types.InputReportReasonFake(),
    'copyright': types.InputReportReasonCopyright(),
    'other': types.InputReportReasonOther()
}

MAX_FLOOD_WAIT = 120
HEALTH_FILE = "account_health.json"

# ---------------------------------------------------------------------------
# REPORT MESSAGE POOL
# ---------------------------------------------------------------------------

REPORT_MESSAGES = [
    "This account is posting spam content and unsolicited messages",
    "Distributing inappropriate and harmful material to users",
    "This user is harassing other members of the community",
    "Account is involved in scam and fraud activities",
    "Sharing violent and disturbing content repeatedly",
    "This profile is impersonating another person or organization",
    "Account is part of a coordinated inauthentic network",
    "Posting misleading information and fake news content",
    "This user is sending unsolicited commercial advertisements",
    "Promoting illegal activities and prohibited services",
    "Account is engaged in targeted harassment and bullying",
    "Sharing copyrighted material without authorization",
    "This profile contains offensive and abusive material",
    "User is repeatedly violating community guidelines and ToS",
    "Account appears to be automated bot behavior spreading spam",
    "Distributing phishing links and malware to other users",
    "This user is selling prohibited and restricted items",
    "Profile is being used for exploitation and grooming",
    "Account is spreading hate speech and discriminatory content",
    "This channel promotes dangerous misinformation at scale",
    "Suspicious account activity detected: possible compromised account",
    "User is flooding chats with repetitive unsolicited content",
]

# ---------------------------------------------------------------------------
# DEVICE FINGERPRINTS
# ---------------------------------------------------------------------------

DEVICE_FINGERPRINTS = [
    {"device_model": "Samsung Galaxy S24", "system_version": "Android 14", "app_version": "10.14.5"},
    {"device_model": "iPhone 15 Pro", "system_version": "iOS 17.5", "app_version": "10.14.5"},
    {"device_model": "Google Pixel 8", "system_version": "Android 14", "app_version": "10.14.5"},
    {"device_model": "Samsung Galaxy S23", "system_version": "Android 13", "app_version": "10.12.0"},
    {"device_model": "iPhone 14", "system_version": "iOS 17.4", "app_version": "10.13.2"},
    {"device_model": "OnePlus 12", "system_version": "Android 14", "app_version": "10.14.5"},
    {"device_model": "Xiaomi 14", "system_version": "Android 14", "app_version": "10.14.3"},
    {"device_model": "Huawei P60 Pro", "system_version": "Android 13", "app_version": "10.11.1"},
    {"device_model": "PC 64bit", "system_version": "Windows 11", "app_version": "4.16.8 x64"},
    {"device_model": "Desktop", "system_version": "macOS 14.5", "app_version": "4.16.8"},
    {"device_model": "Desktop", "system_version": "Ubuntu 24.04", "app_version": "4.16.6 x64"},
    {"device_model": "iPad Pro 12.9", "system_version": "iPadOS 17.5", "app_version": "10.14.5"},
    {"device_model": "Samsung Galaxy A54", "system_version": "Android 14", "app_version": "10.14.2"},
    {"device_model": "iPhone 13 Mini", "system_version": "iOS 17.3", "app_version": "10.12.4"},
    {"device_model": "Google Pixel 7a", "system_version": "Android 14", "app_version": "10.14.0"},
    {"device_model": "Motorola Edge 40", "system_version": "Android 13", "app_version": "10.13.1"},
]

# ---------------------------------------------------------------------------
# PROXY SUPPORT
# ---------------------------------------------------------------------------

PROXY_FILE = "proxies.txt"


def _parse_proxy_url(url: str) -> Optional[dict]:
    try:
        if "://" not in url:
            url = f"socks5://{url}"
        parsed = urlparse(url)
        return {
            "proxy_type": parsed.scheme.lower(),
            "addr": parsed.hostname,
            "port": parsed.port or 1080,
            "username": parsed.username,
            "password": parsed.password,
        }
    except Exception:
        return None


def _load_proxies() -> List[dict]:
    proxy_str = os.environ.get("PROXY_LIST", "")
    if proxy_str:
        raw_list = [p.strip() for p in proxy_str.split(",") if p.strip()]
    elif os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, "r") as f:
            raw_list = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        return []

    proxies = []
    for raw in raw_list:
        p = _parse_proxy_url(raw)
        if p:
            proxies.append(p)
    logger.info("Loaded %d proxies", len(proxies))
    return proxies


def _make_proxy_tuple(proxy_dict: dict) -> Optional[tuple]:
    if socks is None:
        return None
    type_map = {"socks5": socks.SOCKS5, "socks4": socks.SOCKS4, "http": socks.HTTP}
    return (
        type_map.get(proxy_dict["proxy_type"], socks.SOCKS5),
        proxy_dict["addr"],
        proxy_dict["port"],
        True,
        proxy_dict.get("username"),
        proxy_dict.get("password"),
    )


# ---------------------------------------------------------------------------
# ERROR CLASSIFICATION
# ---------------------------------------------------------------------------


class AccountAction:
    CONTINUE = "continue"
    WAIT = "wait"
    REMOVE = "remove"
    ABORT = "abort"


def classify_error(e: Exception) -> Tuple[str, float]:
    if isinstance(e, tg_errors.FloodWaitError):
        return AccountAction.WAIT, e.seconds
    elif isinstance(e, tg_errors.AuthKeyUnregisteredError):
        return AccountAction.REMOVE, 0
    elif isinstance(e, tg_errors.UserDeactivatedBanError):
        return AccountAction.REMOVE, 0
    elif isinstance(e, tg_errors.PeerFloodError):
        return AccountAction.WAIT, 300
    elif isinstance(e, tg_errors.ChatWriteForbiddenError):
        return AccountAction.CONTINUE, 0
    elif isinstance(e, tg_errors.UserBannedInChannelError):
        return AccountAction.CONTINUE, 0
    elif isinstance(e, tg_errors.ChannelPrivateError):
        return AccountAction.ABORT, 0
    elif isinstance(e, ConnectionError):
        return AccountAction.WAIT, 10
    else:
        return AccountAction.CONTINUE, 0


# ---------------------------------------------------------------------------
# ACCOUNT HEALTH TRACKING
# ---------------------------------------------------------------------------


@dataclass
class AccountStatus:
    session_name: str
    healthy: bool = True
    cooldown_until: float = 0.0
    total_actions: int = 0
    total_errors: int = 0
    last_error: str = ""
    is_banned: bool = False


# ---------------------------------------------------------------------------
# ADAPTIVE BATCH SIZING
# ---------------------------------------------------------------------------


class AdaptiveBatch:
    def __init__(self, initial: int = 5, minimum: int = 1, maximum: int = 10, window: int = 20) -> None:
        self.size = initial
        self._min = minimum
        self._max = maximum
        self._window = window
        self._recent: List[bool] = []

    def record(self, success: bool) -> None:
        self._recent.append(success)
        if len(self._recent) > self._window:
            self._recent = self._recent[-self._window:]
        self._adjust()

    def record_batch(self, successes: int, failures: int) -> None:
        for _ in range(successes):
            self._recent.append(True)
        for _ in range(failures):
            self._recent.append(False)
        if len(self._recent) > self._window:
            self._recent = self._recent[-self._window:]
        self._adjust()

    def _adjust(self) -> None:
        if len(self._recent) < 5:
            return
        error_rate = self._recent.count(False) / len(self._recent)
        if error_rate > 0.5:
            self.size = max(self._min, self.size - 2)
        elif error_rate > 0.3:
            self.size = max(self._min, self.size - 1)
        elif error_rate < 0.1 and len(self._recent) >= 10:
            self.size = min(self._max, self.size + 1)


# ---------------------------------------------------------------------------
# MESSAGE SPINNING
# ---------------------------------------------------------------------------


def spin_message(base_message: str) -> str:
    noise = "​" * random.randint(1, 5)

    words = base_message.split()
    if words and random.random() > 0.6:
        words[0] = words[0].upper() if random.random() > 0.5 else words[0].lower()

    endings = ["", ".", "!", "..", "..."]
    emojis = ["", "", "", "\U0001f525", "\U0001f440", "⚠️", "❗", ""]

    result = " ".join(words)
    result = result.rstrip(".!")
    result += random.choice(endings)

    if random.random() > 0.7:
        result += " " + random.choice(emojis)

    return result.strip() + noise


# ---------------------------------------------------------------------------
# MAIN CLASS
# ---------------------------------------------------------------------------


class EniReper:
    def __init__(self, api_id: int, api_hash: str) -> None:
        self.api_id = api_id
        self.api_hash = api_hash
        self.sessions_dir = "sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)
        self.clients: List[TelegramClient] = []
        self.account_health: Dict[str, AccountStatus] = {}
        self._load_health_state()

    def _session_name(self, client: TelegramClient) -> str:
        return os.path.basename(client.session.filename) if client.session.filename else "unknown"

    def _update_health(self, client: TelegramClient, error: Optional[Exception] = None) -> str:
        name = self._session_name(client)
        if name not in self.account_health:
            self.account_health[name] = AccountStatus(session_name=name)
        status = self.account_health[name]

        if error is None:
            status.total_actions += 1
            return AccountAction.CONTINUE

        status.total_errors += 1
        status.last_error = str(error)[:100]
        action, wait = classify_error(error)

        if action == AccountAction.REMOVE:
            status.is_banned = True
            status.healthy = False
            logger.warning("Account %s marked as banned: %s", name, error)
            self._save_health_state()
        elif action == AccountAction.WAIT:
            status.cooldown_until = _time.time() + wait
            logger.info("Account %s on cooldown for %.0fs", name, wait)

        if status.total_errors % 5 == 0:
            self._save_health_state()

        return action

    def get_healthy_clients(self) -> List[TelegramClient]:
        now = _time.time()
        healthy = []
        for client in self.clients:
            name = self._session_name(client)
            status = self.account_health.get(name)
            if status and (status.is_banned or now < status.cooldown_until):
                continue
            healthy.append(client)
        return healthy

    def get_health_report(self) -> List[dict]:
        report = []
        now = _time.time()
        for name, status in self.account_health.items():
            cooldown_remaining = max(0, status.cooldown_until - now)
            report.append({
                "name": name,
                "healthy": status.healthy and not status.is_banned,
                "actions": status.total_actions,
                "errors": status.total_errors,
                "cooldown_remaining": int(cooldown_remaining),
                "banned": status.is_banned,
                "last_error": status.last_error,
            })
        return report

    def _save_health_state(self) -> None:
        data = {}
        for name, status in self.account_health.items():
            data[name] = {
                "healthy": status.healthy,
                "total_actions": status.total_actions,
                "total_errors": status.total_errors,
                "last_error": status.last_error,
                "is_banned": status.is_banned,
            }
        try:
            tmp = HEALTH_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, HEALTH_FILE)
        except Exception as e:
            logger.warning("Failed to save health state: %s", e)

    def _load_health_state(self) -> None:
        if not os.path.exists(HEALTH_FILE):
            return
        try:
            with open(HEALTH_FILE, "r") as f:
                data = json.load(f)
            for name, info in data.items():
                self.account_health[name] = AccountStatus(
                    session_name=name,
                    healthy=info.get("healthy", True),
                    total_actions=info.get("total_actions", 0),
                    total_errors=info.get("total_errors", 0),
                    last_error=info.get("last_error", ""),
                    is_banned=info.get("is_banned", False),
                )
            logger.info("Loaded health state for %d accounts", len(data))
        except Exception as e:
            logger.warning("Failed to load health state: %s", e)

    async def add_account(self, name: str) -> None:
        console.print(Panel(f"[bold cyan]Adding Account:[/bold cyan] {name}", border_style="cyan"))
        client = TelegramClient(os.path.join(self.sessions_dir, name), self.api_id, self.api_hash)
        await client.start()
        rprint(f"[bold green]✔ Account {name} added successfully![/bold green]")
        logger.info("Account %s added", name)
        await client.disconnect()

    async def _connect_single(
        self, name: str, idx: int, proxies: List[dict], fp: dict
    ) -> Tuple[Optional[TelegramClient], str, Optional[dict]]:
        proxy = None
        proxy_info = None
        if proxies:
            proxy_info = proxies[idx % len(proxies)]
            proxy = _make_proxy_tuple(proxy_info)

        client = TelegramClient(
            os.path.join(self.sessions_dir, name),
            self.api_id, self.api_hash,
            device_model=fp["device_model"],
            system_version=fp["system_version"],
            app_version=fp["app_version"],
            proxy=proxy,
        )
        try:
            await client.connect()
            if await client.is_user_authorized():
                if proxy_info:
                    logger.info("Account %s via %s:%s [%s / %s]", name, proxy_info["addr"], proxy_info["port"], fp["device_model"], fp["system_version"])
                else:
                    logger.info("Account %s loaded [%s / %s]", name, fp["device_model"], fp["system_version"])
                return client, name, proxy_info
            else:
                await client.disconnect()
                return None, name, None
        except Exception as e:
            logger.warning("Failed to load account %s: %s", name, e)
            try:
                await client.disconnect()
            except Exception:
                pass
            return None, name, None

    async def load_accounts(self, force: bool = False) -> int:
        if self.clients and not force:
            return len(self.clients)

        for client in self.clients:
            try:
                await client.disconnect()
            except Exception:
                pass

        self.clients = []
        proxies = _load_proxies()
        if proxies and socks is None:
            logger.warning("PySocks not installed -- proxies disabled. Run: pip install pysocks")
            proxies = []

        files = [f for f in os.listdir(self.sessions_dir) if f.endswith('.session')]

        tasks = []
        for idx, f in enumerate(files):
            name = f.replace('.session', '')
            fp = random.choice(DEVICE_FINGERPRINTS)
            tasks.append(self._connect_single(name, idx, proxies, fp))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning("Account connect error: %s", result)
                continue
            client, name, proxy_info = result
            if client:
                self.clients.append(client)
                if name not in self.account_health:
                    self.account_health[name] = AccountStatus(session_name=name)

        self._save_health_state()
        logger.info("Loaded %d accounts (%d sessions, %d proxies) [parallel]", len(self.clients), len(files), len(proxies))
        return len(self.clients)

    # -----------------------------------------------------------------------
    # REPORT
    # -----------------------------------------------------------------------

    async def _report_single(
        self, client: TelegramClient, target_url: str, reason, message: str
    ) -> dict:
        result = {"success": 0, "failed": 0}
        for attempt in range(3):
            try:
                entity = await client.get_entity(target_url)

                report_msg = random.choice(REPORT_MESSAGES)
                await client(functions.account.ReportPeerRequest(
                    peer=entity, reason=reason, message=report_msg
                ))
                result["success"] += 1

                history = await client.get_messages(entity, limit=10)
                for msg in history:
                    try:
                        per_msg_text = random.choice(REPORT_MESSAGES)
                        await client(functions.messages.ReportRequest(
                            peer=entity, id=[msg.id], reason=reason, message=per_msg_text
                        ))
                        result["success"] += 1
                    except Exception:
                        result["failed"] += 1
                    await asyncio.sleep(random.uniform(0.3, 0.8))

                self._update_health(client)
                return result

            except tg_errors.FloodWaitError as e:
                if attempt < 2 and e.seconds <= MAX_FLOOD_WAIT:
                    logger.info("FloodWait on report (%s): %ds -- retrying", self._session_name(client), e.seconds)
                    await asyncio.sleep(e.seconds)
                    continue
                action = self._update_health(client, e)
                result["failed"] += 1
                result["action"] = action
                result["error"] = str(e)[:100]
                return result

            except Exception as e:
                action = self._update_health(client, e)
                result["failed"] += 1
                result["action"] = action
                result["error"] = str(e)[:100]
                return result

        return result

    async def report_target(
        self,
        target_url: str,
        reason_str: str,
        message: str = "Reporting for violations",
        batch_size: int = 5,
        progress_callback=None,
    ) -> dict:
        reason = REPORT_TYPES.get(reason_str.lower(), types.InputReportReasonOther())
        rprint(Panel(
            f"[bold white]Target:[/bold white] {target_url}\n[bold white]Reason:[/bold white] {reason_str}",
            title="Mass Reporting Initiation", border_style="cyan"
        ))

        healthy = self.get_healthy_clients()
        total = len(healthy)
        completed = 0
        results = {"total": total, "success": 0, "failed": 0, "skipped": 0, "errors": {}}
        start_time = _time.time()
        adaptive = AdaptiveBatch(initial=batch_size, minimum=1, maximum=10)

        i = 0
        while i < total:
            batch = healthy[i:i + adaptive.size]
            tasks = [self._report_single(client, target_url, reason, message) for client in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            batch_ok = 0
            batch_fail = 0
            for client, res in zip(batch, batch_results):
                completed += 1
                if isinstance(res, Exception):
                    action = self._update_health(client, res)
                    results["failed"] += 1
                    batch_fail += 1
                    err_name = type(res).__name__
                    results["errors"][err_name] = results["errors"].get(err_name, 0) + 1
                    if action == AccountAction.ABORT:
                        logger.warning("Aborting report: %s", res)
                        results["duration_seconds"] = round(_time.time() - start_time, 1)
                        return results
                else:
                    results["success"] += res.get("success", 0)
                    results["failed"] += res.get("failed", 0)
                    batch_ok += 1

                if progress_callback:
                    try:
                        await progress_callback(completed, total, results)
                    except Exception:
                        pass

            adaptive.record_batch(batch_ok, batch_fail)
            i += len(batch)
            await asyncio.sleep(random.uniform(1.0, 2.0))

        results["duration_seconds"] = round(_time.time() - start_time, 1)
        rprint(f"\n[bold green]✔ Mass reporting complete! {results['success']} reports sent.[/bold green]")
        logger.info("Report complete: %s", results)
        return results

    # -----------------------------------------------------------------------
    # JOIN
    # -----------------------------------------------------------------------

    async def join_target(
        self, target_url: str, batch_size: int = 3, progress_callback=None
    ) -> dict:
        rprint(f"[bold cyan]Deploying accounts to join:[/bold cyan] {target_url}")

        healthy = self.get_healthy_clients()
        total = len(healthy)
        completed = 0
        results = {"total": total, "success": 0, "failed": 0, "errors": {}}
        start_time = _time.time()
        adaptive = AdaptiveBatch(initial=batch_size, minimum=1, maximum=5)

        async def _join_single(client: TelegramClient) -> bool:
            for attempt in range(3):
                try:
                    entity = await client.get_entity(target_url)
                    await client(functions.channels.JoinChannelRequest(channel=entity))
                    self._update_health(client)
                    return True
                except tg_errors.FloodWaitError as e:
                    if attempt < 2 and e.seconds <= MAX_FLOOD_WAIT:
                        logger.info("FloodWait on join (%s): %ds", self._session_name(client), e.seconds)
                        await asyncio.sleep(e.seconds)
                        continue
                    self._update_health(client, e)
                    raise
                except Exception as e:
                    self._update_health(client, e)
                    raise
            return False

        i = 0
        while i < total:
            batch = healthy[i:i + adaptive.size]
            tasks = [_join_single(c) for c in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            batch_ok = 0
            batch_fail = 0
            for client, res in zip(batch, batch_results):
                completed += 1
                if isinstance(res, Exception):
                    results["failed"] += 1
                    batch_fail += 1
                    err_name = type(res).__name__
                    results["errors"][err_name] = results["errors"].get(err_name, 0) + 1
                else:
                    results["success"] += 1
                    batch_ok += 1

                if progress_callback:
                    try:
                        await progress_callback(completed, total, results)
                    except Exception:
                        pass

            adaptive.record_batch(batch_ok, batch_fail)
            i += len(batch)
            await asyncio.sleep(random.uniform(2.0, 5.0))

        results["duration_seconds"] = round(_time.time() - start_time, 1)
        logger.info("Join complete: %s", results)
        return results

    # -----------------------------------------------------------------------
    # SPAM
    # -----------------------------------------------------------------------

    async def spam_target(
        self,
        target_url: str,
        message: str,
        count: int = 1,
        batch_size: int = 5,
        progress_callback=None,
    ) -> dict:
        rprint(f"[bold cyan]Deploying spam to:[/bold cyan] {target_url}")

        healthy = self.get_healthy_clients()
        total = len(healthy) * count
        completed = 0
        results = {"total": total, "success": 0, "failed": 0, "errors": {}}
        start_time = _time.time()
        adaptive = AdaptiveBatch(initial=batch_size, minimum=1, maximum=10)

        async def _spam_single(client: TelegramClient) -> bool:
            for attempt in range(3):
                try:
                    entity = await client.get_entity(target_url)
                    spun = spin_message(message)
                    await client.send_message(entity, spun)
                    self._update_health(client)
                    return True
                except tg_errors.FloodWaitError as e:
                    if attempt < 2 and e.seconds <= MAX_FLOOD_WAIT:
                        logger.info("FloodWait on spam (%s): %ds", self._session_name(client), e.seconds)
                        await asyncio.sleep(e.seconds)
                        continue
                    self._update_health(client, e)
                    raise
                except Exception as e:
                    self._update_health(client, e)
                    raise
            return False

        for _ in range(count):
            i = 0
            while i < len(healthy):
                batch = healthy[i:i + adaptive.size]
                tasks = [_spam_single(c) for c in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                batch_ok = 0
                batch_fail = 0
                for client, res in zip(batch, batch_results):
                    completed += 1
                    if isinstance(res, Exception):
                        results["failed"] += 1
                        batch_fail += 1
                        err_name = type(res).__name__
                        results["errors"][err_name] = results["errors"].get(err_name, 0) + 1
                    else:
                        results["success"] += 1
                        batch_ok += 1

                    if progress_callback:
                        try:
                            await progress_callback(completed, total, results)
                        except Exception:
                            pass

                adaptive.record_batch(batch_ok, batch_fail)
                i += len(batch)
                await asyncio.sleep(random.uniform(0.5, 1.5))

        results["duration_seconds"] = round(_time.time() - start_time, 1)
        logger.info("Spam complete: %s", results)
        return results

    # -----------------------------------------------------------------------
    # DM SPAM
    # -----------------------------------------------------------------------

    async def dm_spam(
        self,
        targets: List[str],
        message: str,
        batch_size: int = 3,
        progress_callback=None,
    ) -> dict:
        rprint(f"[bold cyan]Deploying DM spam to {len(targets)} users[/bold cyan]")

        healthy = self.get_healthy_clients()
        total = len(targets)
        completed = 0
        results = {"total": total, "success": 0, "failed": 0, "errors": {}}
        start_time = _time.time()
        adaptive = AdaptiveBatch(initial=batch_size, minimum=1, maximum=5)

        async def _dm_single(username: str, assigned_client: TelegramClient) -> bool:
            for attempt in range(3):
                try:
                    entity = await assigned_client.get_entity(username)
                    spun = spin_message(message)
                    await assigned_client.send_message(entity, spun)
                    self._update_health(assigned_client)
                    return True
                except tg_errors.FloodWaitError as e:
                    if attempt < 2 and e.seconds <= MAX_FLOOD_WAIT:
                        logger.info("FloodWait on DM (%s): %ds", self._session_name(assigned_client), e.seconds)
                        await asyncio.sleep(e.seconds)
                        continue
                    self._update_health(assigned_client, e)
                    raise
                except Exception as e:
                    self._update_health(assigned_client, e)
                    raise
            return False

        i = 0
        while i < total:
            batch_targets = targets[i:i + adaptive.size]

            tasks = []
            for j, username in enumerate(batch_targets):
                client = healthy[(i + j) % len(healthy)] if healthy else None
                if not client:
                    break
                tasks.append(_dm_single(username, client))

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            batch_ok = 0
            batch_fail = 0
            for res in batch_results:
                completed += 1
                if isinstance(res, Exception):
                    results["failed"] += 1
                    batch_fail += 1
                    err_name = type(res).__name__
                    results["errors"][err_name] = results["errors"].get(err_name, 0) + 1
                else:
                    results["success"] += 1
                    batch_ok += 1

                if progress_callback:
                    try:
                        await progress_callback(completed, total, results)
                    except Exception:
                        pass

            adaptive.record_batch(batch_ok, batch_fail)
            i += len(batch_targets)
            await asyncio.sleep(random.uniform(3.0, 8.0))

        results["duration_seconds"] = round(_time.time() - start_time, 1)
        rprint(f"\n[bold green]✔ DM spam complete! {results['success']}/{total} delivered.[/bold green]")
        logger.info("DM spam complete: %s", results)
        return results

    # -----------------------------------------------------------------------
    # STEALTH REPORT (join + browse + report)
    # -----------------------------------------------------------------------

    async def stealth_report_target(
        self,
        target_url: str,
        reason_str: str,
        message: str = "Reporting for violations",
        batch_size: int = 5,
        progress_callback=None,
    ) -> dict:
        reason = REPORT_TYPES.get(reason_str.lower(), types.InputReportReasonOther())
        rprint(Panel(
            f"[bold white]Target:[/bold white] {target_url}\n[bold white]Mode:[/bold white] Stealth (join → browse → report)",
            title="Stealth Report Initiation", border_style="yellow"
        ))

        healthy = self.get_healthy_clients()
        total = len(healthy)
        completed = 0
        results = {"total": total, "success": 0, "failed": 0, "joined": 0, "errors": {}}
        start_time = _time.time()
        adaptive = AdaptiveBatch(initial=batch_size, minimum=1, maximum=8)

        async def _stealth_single(client: TelegramClient) -> dict:
            single = {"success": 0, "failed": 0, "joined": False}
            try:
                entity = await client.get_entity(target_url)

                try:
                    await client(functions.channels.JoinChannelRequest(channel=entity))
                    single["joined"] = True
                    await asyncio.sleep(random.uniform(2.0, 5.0))
                except (tg_errors.UserAlreadyParticipantError, Exception):
                    pass

                try:
                    messages = await client.get_messages(entity, limit=random.randint(5, 15))
                    if messages:
                        for msg in messages[:random.randint(2, 5)]:
                            try:
                                await client(functions.messages.GetMessagesViewsRequest(
                                    peer=entity, id=[msg.id], increment=True
                                ))
                            except Exception:
                                pass
                            await asyncio.sleep(random.uniform(0.5, 1.5))
                except Exception:
                    pass

                await asyncio.sleep(random.uniform(3.0, 8.0))

                report_msg = random.choice(REPORT_MESSAGES)
                await client(functions.account.ReportPeerRequest(
                    peer=entity, reason=reason, message=report_msg
                ))
                single["success"] += 1

                history = await client.get_messages(entity, limit=10)
                for msg in history:
                    try:
                        per_msg_text = random.choice(REPORT_MESSAGES)
                        await client(functions.messages.ReportRequest(
                            peer=entity, id=[msg.id], reason=reason, message=per_msg_text
                        ))
                        single["success"] += 1
                    except Exception:
                        single["failed"] += 1
                    await asyncio.sleep(random.uniform(0.3, 0.8))

                self._update_health(client)

            except tg_errors.FloodWaitError as e:
                self._update_health(client, e)
                single["failed"] += 1
            except Exception as e:
                self._update_health(client, e)
                single["failed"] += 1

            return single

        i = 0
        while i < total:
            batch = healthy[i:i + adaptive.size]
            tasks = [_stealth_single(c) for c in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            batch_ok = 0
            batch_fail = 0
            for res in batch_results:
                completed += 1
                if isinstance(res, Exception):
                    results["failed"] += 1
                    batch_fail += 1
                else:
                    results["success"] += res.get("success", 0)
                    results["failed"] += res.get("failed", 0)
                    if res.get("joined"):
                        results["joined"] += 1
                    batch_ok += 1 if res.get("success", 0) > 0 else 0
                    batch_fail += 1 if res.get("success", 0) == 0 else 0

                if progress_callback:
                    try:
                        await progress_callback(completed, total, results)
                    except Exception:
                        pass

            adaptive.record_batch(batch_ok, batch_fail)
            i += len(batch)
            await asyncio.sleep(random.uniform(2.0, 4.0))

        results["duration_seconds"] = round(_time.time() - start_time, 1)
        rprint(f"\n[bold green]✔ Stealth report complete! {results['success']} reports, {results['joined']} joins.[/bold green]")
        logger.info("Stealth report complete: %s", results)
        return results

    # -----------------------------------------------------------------------
    # USER SCRAPING
    # -----------------------------------------------------------------------

    async def scrape_users(
        self,
        target_url: str,
        limit: int = 200,
        progress_callback=None,
    ) -> list[str]:
        healthy = self.get_healthy_clients()
        if not healthy:
            logger.warning("No healthy clients for scraping")
            return []

        client = healthy[0]
        try:
            entity = await client.get_entity(target_url)
            participants = await client.get_participants(entity, limit=limit)
            usernames = []
            for user in participants:
                if user.username:
                    usernames.append(user.username)
                elif user.id:
                    usernames.append(str(user.id))

            if progress_callback:
                try:
                    await progress_callback(len(usernames), limit, {"scraped": len(usernames)})
                except Exception:
                    pass

            self._update_health(client)
            logger.info("Scraped %d users from %s", len(usernames), target_url)
            return usernames

        except tg_errors.ChatAdminRequiredError:
            logger.warning("Admin access required to scrape %s", target_url)
            return []
        except Exception as e:
            self._update_health(client, e)
            logger.error("User scrape failed for %s: %s", target_url, e)
            return []


# ---------------------------------------------------------------------------
# INTERACTIVE CLI
# ---------------------------------------------------------------------------


async def interactive_menu(reper: EniReper) -> None:
    while True:
        console.clear()
        rprint(BANNER)
        table = Table(title="Tactical Dashboard", border_style="magenta", show_header=False)
        table.add_row("[cyan]1[/cyan]", "Add New Account")
        table.add_row("[cyan]2[/cyan]", "Reload/View Accounts")
        table.add_row("[cyan]3[/cyan]", "Mass Report Target")
        table.add_row("[cyan]4[/cyan]", "Mass Join Channel")
        table.add_row("[cyan]5[/cyan]", "Mass Spam Target")
        table.add_row("[cyan]6[/cyan]", "DM Spam Users")
        table.add_row("[cyan]7[/cyan]", "Account Health")
        table.add_row("[cyan]8[/cyan]", "Exit")
        console.print(table)

        choice = Prompt.ask("Action", choices=["1", "2", "3", "4", "5", "6", "7", "8"])
        if choice == "1":
            name = Prompt.ask("Account Name")
            await reper.add_account(name)
        elif choice == "2":
            count = await reper.load_accounts(force=True)
            rprint(f"[bold green]{count} accounts ready.[/bold green]")
            Prompt.ask("Press Enter to continue")
        elif choice == "3":
            await reper.load_accounts()
            target = Prompt.ask("Target URL")
            reason = Prompt.ask("Reason", choices=list(REPORT_TYPES.keys()), default="spam")
            await reper.report_target(target, reason)
            Prompt.ask("Press Enter to continue")
        elif choice == "4":
            await reper.load_accounts()
            target = Prompt.ask("Channel URL")
            await reper.join_target(target)
            Prompt.ask("Press Enter to continue")
        elif choice == "5":
            await reper.load_accounts()
            target = Prompt.ask("Target URL/Username")
            msg = Prompt.ask("Spam Message")
            count = int(Prompt.ask("Messages per account", default="1"))
            await reper.spam_target(target, msg, count)
            Prompt.ask("Press Enter to continue")
        elif choice == "6":
            await reper.load_accounts()
            raw = Prompt.ask("Usernames (comma-separated)")
            targets = [t.strip() for t in raw.split(",") if t.strip()]
            msg = Prompt.ask("Message")
            await reper.dm_spam(targets, msg)
            Prompt.ask("Press Enter to continue")
        elif choice == "7":
            report = reper.get_health_report()
            if not report:
                rprint("[yellow]No account data yet. Load accounts first.[/yellow]")
            else:
                for acct in report:
                    status = "\U0001f7e2" if acct["healthy"] else "\U0001f534"
                    rprint(f"  {status} {acct['name']} | actions: {acct['actions']} | errors: {acct['errors']} | banned: {acct['banned']}")
            Prompt.ask("Press Enter to continue")
        elif choice == "8":
            break


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--add")
    parser.add_argument("--target")
    parser.add_argument("--reason", default="spam")
    parser.add_argument("--api-id", type=int, default=DEFAULT_API_ID)
    parser.add_argument("--api-hash", default=DEFAULT_API_HASH)
    args = parser.parse_args()

    reper = EniReper(args.api_id, args.api_hash)
    if args.add:
        await reper.add_account(args.add)
    elif args.target:
        await reper.load_accounts()
        await reper.report_target(args.target, args.reason)
    else:
        await interactive_menu(reper)

    for client in reper.clients:
        try:
            await client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    asyncio.run(main())
