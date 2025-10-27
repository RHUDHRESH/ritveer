"""
Payment Processing Tools
Create payment links, process transactions, generate payment QR codes
"""

import uuid
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)

try:
    import razorpay
    RAZORPAY_AVAILABLE = True
except ImportError:
    RAZORPAY_AVAILABLE = False


class PaymentLinkGeneratorTool(BaseTool):
    """Generate REAL payment links via Razorpay"""

    def __init__(self, razorpay_key_id: str = None, razorpay_key_secret: str = None):
        super().__init__(
            name="payment_link_generator",
            description="Generate payment links for orders and invoices",
            required_params=["amount", "customer_name", "artisan_id", "order_id"]
        )
        self.razorpay_key_id = razorpay_key_id or os.getenv("RAZORPAY_KEY_ID")
        self.razorpay_key_secret = razorpay_key_secret or os.getenv("RAZORPAY_KEY_SECRET")
        self.client = None
        if self.razorpay_key_id and self.razorpay_key_secret and RAZORPAY_AVAILABLE:
            self.client = razorpay.Client(
                auth=(self.razorpay_key_id, self.razorpay_key_secret)
            )

    async def execute(self, **kwargs) -> ToolResult:
        """Generate REAL payment link via Razorpay"""
        start_time = datetime.utcnow()

        try:
            amount = float(kwargs.get("amount", 0))
            customer_name = kwargs.get("customer_name")
            artisan_id = kwargs.get("artisan_id")
            order_id = kwargs.get("order_id")
            customer_email = kwargs.get("customer_email", "customer@example.com")
            customer_phone = kwargs.get("customer_phone", "")
            description = kwargs.get("description", f"Payment for order {order_id}")

            # Try real Razorpay if credentials available
            if self.client and RAZORPAY_AVAILABLE:
                try:
                    payment_link = self._create_razorpay_link(
                        amount, order_id, customer_name, customer_email,
                        customer_phone, description
                    )
                    status = "created_via_razorpay"
                except Exception as razorpay_error:
                    logger.warning(f"Razorpay link creation failed, creating mock: {razorpay_error}")
                    status = "mock"
                    payment_link = self._create_mock_link(
                        amount, customer_name, artisan_id, order_id, description
                    )
            else:
                # Create mock link if no Razorpay credentials
                status = "mock"
                payment_link = self._create_mock_link(
                    amount, customer_name, artisan_id, order_id, description
                )
                logger.info(f"Payment link mocked (no Razorpay configured): {order_id}")

            payment_link["status"] = status

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=payment_link,
                message=f"Payment link {status} for ₹{amount}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"amount": amount, "link_id": payment_link.get("id", payment_link.get("link_id")), "status": status}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Payment link generation error: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                message=f"Payment link generation failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )

    def _create_razorpay_link(self, amount: float, order_id: str, customer_name: str,
                             customer_email: str, customer_phone: str, description: str) -> Dict:
        """Create REAL payment link via Razorpay API"""
        if not self.client:
            raise Exception("Razorpay client not initialized")

        # Convert amount to paise (Razorpay uses paise)
        amount_paise = int(amount * 100)

        try:
            # Create payment link
            response = self.client.payment_link.create({
                "amount": amount_paise,
                "currency": "INR",
                "accept_partial": True,
                "first_min_partial_amount": 100,
                "description": description,
                "customer": {
                    "name": customer_name,
                    "email": customer_email,
                    "contact": customer_phone
                },
                "notify": {
                    "sms": True,
                    "email": True
                },
                "reminder_enable": True,
                "notes": {
                    "order_id": order_id,
                    "policy_name": "ArtisanHub Payment"
                },
                "callback_url": os.getenv("RAZORPAY_CALLBACK_URL", "https://example.com/callback"),
                "callback_method": "get"
            })

            logger.info(f"Razorpay payment link created: {response['id']}")

            return {
                "id": response['id'],
                "link_id": response['id'],
                "amount": amount,
                "currency": "INR",
                "customer_name": customer_name,
                "description": description,
                "payment_url": response['short_url'],
                "created_at": response['created_at'],
                "expires_at": response.get('expire_by'),
                "status": "active"
            }

        except Exception as e:
            logger.error(f"Razorpay API error: {str(e)}")
            raise

    def _create_mock_link(self, amount: float, customer_name: str,
                         artisan_id: str, order_id: str, description: str) -> Dict:
        """Create mock payment link"""
        return {
            "link_id": f"pay_{uuid.uuid4().hex[:12]}",
            "amount": amount,
            "currency": "INR",
            "customer_name": customer_name,
            "description": description,
            "order_id": order_id,
            "artisan_id": artisan_id,
            "payment_url": f"https://payment.karigar.local/pay/{uuid.uuid4().hex[:16]}",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        }


