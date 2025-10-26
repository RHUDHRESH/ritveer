# Local-only Telegram/WhatsApp webhook stubs for desktop simulation

import os
import sys
import time
import threading
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, ValidationError

# --- File constants ---
TELEGRAM_INBOX_FILE = "telegram_inbox.txt"
TELEGRAM_OUTBOX_FILE = "telegram_outbox.txt"
WHATSAPP_INBOX_FILE = "whatsapp_inbox.txt"
WHATSAPP_OUTBOX_FILE = "whatsapp_outbox.txt"
LOG_FILE = "messaging.log"


# --- Logging setup ---
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def log_event(event_type: str, message_id: str, details: str):
    entry = f"{datetime.utcnow().isoformat()}Z | {event_type} | {message_id} | {details}"
    print(entry)
    logging.info(entry)


# --- Error definitions ---
class StubException(Exception): pass
class MessageFormatError(StubException): pass
class HandlerRegistryError(StubException): pass
class FileIOError(StubException): pass

# --- Data models ---

class MessageStub(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: str
    source: str
    text: str
    timestamp: float = Field(default_factory=time.time)

class CallbackRegistry:
    """
    Registry for handler functions (simulates agent connection).
    """
    def __init__(self):
        self._handlers: Dict[str, Callable[[MessageStub], None]] = {}

    def register(self, name: str, handler: Callable[[MessageStub], None]):
        if name in self._handlers:
            raise HandlerRegistryError(f"Handler for '{name}' already exists.")
        self._handlers[name] = handler

    def call(self, name: str, msg: MessageStub):
        if name not in self._handlers:
            raise HandlerRegistryError(f"No handler for '{name}'.")
        return self._handlers[name](msg)
    
    def unregister(self, name: str):
        if name in self._handlers:
            del self._handlers[name]

# Instantiate a global registry
handler_registry = CallbackRegistry()

### Core Webhook Stubs

class TelegramWebhookStub:
    """
    Local-only simulation of Telegram Webhook.
    Reads messages from telegram_inbox.txt, writes responses to telegram_outbox.txt.
    """

    PLATFORM = "telegram"

    def __init__(self, inbox_file=TELEGRAM_INBOX_FILE, outbox_file=TELEGRAM_OUTBOX_FILE):
        self.inbox_file = inbox_file
        self.outbox_file = outbox_file
        self.last_processed = set()
        self._ensure_files()

    def _ensure_files(self):
        for f in (self.inbox_file, self.outbox_file):
            if not os.path.exists(f):
                open(f, "a").close()

    def receive_messages(self) -> List[MessageStub]:
        messages = []
        try:
            with open(self.inbox_file, "r") as f:
                for line in f:
                    try:
                        parts = line.strip().split(" | ", 3)
                        if len(parts) < 3:
                            continue
                        message_id, source, text = parts[:3]
                        if message_id in self.last_processed:
                            continue
                        msg = MessageStub(
                            message_id=message_id,
                            platform=self.PLATFORM,
                            source=source,
                            text=text
                        )
                        messages.append(msg)
                        self.last_processed.add(message_id)
                        log_event("TG_RECEIVED", message_id, f"From: {source} | Text: {text}")
                    except Exception as e:
                        continue
        except IOError:
            raise FileIOError(f"Could not read {self.inbox_file}.")
        return messages

    def send_message(self, msg: MessageStub):
        try:
            with open(self.outbox_file, "a") as f:
                f.write(f"{msg.message_id} | {msg.source} | {msg.text}\n")
            log_event("TG_SENT", msg.message_id, f"To: {msg.source} | Text: {msg.text}")
        except IOError as e:
            raise FileIOError(f"Error writing to {self.outbox_file}: {str(e)}")

    def process_messages(self):
        messages = self.receive_messages()
        for msg in messages:
            # Simulate handler (could be a LangGraph pipeline)
            try:
                handler_registry.call("telegram", msg)
            except HandlerRegistryError:
                print(f"[Stub] No handler registered for 'telegram', printing message.")
                print(f"Telegram received: {msg.text} (from {msg.source})")
            except Exception as e:
                print(f"[Stub] Error calling handler: {e}")

    def simulate_receive(self, source="user"):
        text = input("Enter Telegram message: ")
        msg = MessageStub(platform=self.PLATFORM, source=source, text=text)
        # Append to inbox file
        try:
            with open(self.inbox_file, "a") as f:
                f.write(f"{msg.message_id} | {source} | {text}\n")
            print(f"[Stub] Message added to inbox (simulate incoming)")
            log_event("TG_STUB_RECEIVE", msg.message_id, f"Simulate message from {source}")
        except IOError as e:
            raise FileIOError(f"Could not write to {self.inbox_file}")

class WhatsAppWebhookStub:
    """
    Local-only simulation of WhatsApp Webhook.
    Reads messages from whatsapp_inbox.txt, writes to whatsapp_outbox.txt.
    """

    PLATFORM = "whatsapp"

    def __init__(self, inbox_file=WHATSAPP_INBOX_FILE, outbox_file=WHATSAPP_OUTBOX_FILE):
        self.inbox_file = inbox_file
        self.outbox_file = outbox_file
        self.last_processed = set()
        self._ensure_files()

    def _ensure_files(self):
        for f in (self.inbox_file, self.outbox_file):
            if not os.path.exists(f):
                open(f, "a").close()

    def receive_messages(self) -> List[MessageStub]:
        messages = []
        try:
            with open(self.inbox_file, "r") as f:
                for line in f:
                    try:
                        parts = line.strip().split(" | ", 3)
                        if len(parts) < 3:
                            continue
                        message_id, source, text = parts[:3]
                        if message_id in self.last_processed:
                            continue
                        msg = MessageStub(
                            message_id=message_id,
                            platform=self.PLATFORM,
                            source=source,
                            text=text
                        )
                        messages.append(msg)
                        self.last_processed.add(message_id)
                        log_event("WA_RECEIVED", message_id, f"From: {source} | Text: {text}")
                    except Exception as e:
                        continue
        except IOError:
            raise FileIOError(f"Could not read {self.inbox_file}.")
        return messages

    def send_message(self, msg: MessageStub):
        try:
            with open(self.outbox_file, "a") as f:
                f.write(f"{msg.message_id} | {msg.source} | {msg.text}\n")
            log_event("WA_SENT", msg.message_id, f"To: {msg.source} | Text: {msg.text}")
        except IOError as e:
            raise FileIOError(f"Error writing to {self.outbox_file}: {str(e)}")

    def process_messages(self):
        messages = self.receive_messages()
        for msg in messages:
            # Simulate handler (could be a LangGraph pipeline)
            try:
                handler_registry.call("whatsapp", msg)
            except HandlerRegistryError:
                print(f"[Stub] No handler registered for 'whatsapp', printing message.")
                print(f"WhatsApp received: {msg.text} (from {msg.source})")
            except Exception as e:
                print(f"[Stub] Error calling handler: {e}")

    def simulate_receive(self, source="user"):
        text = input("Enter WhatsApp message: ")
        msg = MessageStub(platform=self.PLATFORM, source=source, text=text)
        # Append to inbox file
        try:
            with open(self.inbox_file, "a") as f:
                f.write(f"{msg.message_id} | {source} | {text}\n")
            print(f"[Stub] Message added to inbox (simulate incoming)")
            log_event("WA_STUB_RECEIVE", msg.message_id, f"Simulate message from {source}")
        except IOError as e:
            raise FileIOError(f"Could not write to {self.inbox_file}")

### CLI interface

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Local desktop messaging webhook stubs")
    parser.add_argument("--platform", choices=["telegram", "whatsapp"], default="telegram", help="Choose platform to operate")
    parser.add_argument("--send", action="store_true", help="Send message to outbox")
    parser.add_argument("--receive", action="store_true", help="Process new messages from inbox")
    parser.add_argument("--simulate", action="store_true", help="Simulate message receive (adds to inbox)")
    args = parser.parse_args()

    if args.platform == "telegram":
        stub = TelegramWebhookStub()
    else:
        stub = WhatsAppWebhookStub()

    if args.simulate:
        stub.simulate_receive()
    elif args.receive:
        stub.process_messages()
    elif args.send:
        src = input("Enter recipient/source: ")
        msgtxt = input("Enter message: ")
        msg = MessageStub(platform=args.platform, source=src, text=msgtxt)
        stub.send_message(msg)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

###########################################################
# PYTEST TESTS: 200+ lines for messaging stubs below      #
###########################################################

import pytest

class DummyHandler:
    def __init__(self):
        self.last_message = None

    def handle(self, msg):
        self.last_message = msg

@pytest.fixture
def telegram_files(tmp_path):
    inbox = tmp_path / "tg_inbox.txt"
    outbox = tmp_path / "tg_outbox.txt"
    log = tmp_path / "tg_log.txt"
    for f in [inbox, outbox, log]:
        f.write_text("")
    return str(inbox), str(outbox), str(log)

@pytest.pytest.fixture
def whatsapp_files(tmp_path):
    inbox = tmp_path / "wa_inbox.txt"
    outbox = tmp_path / "wa_outbox.txt"
    log = tmp_path / "wa_log.txt"
    for f in [inbox, outbox, log]:
        f.write_text("")
    return str(inbox), str(outbox), str(log)

def test_telegram_send_receive(telegram_files, monkeypatch):
    inbox, outbox, _ = telegram_files
    stub = TelegramWebhookStub(inbox, outbox)
    msg = MessageStub(platform="telegram", source="alice", text="hi")
    stub.send_message(msg)
    # Should appear in outbox
    with open(outbox) as f:
        lines = f.readlines()
    assert any(msg.message_id in l for l in lines)
    # Simulate inbox receive
    with open(inbox, "a") as f:
        f.write(f"{msg.message_id} | alice | hi\n")
    monkeypatch.setattr(handler_registry, "_handlers", {{}})
    dummy = DummyHandler()
    handler_registry.register("telegram", dummy.handle)
    stub.process_messages()
    assert dummy.last_message is not None
    assert dummy.last_message.text == "hi"

def test_whatsapp_send_receive(whatsapp_files, monkeypatch):
    inbox, outbox, _ = whatsapp_files
    stub = WhatsAppWebhookStub(inbox, outbox)
    msg = MessageStub(platform="whatsapp", source="bob", text="hello")
    stub.send_message(msg)
    with open(outbox) as f:
        lines = f.readlines()
    assert any(msg.message_id in l for l in lines)
    with open(inbox, "a") as f:
        f.write(f"{msg.message_id} | bob | hello\n")
    monkeypatch.setattr(handler_registry, "_handlers", {{}})
    dummy = DummyHandler()
    handler_registry.register("whatsapp", dummy.handle)
    stub.process_messages()
    assert dummy.last_message is not None
    assert dummy.last_message.text == "hello"

def test_handler_errors(telegram_files, monkeypatch):
    inbox, outbox, _ = telegram_files
    stub = TelegramWebhookStub(inbox, outbox)
    msg = MessageStub(platform="telegram", source="alice", text="fail")
    with open(inbox, "a") as f:
        f.write(f"{msg.message_id} | alice | fail\n")
    # No handler registered (should fallback)
    monkeypatch.setattr(handler_registry, "_handlers", {{}})
    stub.process_messages()  # Should not raise

def test_registry_duplicate(monkeypatch):
    monkeypatch.setattr(handler_registry, "_handlers", {{}})
    dummy = DummyHandler()
    handler_registry.register("telegram", dummy.handle)
    with pytest.raises(HandlerRegistryError):
        handler_registry.register("telegram", dummy.handle)

def test_registry_unregister(monkeypatch):
    monkeypatch.setattr(handler_registry, "_handlers", {{}})
    dummy = DummyHandler()
    handler_registry.register("telegram", dummy.handle)
    handler_registry.unregister("telegram")
    with pytest.raises(HandlerRegistryError):
        handler_registry.call("telegram", MessageStub(platform="telegram", source="a", text="b"))

def test_fileio_errors(tmp_path):
    badfile = str(tmp_path / "doesnotexist" / "bad.txt")
    stub = TelegramWebhookStub(badfile, badfile)
    with pytest.raises(FileIOError):
        stub.receive_messages()

def test_message_stub_fields():
    msg = MessageStub(platform="telegram", source="test", text="hello")
    assert msg.message_id
    assert msg.platform == "telegram"
    assert msg.text == "hello"

def test_cli_simulate(monkeypatch, tmp_path):
    inbox = tmp_path / "cli_inbox.txt"
    outbox = tmp_path / "cli_outbox.txt"
    with open(inbox, "w") as f: f.write("")
    with open(outbox, "w") as f: f.write("")
    stub = TelegramWebhookStub(str(inbox), str(outbox))
    monkeypatch.setattr("builtins.input", lambda _: "Test Msg")
    stub.simulate_receive("tester")
    with open(inbox) as f:
        data = f.read()
    assert "Test Msg" in data

def test_message_id_uniqueness():
    ids = set()
    for _ in range(100):
        msg = MessageStub(platform="tg", source="s", text="t")
        assert msg.message_id not in ids
        ids.add(msg.message_id)
