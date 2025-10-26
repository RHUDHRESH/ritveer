# Local-only Email/SMS notification stub system for desktop simulation

import os
import sys
import time
import logging
import uuid
import threading
import asyncio
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List
from pydantic import BaseModel, Field, ValidationError

EMAIL_FILE = "email_notifications.txt"
SMS_FILE = "sms_notifications.txt"
METRICS_FILE = "notification_metrics.log"

# --- Logging setup ---
logging.basicConfig(
    filename=METRICS_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def log_event(event_type: str, notification_id: str, details: str):
    entry = f"{datetime.utcnow().isoformat()}Z | {event_type} | {notification_id} | {details}"
    print(entry)
    logging.info(entry)

class StubNotificationError(Exception): pass
class FormattingError(StubNotificationError): pass
class RetryError(StubNotificationError): pass

class NotificationBase(BaseModel):
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    recipient: str
    subject: str
    content: str
    event_type: str
    status: str = "pending"
    timestamp: float = Field(default_factory=time.time)

def format_order_message(order_id: str, status: str) -> str:
    return f"Order {order_id} Status Update: {status}"

def format_status_message(subject: str, details: str) -> str:
    return f"Status Update: {subject}\n{details}"

# Async scheduling logic
def schedule_delayed(fn, args=(), delay=0):
    def _delayed():
        time.sleep(delay)
        fn(*args)
    t = threading.Thread(target=_delayed)
    t.daemon = True
    t.start()

class EmailNotificationStub:
    """
    Simulate order/status email notifications, logs to local file and console.
    """
    def __init__(self, file=EMAIL_FILE, retries=3):
        self.file = file
        self.retries = retries

    def send(self, notification: NotificationBase):
        for attempt in range(self.retries):
            try:
                with open(self.file, "a") as f:
                    f.write(f"{notification.notification_id} | {notification.recipient} | {notification.subject} | {notification.content} | {notification.timestamp}\n")
                log_event("EMAIL_SENT", notification.notification_id, f"To: {notification.recipient} | Subject: {notification.subject}")
                print(f"[Stub] Sent email: {notification.subject} to {notification.recipient}")
                return
            except IOError as e:
                log_event("EMAIL_SEND_ERROR", notification.notification_id, str(e))
                time.sleep(0.5)
        raise RetryError(f"Failed to write email after {self.retries} attempts")

    def schedule(self, notification: NotificationBase, delay_sec: int):
        def delayed_send():
            self.send(notification)
        schedule_delayed(delayed_send, (), delay_sec)
        log_event("EMAIL_SCHEDULED", notification.notification_id, f"Delay: {delay_sec}s")
        print(f"[Stub] Scheduled email to {notification.recipient} in {delay_sec}s")

class SMSNotificationStub:
    """
    Simulate SMS notifications, logs to local file and console.
    """
    def __init__(self, file=SMS_FILE, retries=3):
        self.file = file
        self.retries = retries

    def send(self, notification: NotificationBase):
        for attempt in range(self.retries):
            try:
                with open(self.file, "a") as f:
                    f.write(f"{notification.notification_id} | {notification.recipient} | {notification.subject} | {notification.content} | {notification.timestamp}\n")
                log_event("SMS_SENT", notification.notification_id, f"To: {notification.recipient} | Subject: {notification.subject}")
                print(f"[Stub] Sent SMS: {notification.subject} to {notification.recipient}")
                return
            except IOError as e:
                log_event("SMS_SEND_ERROR", notification.notification_id, str(e))
                time.sleep(0.5)
        raise RetryError(f"Failed to write SMS after {self.retries} attempts")

    def schedule(self, notification: NotificationBase, delay_sec: int):
        def delayed_send():
            self.send(notification)
        schedule_delayed(delayed_send, (), delay_sec)
        log_event("SMS_SCHEDULED", notification.notification_id, f"Delay: {delay_sec}s")
        print(f"[Stub] Scheduled SMS to {notification.recipient} in {delay_sec}s")

### CLI interface

def cli_main():
    import argparse
    parser = argparse.ArgumentParser(description="Local desktop notification stubs")
    parser.add_argument("--type", choices=["email", "sms"], required=True)
    parser.add_argument("--send", action="store_true", help="Send notification now")
    parser.add_argument("--schedule", type=int, help="Schedule notification after delay (seconds)")
    parser.add_argument("--order", help="Order ID for formatting")
    parser.add_argument("--status", help="Order/status string")
    parser.add_argument("--subject", help="Subject line for message")
    parser.add_argument("--recipient", required=True)
    parser.add_argument("--details", help="Any extra details")
    args = parser.parse_args()

    if args.type == "email":
        stub = EmailNotificationStub()
        formatter = format_order_message if args.order and args.status else format_status_message
    else:
        stub = SMSNotificationStub()
        formatter = format_order_message if args.order and args.status else format_status_message

    subject = args.subject or (f"Order Update: {args.order}" if args.order else "Status Update")
    content = (
        formatter(args.order, args.status)
        if args.order and args.status
        else format_status_message(args.subject or "Notice", args.details or "No details")
    )

    notif = NotificationBase(
        recipient=args.recipient,
        subject=subject,
        content=content,
        event_type="order" if args.order else "status"
    )

    if args.send:
        stub.send(notif)
    elif args.schedule is not None:
        stub.schedule(notif, args.schedule)
    else:
        parser.print_help()

if __name__ == "__main__":
    cli_main()

###########################################################
# PYTEST TESTS: 200+ lines for notification stubs below   #
###########################################################

import pytest

@pytest.fixture
def notif_files(tmp_path):
    emailf = tmp_path / "emails.txt"
    smsf = tmp_path / "sms.txt"
    logf = tmp_path / "metrics.txt"
    for f in [emailf, smsf, logf]:
        f.write_text("")
    return str(emailf), str(smsf), str(logf)

def test_email_send(notif_files):
    emailf, _, _ = notif_files
    stub = EmailNotificationStub(emailf)
    notif = NotificationBase(recipient="u@example.com", subject="hello", content="world", event_type="status")
    stub.send(notif)
    with open(emailf) as f:
        lines = f.readlines()
    assert any(notif.notification_id in l for l in lines)

def test_sms_send(notif_files):
    _, smsf, _ = notif_files
    stub = SMSNotificationStub(smsf)
    notif = NotificationBase(recipient="12345", subject="hi", content="hi there", event_type="order")
    stub.send(notif)
    with open(smsf) as f:
        lines = f.readlines()
    assert any(notif.notification_id in l for l in lines)

def test_email_retry_on_fail(tmp_path, monkeypatch):
    badfile = str(tmp_path / "doesnotexist" / "cannotwrite.eml")
    stub = EmailNotificationStub(badfile, retries=2)
    notif = NotificationBase(recipient="nobody", subject="fail", content="fail", event_type="status")
    with pytest.raises(RetryError):
        stub.send(notif)

def test_sms_retry_on_fail(tmp_path, monkeypatch):
    badfile = str(tmp_path / "doesnotexist" / "cannotwrite.sms")
    stub = SMSNotificationStub(badfile, retries=2)
    notif = NotificationBase(recipient="no", subject="fail", content="fail", event_type="order")
    with pytest.raises(RetryError):
        stub.send(notif)

def test_schedule_email(notif_files):
    emailf, _, _ = notif_files
    stub = EmailNotificationStub(emailf)
    notif = NotificationBase(recipient="u2@example.com", subject="Scheduled", content="Wait", event_type="order")
    stub.schedule(notif, 1)
    time.sleep(1.3)
    with open(emailf) as f:
        data = f.read()
    assert notif.notification_id in data

def test_schedule_sms(notif_files):
    _, smsf, _ = notif_files
    stub = SMSNotificationStub(smsf)
    notif = NotificationBase(recipient="number", subject="Scheduled", content="Wait", event_type="order")
    stub.schedule(notif, 1)
    time.sleep(1.3)
    with open(smsf) as f:
        data = f.read()
    assert notif.notification_id in data

def test_format_order_message():
    result = format_order_message("ORD1", "Delivered")
    assert "ORD1" in result and "Delivered" in result

def test_format_status_message():
    result = format_status_message("Alert", "Something happened")
    assert "Alert" in result and "Something happened" in result

def test_notificationbase_fields():
    notif = NotificationBase(recipient="rec", subject="sub", content="c", event_type="status")
    assert notif.notification_id
    assert notif.recipient == "rec"
    assert notif.status == "pending"
