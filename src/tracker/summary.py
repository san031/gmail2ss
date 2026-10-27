import os
import smtplib
import sys
from datetime import datetime, timedelta
from email.message import EmailMessage

from dotenv import load_dotenv

import sheet

load_dotenv()


def upcoming_interviews(days: int = 7) -> tuple[list, list]:
    now, end = datetime.now(), datetime.now() + timedelta(days=days)
    upcoming, unparsed = [], []
    for r in sheet.list_applications(status="Interview Scheduled"):
        try:
            when = datetime.strptime(str(r["Interview Date"]), "%Y-%m-%d %H:%M")
        except ValueError:
            unparsed.append(r)  # don't silently drop it
            continue
        if now <= when <= end:
            upcoming.append((when, r))
    return sorted(upcoming, key=lambda x: x[0]), unparsed


def build_summary(days: int = 7) -> str:
    upcoming, unparsed = upcoming_interviews(days)
    lines = [f"Interviews in the next {days} days:"]
    lines += [f"  {w:%a %d %b %H:%M}  {r['Company']} - {r['Role']} (round {r['Round']})"
              for w, r in upcoming] or ["  none"]
    if unparsed:
        lines.append("\nCheck manually (date not understood):")
        lines += [f"  {r['Company']} - {r['Role']}: {r['Interview Date']!r}" for r in unparsed]
    return "\n".join(lines)


def email_to_self(body: str) -> None:
    address = os.environ["EMAIL_ADDRESS"]
    msg = EmailMessage()
    msg["From"] = msg["To"] = address
    msg["Subject"] = f"Job tracker: interviews this week ({datetime.now():%d %b})"
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(address, os.environ["EMAIL_APP_PASSWORD"])
        smtp.send_message(msg)


if __name__ == "__main__":
    text = build_summary()
    print(text)
    if "--email" in sys.argv:
        email_to_self(text)