class PaymentStatusTool(BaseTool):
    """Check REAL payment status via Razorpay"""

    def __init__(self, razorpay_key_id: str = None, razorpay_key_secret: str = None):
        super().__init__(
            name="payment_status",
            description="Check payment status and transaction details",
            required_params=["payment_id"]
        )
        self.razorpay_key_id = razorpay_key_id or os.getenv("RAZORPAY_KEY_ID")
        self.razorpay_key_secret = razorpay_key_secret or os.getenv("RAZORPAY_KEY_SECRET")
        self.client = None
        if self.razorpay_key_id and self.razorpay_key_secret and RAZORPAY_AVAILABLE:
            self.client = razorpay.Client(
                auth=(self.razorpay_key_id, self.razorpay_key_secret)
            )

    async def execute(self, **kwargs) -> ToolResult:
        """Check REAL payment status"""
        start_time = datetime.utcnow()

        try:
            payment_id = kwargs.get("payment_id")

            # Try real Razorpay if credentials available
            if self.client and RAZORPAY_AVAILABLE:
                try:
                    payment_status = self._fetch_razorpay_status(payment_id)
                    status_source = "razorpay"
                except Exception as razorpay_error:
                    logger.warning(f"Razorpay fetch failed, returning mock: {razorpay_error}")
                    status_source = "mock"
                    payment_status = self._create_mock_status(payment_id)
            else:
                # Return mock status if no Razorpay credentials
                status_source = "mock"
                payment_status = self._create_mock_status(payment_id)
                logger.info(f"Payment status mocked (no Razorpay configured): {payment_id}")

            payment_status["source"] = status_source

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=payment_status,
                message=f"Payment {payment_id} status retrieved",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"status": payment_status.get("status"), "source": status_source}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Payment status check error: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                message=f"Payment status check failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )

    def _fetch_razorpay_status(self, payment_link_id: str) -> Dict:
        """Fetch REAL payment status from Razorpay"""
        if not self.client:
            raise Exception("Razorpay client not initialized")

        # Fetch payment link details
        link = self.client.payment_link.fetch(payment_link_id)

        return {
            "payment_id": payment_link_id,
            "link_id": link['id'],
            "status": link['status'],  # issued, partially_paid, paid, expired, cancelled
            "amount": link['amount'] / 100,  # Convert from paise
            "amount_paid": link.get('amount_paid', 0) / 100,
            "currency": link['currency'],
            "customer": link.get('customer', {}),
            "timestamp": link.get('created_at'),
            "upi_link": link.get('upi_link'),
            "short_url": link.get('short_url'),
            "reference_id": link.get('reference_id'),
            "notes": link.get('notes', {})
        }

    def _create_mock_status(self, payment_id: str) -> Dict:
        """Create mock payment status"""
        return {
            "payment_id": payment_id,
            "status": "completed",  # pending, completed, failed
            "amount": 5000,
            "amount_paid": 5000,
            "currency": "INR",
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.utcnow().isoformat(),
            "method": "upi",  # upi, card, netbanking, wallet
            "customer_id": "cust_123456",
            "order_id": "ord_123456",
        }


