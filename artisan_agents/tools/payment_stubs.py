# Local-only payment simulation stub system for desktop testing

import os
import sys
import time
import logging
import uuid
import threading
import asyncio
import random
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List
from pydantic import BaseModel, Field, ValidationError
from enum import Enum

PAYMENT_FILE = "payment_transactions.txt"
METRICS_FILE = "payment_metrics.log"

# --- Logging setup ---
logging.basicConfig(
    filename=METRICS_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def log_event(event_type: str, transaction_id: str, details: str):
    entry = f"{datetime.utcnow().isoformat()}Z | {event_type} | {transaction_id} | {details}"
    print(entry)
    logging.info(entry)

class PaymentStubError(Exception): pass
class PaymentProcessingError(PaymentStubError): pass
class RetryError(PaymentStubError): pass

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentMethod(Enum):
    UPI = "upi"
    RAZORPAY = "razorpay"
    WALLET = "wallet"
    CARD = "card"

class PaymentBase(BaseModel):
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    amount: float
    currency: str = "INR"
    payment_method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)

def simulate_payment_processing(payment: PaymentBase, success_rate: float = 0.9) -> PaymentStatus:
    """
    Simulate payment processing with configurable success rate.

    Args:
        payment: Payment object to process
        success_rate: Probability of successful payment (0.0 to 1.0)

    Returns:
        Final payment status
    """
    # Simulate processing time
    time.sleep(random.uniform(0.5, 2.0))

    # Simulate success/failure based on success rate
    if random.random() < success_rate:
        return PaymentStatus.COMPLETED
    else:
        return PaymentStatus.FAILED

def format_payment_message(order_id: str, amount: float, status: PaymentStatus) -> str:
    return f"Payment for Order {order_id}: ₹{amount:.2f} - Status: {status.value.upper()}"

def format_refund_message(order_id: str, amount: float, reason: str) -> str:
    return f"Refund for Order {order_id}: ₹{amount:.2f} - Reason: {reason}"

# Async scheduling logic
def schedule_delayed(fn, args=(), delay=0):
    def _delayed():
        time.sleep(delay)
        fn(*args)
    t = threading.Thread(target=_delayed)
    t.daemon = True
    t.start()

class PaymentStub:
    """
    Simulate payment processing for UPI, Razorpay, and other payment methods.
    Logs to local file and console for testing purposes.
    """
    def __init__(self, file=PAYMENT_FILE, retries=3, success_rate=0.9):
        self.file = file
        self.retries = retries
        self.success_rate = success_rate

    def process_payment(self, payment: PaymentBase) -> PaymentBase:
        """
        Process a payment transaction.

        Args:
            payment: Payment object to process

        Returns:
            Updated payment object with final status
        """
        payment.status = PaymentStatus.PROCESSING

        for attempt in range(self.retries):
            try:
                log_event("PAYMENT_ATTEMPT", payment.transaction_id,
                         f"Attempt {attempt + 1}/{self.retries} - Method: {payment.payment_method.value}")

                # Simulate payment processing
                final_status = simulate_payment_processing(payment, self.success_rate)

                payment.status = final_status

                # Log transaction to file
                with open(self.file, "a") as f:
                    f.write(f"{payment.transaction_id} | {payment.order_id} | {payment.amount} | {payment.payment_method.value} | {payment.status.value} | {payment.timestamp}\n")

                log_event("PAYMENT_COMPLETED", payment.transaction_id,
                         f"Final Status: {payment.status.value} - Amount: ₹{payment.amount}")

                print(f"[Stub] Processed payment: {payment.transaction_id} - Status: {payment.status.value}")
                return payment

            except Exception as e:
                log_event("PAYMENT_ERROR", payment.transaction_id, str(e))
                time.sleep(0.5)
                continue

        # All retries failed
        payment.status = PaymentStatus.FAILED
        raise RetryError(f"Failed to process payment after {self.retries} attempts")

    def refund_payment(self, transaction_id: str, amount: Optional[float] = None, reason: str = "Customer request") -> PaymentBase:
        """
        Process a payment refund.

        Args:
            transaction_id: Original transaction ID to refund
            amount: Refund amount (None for full refund)
            reason: Reason for refund

        Returns:
            New refund payment object
        """
        # Find original transaction
        original_payment = self._find_transaction(transaction_id)
        if not original_payment:
            raise PaymentProcessingError(f"Original transaction {transaction_id} not found")

        if original_payment.status != PaymentStatus.COMPLETED:
            raise PaymentProcessingError(f"Cannot refund non-completed payment: {original_payment.status.value}")

        # Calculate refund amount
        refund_amount = amount if amount is not None else original_payment.amount

        # Create refund payment
        refund_payment = PaymentBase(
            order_id=original_payment.order_id,
            amount=refund_amount,
            payment_method=original_payment.payment_method,
            status=PaymentStatus.PROCESSING,
            metadata={
                "refund_reason": reason,
                "original_transaction": transaction_id,
                "refund_type": "full" if amount is None else "partial"
            }
        )

        # Process refund
        refund_payment.status = PaymentStatus.COMPLETED

        # Log refund
        with open(self.file, "a") as f:
            f.write(f"{refund_payment.transaction_id} | REFUND | {original_payment.order_id} | {refund_amount} | REFUND | {refund_payment.status.value} | {refund_payment.timestamp}\n")

        log_event("REFUND_COMPLETED", refund_payment.transaction_id,
                 f"Refunded ₹{refund_amount} - Reason: {reason}")

        print(f"[Stub] Processed refund: {refund_payment.transaction_id} - Amount: ₹{refund_amount}")
        return refund_payment

    def _find_transaction(self, transaction_id: str) -> Optional[PaymentBase]:
        """
        Find a transaction by ID (simplified implementation).

        Args:
            transaction_id: Transaction ID to find

        Returns:
            Payment object if found, None otherwise
        """
        try:
            with open(self.file, "r") as f:
                for line in f:
                    parts = line.strip().split(" | ")
                    if parts and parts[0] == transaction_id:
                        return PaymentBase(
                            transaction_id=parts[0],
                            order_id=parts[1],
                            amount=float(parts[2]),
                            payment_method=PaymentMethod(parts[3]),
                            status=PaymentStatus(parts[4]),
                            timestamp=float(parts[5])
                        )
        except Exception as e:
            log_event("TRANSACTION_LOOKUP_ERROR", transaction_id, str(e))

        return None

    def schedule_payment(self, payment: PaymentBase, delay_sec: int):
        """
        Schedule a payment for later processing.

        Args:
            payment: Payment to schedule
            delay_sec: Delay in seconds
        """
        def delayed_process():
            self.process_payment(payment)

        schedule_delayed(delayed_process, (), delay_sec)
        log_event("PAYMENT_SCHEDULED", payment.transaction_id, f"Delay: {delay_sec}s")
        print(f"[Stub] Scheduled payment {payment.transaction_id} in {delay_sec}s")

