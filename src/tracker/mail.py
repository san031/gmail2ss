

import email
import imaplib
import os
import re
from datetime import date, timedelta
from email import policy
from html import unescape

from dotenv import load_dotenv

load_dotenv()

IMAP_HOST = "imap.gmail.com"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _imap_date(d: date) -> str:
    # IMAP needs English month names; strftime("%b") follows the OS locale
    return f"{d.day:02d}-{MONTHS[d.month - 1]}-{d.year}"


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return unescape(text)


def _body_text(msg, max_chars: int) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    text = part.get_content()
    if part.get_content_subtype() == "html":
        text = _html_to_text(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _parse(raw: bytes, max_chars: int) -> dict:
    msg = email.message_from_bytes(raw, policy=policy.default)
    return {
        "email_id": (msg["Message-ID"] or "").strip(),
        "from": str(msg["From"] or ""),
        "subject": str(msg["Subject"] or ""),
        "date": str(msg["Date"] or ""),
        "body": _body_text(msg, max_chars),
    }


def fetch_recent_emails(days: int = 7, limit: int = 20, folder: str = "INBOX",
                        max_chars: int = 4000) -> list[dict]:
    """Return the newest `limit` emails from the last `days` days, newest first."""
    address = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_APP_PASSWORD"]
    since = _imap_date(date.today() - timedelta(days=days))

    with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
        imap.login(address, password)
        imap.select(folder, readonly=True)

        status, data = imap.uid("search", None, "SINCE", since)
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {data}")
        uids = data[0].split()[-limit:]

        emails = []
        for uid in reversed(uids):
            status, parts = imap.uid("fetch", uid, "(BODY.PEEK[])")
            if status != "OK" or not parts or parts[0] is None:
                continue
            emails.append(_parse(parts[0][1], max_chars))
    return emails


if __name__ == "__main__":
    for m in fetch_recent_emails(days=3, limit=10):
        print(f"{m['date']} | {m['from']} | {m['subject']}")
        print(f"   id: {m['email_id']}")
        print(f"   body: {m['body'][:120]}...\n")