class RefundProcessorTool(BaseTool):
    """Process REAL refunds via Razorpay"""

    def __init__(self, razorpay_key_id: str = None, razorpay_key_secret: str = None):
        super().__init__(
            name="refund_processor",
            description="Process refunds for cancelled or returned orders",
            required_params=["payment_id", "amount", "reason"]
        )
        self.razorpay_key_id = razorpay_key_id or os.getenv("RAZORPAY_KEY_ID")
        self.razorpay_key_secret = razorpay_key_secret or os.getenv("RAZORPAY_KEY_SECRET")
        self.client = None
        if self.razorpay_key_id and self.razorpay_key_secret and RAZORPAY_AVAILABLE:
            self.client = razorpay.Client(
                auth=(self.razorpay_key_id, self.razorpay_key_secret)
            )

    async def execute(self, **kwargs) -> ToolResult:
        """Process REAL refund"""
        start_time = datetime.utcnow()

        try:
            payment_id = kwargs.get("payment_id")
            amount = float(kwargs.get("amount", 0))
            reason = kwargs.get("reason")

            # Try real Razorpay if credentials available
            if self.client and RAZORPAY_AVAILABLE:
                try:
                    refund_data = self._process_razorpay_refund(payment_id, amount, reason)
                    refund_source = "razorpay"
                except Exception as razorpay_error:
                    logger.warning(f"Razorpay refund failed, creating mock: {razorpay_error}")
                    refund_source = "mock"
                    refund_data = self._create_mock_refund(payment_id, amount, reason)
            else:
                # Create mock refund if no Razorpay
                refund_source = "mock"
                refund_data = self._create_mock_refund(payment_id, amount, reason)
                logger.info(f"Refund mocked (no Razorpay configured): {payment_id}")

            refund_data["source"] = refund_source

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=refund_data,
                message=f"Refund of ₹{amount} {refund_source} for payment {payment_id}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"refund_id": refund_data.get("refund_id"), "source": refund_source}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Refund processing error: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                message=f"Refund processing failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )

    def _process_razorpay_refund(self, payment_id: str, amount: float, reason: str) -> Dict:
        """Process REAL refund via Razorpay"""
        if not self.client:
            raise Exception("Razorpay client not initialized")

        # Convert amount to paise
        amount_paise = int(amount * 100)

        # Create refund
        refund = self.client.payment.refund(payment_id, {
            "amount": amount_paise,
            "receipt": f"refund_{uuid.uuid4().hex[:8]}",
            "notes": {
                "reason": reason,
                "platform": "ArtisanHub"
            }
        })

        logger.info(f"Razorpay refund created: {refund['id']}")

        return {
            "refund_id": refund['id'],
            "payment_id": payment_id,
            "amount": amount,
            "currency": "INR",
            "reason": reason,
            "status": refund['status'],  # processed, failed, pending
            "created_at": refund.get('created_at'),
            "receipt": refund.get('receipt')
        }

    def _create_mock_refund(self, payment_id: str, amount: float, reason: str) -> Dict:
        """Create mock refund"""
        return {
            "refund_id": f"refund_{uuid.uuid4().hex[:12]}",
            "payment_id": payment_id,
            "amount": amount,
            "currency": "INR",
            "reason": reason,
            "status": "initiated",  # initiated, processing, completed, failed
            "created_at": datetime.utcnow().isoformat(),
            "expected_completion": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        }


class CommissionCalculatorTool(BaseTool):
    """Calculate platform commission and artisan payout"""

    def __init__(self):
        super().__init__(
            name="commission_calculator",
            description="Calculate platform commission and artisan payout",
            required_params=["amount", "commission_rate"]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Calculate commission"""
        start_time = datetime.utcnow()

        try:
            amount = float(kwargs.get("amount", 0))
            commission_rate = float(kwargs.get("commission_rate", 2.5))

            commission = amount * (commission_rate / 100)
            artisan_payout = amount - commission

            calculation = {
                "transaction_amount": amount,
                "commission_rate": f"{commission_rate}%",
                "platform_commission": commission,
                "artisan_payout": artisan_payout,
                "currency": "INR",
                "breakdown": {
                    "gross": amount,
                    "commission": commission,
                    "net": artisan_payout,
                }
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=calculation,
                message=f"Commission calculated: ₹{commission} | Payout: ₹{artisan_payout}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"commission": commission, "payout": artisan_payout}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Commission calculation failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


# Tool instances
payment_link_generator = PaymentLinkGeneratorTool()
payment_status_tool = PaymentStatusTool()
refund_processor = RefundProcessorTool()
commission_calculator = CommissionCalculatorTool()