class UPIPaymentStub(PaymentStub):
    """
    Specialized UPI payment processing stub.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.payment_method = PaymentMethod.UPI

    def process_payment(self, payment: PaymentBase) -> PaymentBase:
        """Process UPI payment with UPI-specific logic."""
        if payment.payment_method != PaymentMethod.UPI:
            payment.payment_method = PaymentMethod.UPI

        # Add UPI-specific metadata
        payment.metadata.update({
            "upi_id": f"user{random.randint(1000, 9999)}@upi",
            "merchant_vpa": "artisan.market@paytm"
        })

        return super().process_payment(payment)

class RazorpayPaymentStub(PaymentStub):
    """
    Specialized Razorpay payment processing stub.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.payment_method = PaymentMethod.RAZORPAY

    def process_payment(self, payment: PaymentBase) -> PaymentBase:
        """Process Razorpay payment with Razorpay-specific logic."""
        if payment.payment_method != PaymentMethod.RAZORPAY:
            payment.payment_method = PaymentMethod.RAZORPAY

        # Add Razorpay-specific metadata
        payment.metadata.update({
            "razorpay_order_id": f"order_{uuid.uuid4().hex[:10]}",
            "razorpay_payment_id": f"pay_{uuid.uuid4().hex[:10]}"
        })

        return super().process_payment(payment)

### CLI interface

def cli_main():
    import argparse
    parser = argparse.ArgumentParser(description="Local desktop payment stubs")
    parser.add_argument("--method", choices=["upi", "razorpay", "wallet"], required=True)
    parser.add_argument("--process", action="store_true", help="Process payment now")
    parser.add_argument("--refund", help="Refund transaction ID")
    parser.add_argument("--schedule", type=int, help="Schedule payment after delay (seconds)")
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--amount", type=float, required=True)
    parser.add_argument("--success-rate", type=float, default=0.9, help="Success rate (0.0 to 1.0)")
    parser.add_argument("--reason", default="Test payment", help="Payment reason/description")
    args = parser.parse_args()

    # Create appropriate payment stub
    if args.method == "upi":
        stub = UPIPaymentStub(success_rate=args.success_rate)
        payment_method = PaymentMethod.UPI
    elif args.method == "razorpay":
        stub = RazorpayPaymentStub(success_rate=args.success_rate)
        payment_method = PaymentMethod.RAZORPAY
    else:
        stub = PaymentStub(success_rate=args.success_rate)
        payment_method = PaymentMethod.WALLET

    if args.process:
        # Create and process payment
        payment = PaymentBase(
            order_id=args.order_id,
            amount=args.amount,
            payment_method=payment_method,
            metadata={"reason": args.reason}
        )
        result = stub.process_payment(payment)
        print(f"Payment processed: {result.transaction_id} - Status: {result.status.value}")

    elif args.refund:
        # Process refund
        try:
            refund = stub.refund_payment(args.refund, args.amount, args.reason)
            print(f"Refund processed: {refund.transaction_id} - Amount: ₹{refund.amount}")
        except PaymentProcessingError as e:
            print(f"Refund failed: {e}")

    elif args.schedule is not None:
        # Schedule payment
        payment = PaymentBase(
            order_id=args.order_id,
            amount=args.amount,
            payment_method=payment_method,
            metadata={"reason": args.reason}
        )
        stub.schedule_payment(payment, args.schedule)
        print(f"Payment scheduled: {payment.transaction_id}")

    else:
        parser.print_help()

if __name__ == "__main__":
    cli_main()

###########################################################
# PYTEST TESTS: Payment stub tests below
###########################################################

import pytest

@pytest.fixture
def payment_file(tmp_path):
    paymentf = tmp_path / "payments.txt"
    logf = tmp_path / "payment_metrics.txt"
    for f in [paymentf, logf]:
        f.write_text("")
    return str(paymentf), str(logf)

def test_payment_process_success(payment_file):
    paymentf, _ = payment_file
    stub = PaymentStub(paymentf, success_rate=1.0)
    payment = PaymentBase(
        order_id="ORD001",
        amount=100.0,
        payment_method=PaymentMethod.UPI
    )
    result = stub.process_payment(payment)

    assert result.status == PaymentStatus.COMPLETED
    assert result.transaction_id

    with open(paymentf) as f:
        lines = f.readlines()
    assert any(result.transaction_id in line for line in lines)

def test_payment_process_failure(payment_file):
    paymentf, _ = payment_file
    stub = PaymentStub(paymentf, success_rate=0.0)
    payment = PaymentBase(
        order_id="ORD002",
        amount=200.0,
        payment_method=PaymentMethod.RAZORPAY
    )
    result = stub.process_payment(payment)

    assert result.status == PaymentStatus.FAILED

def test_upi_payment_stub(payment_file):
    paymentf, _ = payment_file
    stub = UPIPaymentStub(paymentf, success_rate=1.0)
    payment = PaymentBase(
        order_id="ORD003",
        amount=150.0,
        payment_method=PaymentMethod.UPI
    )
    result = stub.process_payment(payment)

    assert result.status == PaymentStatus.COMPLETED
    assert result.payment_method == PaymentMethod.UPI
    assert "upi_id" in result.metadata

def test_razorpay_payment_stub(payment_file):
    paymentf, _ = payment_file
    stub = RazorpayPaymentStub(paymentf, success_rate=1.0)
    payment = PaymentBase(
        order_id="ORD004",
        amount=250.0,
        payment_method=PaymentMethod.RAZORPAY
    )
    result = stub.process_payment(payment)

    assert result.status == PaymentStatus.COMPLETED
    assert result.payment_method == PaymentMethod.RAZORPAY
    assert "razorpay_order_id" in result.metadata

def test_payment_refund(payment_file):
    paymentf, _ = payment_file
    stub = PaymentStub(paymentf, success_rate=1.0)

    # First create a successful payment
    payment = PaymentBase(
        order_id="ORD005",
        amount=100.0,
        payment_method=PaymentMethod.UPI
    )
    result = stub.process_payment(payment)
    assert result.status == PaymentStatus.COMPLETED

    # Now refund it
    refund = stub.refund_payment(result.transaction_id, reason="Test refund")
    assert refund.status == PaymentStatus.COMPLETED
    assert refund.amount == 100.0

def test_payment_refund_partial(payment_file):
    paymentf, _ = payment_file
    stub = PaymentStub(paymentf, success_rate=1.0)

    # First create a successful payment
    payment = PaymentBase(
        order_id="ORD006",
        amount=100.0,
        payment_method=PaymentMethod.UPI
    )
    result = stub.process_payment(payment)
    assert result.status == PaymentStatus.COMPLETED

    # Now partially refund it
    refund = stub.refund_payment(result.transaction_id, amount=50.0, reason="Partial refund")
    assert refund.status == PaymentStatus.COMPLETED
    assert refund.amount == 50.0

def test_refund_nonexistent_transaction(payment_file):
    paymentf, _ = payment_file
    stub = PaymentStub(paymentf, success_rate=1.0)

    with pytest.raises(PaymentProcessingError):
        stub.refund_payment("NONEXISTENT", reason="Test")

def test_schedule_payment(payment_file):
    paymentf, _ = payment_file
    stub = PaymentStub(paymentf, success_rate=1.0)
    payment = PaymentBase(
        order_id="ORD007",
        amount=75.0,
        payment_method=PaymentMethod.UPI
    )

    stub.schedule_payment(payment, 1)
    time.sleep(1.3)

    with open(paymentf) as f:
        data = f.read()
    assert payment.transaction_id in data

def test_format_payment_message():
    result = format_payment_message("ORD001", 100.0, PaymentStatus.COMPLETED)
    assert "ORD001" in result and "100.00" in result and "COMPLETED" in result

def test_format_refund_message():
    result = format_refund_message("ORD001", 50.0, "Customer request")
    assert "ORD001" in result and "50.00" in result and "Customer request" in result

def test_payment_base_fields():
    payment = PaymentBase(
        order_id="ORD001",
        amount=100.0,
        payment_method=PaymentMethod.UPI
    )
    assert payment.transaction_id
    assert payment.order_id == "ORD001"
    assert payment.amount == 100.0
    assert payment.status == PaymentStatus.PENDING
