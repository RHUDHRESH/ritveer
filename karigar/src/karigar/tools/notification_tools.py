"""
Notification Tools
Send emails, SMS, WhatsApp messages to artisans and customers
"""

import asyncio
import smtplib
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


class EmailNotificationTool(BaseTool):
    """Send REAL email notifications via SMTP"""

    def __init__(self, smtp_server: str = None, smtp_port: int = 587, smtp_user: str = None, smtp_password: str = None):
        super().__init__(
            name="email_notification",
            description="Send email notifications to artisans and customers",
            required_params=["recipient_email", "subject", "message"]
        )
        # Get from environment variables or use defaults
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("SMTP_FROM_EMAIL", self.smtp_user or "noreply@artisanhub.com")

    async def execute(self, **kwargs) -> ToolResult:
        """Send REAL email via SMTP"""
        start_time = datetime.utcnow()

        try:
            recipient_email = kwargs.get("recipient_email")
            subject = kwargs.get("subject")
            message = kwargs.get("message")
            template = kwargs.get("template", "default")
            html_content = kwargs.get("html_content", None)

            # Validate email
            if not self._validate_email(recipient_email):
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Invalid email address: {recipient_email}",
                    execution_time=execution_time,
                    timestamp=datetime.utcnow()
                )

            # Try real SMTP if credentials available
            if self.smtp_user and self.smtp_password:
                try:
                    self._send_via_smtp(recipient_email, subject, message, html_content)
                    status = "sent_via_smtp"
                except Exception as smtp_error:
                    logger.warning(f"SMTP sending failed, logging instead: {smtp_error}")
                    status = "logged"
                    self._log_email(recipient_email, subject, message)
            else:
                # Log email if no SMTP credentials
                status = "logged"
                self._log_email(recipient_email, subject, message)
                logger.info(f"Email logged (no SMTP configured): {recipient_email}")

            email_data = {
                "to": recipient_email,
                "subject": subject,
                "body": message,
                "template": template,
                "sent_at": datetime.utcnow().isoformat(),
                "status": status,
                "smtp_server": self.smtp_server if status == "sent_via_smtp" else "not_configured"
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=email_data,
                message=f"Email {status} to {recipient_email}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"recipient": recipient_email, "status": status}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Email sending error: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                message=f"Email sending failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )

    def _send_via_smtp(self, to_email: str, subject: str, message: str, html_content: str = None):
        """Send REAL email via SMTP"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email

        # Plain text version
        text_part = MIMEText(message, "plain")
        msg.attach(text_part)

        # HTML version if provided
        if html_content:
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

        # Send via SMTP
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_email, to_email, msg.as_string())

        logger.info(f"Email sent via SMTP to {to_email}")

    def _log_email(self, to_email: str, subject: str, message: str):
        """Log email instead of sending (fallback)"""
        logger.info(f"[EMAIL LOG] To: {to_email}, Subject: {subject}, Body: {message[:100]}...")

    def _validate_email(self, email: str) -> bool:
        """Simple email validation"""
        return "@" in email and "." in email.split("@")[1]


class SMSNotificationTool(BaseTool):
    """Send REAL SMS notifications via Twilio"""

    def __init__(self, twilio_account_sid: str = None, twilio_auth_token: str = None, twilio_phone: str = None):
        super().__init__(
            name="sms_notification",
            description="Send SMS notifications to phone numbers",
            required_params=["phone_number", "message"]
        )
        # Get from environment variables
        self.twilio_account_sid = twilio_account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = twilio_auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone = twilio_phone or os.getenv("TWILIO_PHONE_NUMBER")

    async def execute(self, **kwargs) -> ToolResult:
        """Send REAL SMS via Twilio"""
        start_time = datetime.utcnow()

        try:
            phone_number = kwargs.get("phone_number")
            message = kwargs.get("message")

            # Validate phone number format
            if not self._validate_phone(phone_number):
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Invalid phone number: {phone_number}",
                    execution_time=execution_time,
                    timestamp=datetime.utcnow()
                )

            # Try real Twilio if credentials available
            if self.twilio_account_sid and self.twilio_auth_token and TWILIO_AVAILABLE:
                try:
                    self._send_via_twilio(phone_number, message)
                    status = "sent_via_twilio"
                except Exception as twilio_error:
                    logger.warning(f"Twilio sending failed, logging instead: {twilio_error}")
                    status = "logged"
                    self._log_sms(phone_number, message)
            else:
                # Log SMS if no Twilio credentials
                status = "logged"
                self._log_sms(phone_number, message)
                logger.info(f"SMS logged (no Twilio configured): {phone_number}")

            sms_data = {
                "phone": phone_number,
                "message": message,
                "length": len(message),
                "sent_at": datetime.utcnow().isoformat(),
                "status": status,
                "provider": "twilio" if status == "sent_via_twilio" else "not_configured"
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=sms_data,
                message=f"SMS {status} to {phone_number}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"phone": phone_number, "status": status}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"SMS sending error: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                message=f"SMS sending failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )

    def _send_via_twilio(self, phone_number: str, message: str):
        """Send REAL SMS via Twilio"""
        if not TWILIO_AVAILABLE:
            raise ImportError("Twilio not installed. Install with: pip install twilio")

        client = Client(self.twilio_account_sid, self.twilio_auth_token)
        msg = client.messages.create(
            body=message,
            from_=self.twilio_phone,
            to=phone_number
        )
        logger.info(f"SMS sent via Twilio to {phone_number}, SID: {msg.sid}")

    def _log_sms(self, phone_number: str, message: str):
        """Log SMS instead of sending (fallback)"""
        logger.info(f"[SMS LOG] To: {phone_number}, Message: {message}")

    def _validate_phone(self, phone: str) -> bool:
        """Basic phone validation"""
        # Should contain digits and be at least 10 chars
        digits = "".join(c for c in phone if c.isdigit())
        return len(digits) >= 10


class WhatsAppNotificationTool(BaseTool):
    """Send WhatsApp notifications via Twilio or WhatsApp Business API"""

    def __init__(self, twilio_account_sid: str = None, twilio_auth_token: str = None, twilio_whatsapp: str = None):
        super().__init__(
            name="whatsapp_notification",
            description="Send WhatsApp messages to contacts",
            required_params=["phone_number", "message"]
        )
        # Get from environment variables
        self.twilio_account_sid = twilio_account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = twilio_auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_whatsapp = twilio_whatsapp or os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

    async def execute(self, **kwargs) -> ToolResult:
        """Send WhatsApp message"""
        start_time = datetime.utcnow()

        try:
            phone_number = kwargs.get("phone_number")
            message = kwargs.get("message")
            message_type = kwargs.get("message_type", "text")

            # Format phone for WhatsApp (add whatsapp: prefix)
            whatsapp_phone = f"whatsapp:{phone_number}" if not phone_number.startswith("whatsapp:") else phone_number

            # Try real Twilio WhatsApp if credentials available
            if self.twilio_account_sid and self.twilio_auth_token and TWILIO_AVAILABLE:
                try:
                    self._send_via_twilio_whatsapp(whatsapp_phone, message)
                    status = "sent_via_whatsapp"
                except Exception as whatsapp_error:
                    logger.warning(f"WhatsApp sending failed, logging instead: {whatsapp_error}")
                    status = "logged"
                    self._log_whatsapp(phone_number, message)
            else:
                # Log message if no credentials
                status = "logged"
                self._log_whatsapp(phone_number, message)
                logger.info(f"WhatsApp logged (no Twilio configured): {phone_number}")

            whatsapp_data = {
                "phone": phone_number,
                "message": message,
                "type": message_type,
                "sent_at": datetime.utcnow().isoformat(),
                "status": status,
                "provider": "twilio_whatsapp" if status == "sent_via_whatsapp" else "not_configured"
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=whatsapp_data,
                message=f"WhatsApp message {status} to {phone_number}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"phone": phone_number, "status": status}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"WhatsApp sending error: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                message=f"WhatsApp sending failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )

    def _send_via_twilio_whatsapp(self, whatsapp_phone: str, message: str):
        """Send via Twilio WhatsApp API"""
        if not TWILIO_AVAILABLE:
            raise ImportError("Twilio not installed. Install with: pip install twilio")

        client = Client(self.twilio_account_sid, self.twilio_auth_token)
        msg = client.messages.create(
            body=message,
            from_=self.twilio_whatsapp,
            to=whatsapp_phone
        )
        logger.info(f"WhatsApp sent via Twilio to {whatsapp_phone}, SID: {msg.sid}")

    def _log_whatsapp(self, phone_number: str, message: str):
        """Log WhatsApp message instead of sending"""
        logger.info(f"[WHATSAPP LOG] To: {phone_number}, Message: {message}")


class PushNotificationTool(BaseTool):
    """Send REAL push notifications via Firebase Cloud Messaging"""

    def __init__(self, firebase_credentials_path: str = None):
        super().__init__(
            name="push_notification",
            description="Send push notifications to mobile apps",
            required_params=["user_id", "title", "message"]
        )
        self.firebase_credentials_path = firebase_credentials_path or os.getenv("FIREBASE_CREDENTIALS_PATH")
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Initialize Firebase if credentials available"""
        try:
            if self.firebase_credentials_path and FIREBASE_AVAILABLE:
                if not firebase_admin._apps:
                    creds = credentials.Certificate(self.firebase_credentials_path)
                    firebase_admin.initialize_app(creds)
                    logger.info("Firebase initialized successfully")
        except Exception as e:
            logger.warning(f"Firebase initialization failed: {e}")

    async def execute(self, **kwargs) -> ToolResult:
        """Send REAL push notification"""
        start_time = datetime.utcnow()

        try:
            user_id = kwargs.get("user_id")
            title = kwargs.get("title")
            message_text = kwargs.get("message")
            action = kwargs.get("action", "open_app")
            device_token = kwargs.get("device_token")  # FCM device token

            # Try Firebase if available and credentials exist
            if device_token and FIREBASE_AVAILABLE and self.firebase_credentials_path:
                try:
                    self._send_via_firebase(device_token, title, message_text)
                    status = "sent_via_firebase"
                except Exception as firebase_error:
                    logger.warning(f"Firebase sending failed, logging instead: {firebase_error}")
                    status = "logged"
                    self._log_push(user_id, title, message_text)
            else:
                # Log push notification if no Firebase
                status = "logged"
                self._log_push(user_id, title, message_text)
                if not device_token:
                    logger.info(f"Push notification queued (no device_token provided)")
                else:
                    logger.info(f"Push notification logged (no Firebase configured): {user_id}")

            push_data = {
                "user_id": user_id,
                "title": title,
                "message": message_text,
                "action": action,
                "sent_at": datetime.utcnow().isoformat(),
                "status": status,
                "provider": "firebase" if status == "sent_via_firebase" else "not_configured"
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=push_data,
                message=f"Push notification {status} to user {user_id}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"user_id": user_id, "status": status}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Push notification error: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                message=f"Push notification failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )

    def _send_via_firebase(self, device_token: str, title: str, body: str):
        """Send via Firebase Cloud Messaging"""
        if not FIREBASE_AVAILABLE:
            raise ImportError("Firebase not installed. Install with: pip install firebase-admin")

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            token=device_token
        )
        response = messaging.send(message)
        logger.info(f"Push notification sent via Firebase, ID: {response}")

    def _log_push(self, user_id: str, title: str, message: str):
        """Log push notification instead of sending"""
        logger.info(f"[PUSH LOG] User: {user_id}, Title: {title}, Message: {message}")


class NotificationSchedulerTool(BaseTool):
    """Schedule notifications for later"""

    def __init__(self):
        super().__init__(
            name="notification_scheduler",
            description="Schedule notifications for later delivery",
            required_params=["recipient", "message", "scheduled_time"]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Schedule notification"""
        start_time = datetime.utcnow()

        try:
            recipient = kwargs.get("recipient")
            message = kwargs.get("message")
            scheduled_time = kwargs.get("scheduled_time")
            notification_type = kwargs.get("type", "email")

            # Mock scheduling
            scheduled_notification = {
                "notification_id": f"notif_{datetime.utcnow().timestamp()}",
                "recipient": recipient,
                "message": message,
                "type": notification_type,
                "scheduled_for": scheduled_time,
                "status": "scheduled"
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=scheduled_notification,
                message=f"Notification scheduled for {recipient}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"notification_id": scheduled_notification["notification_id"]}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Notification scheduling failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


class NotificationTemplateTool(BaseTool):
    """Get notification templates"""

    def __init__(self):
        super().__init__(
            name="notification_template",
            description="Get predefined notification templates",
            required_params=["template_name"]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Get template"""
        start_time = datetime.utcnow()

        try:
            template_name = kwargs.get("template_name")

            templates = {
                "order_confirmation": {
                    "subject": "Order Confirmed",
                    "body": "Your order has been confirmed. Order ID: {order_id}",
                    "sms": "Order {order_id} confirmed. Track here: {link}"
                },
                "production_started": {
                    "subject": "Production Started",
                    "body": "Production for your order has started",
                    "sms": "Production started for order {order_id}"
                },
                "ready_for_shipping": {
                    "subject": "Ready for Shipping",
                    "body": "Your order is ready for shipping",
                    "sms": "Order {order_id} ready for shipment"
                },
                "payment_due": {
                    "subject": "Payment Due",
                    "body": "Payment due for order {order_id}",
                    "sms": "Payment due: {amount} for order {order_id}"
                }
            }

            template = templates.get(template_name, {})

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=template,
                message=f"Template '{template_name}' retrieved",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"template": template_name}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Template retrieval failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


# Tool instances
email_notification = EmailNotificationTool()
sms_notification = SMSNotificationTool()
whatsapp_notification = WhatsAppNotificationTool()
push_notification = PushNotificationTool()
notification_scheduler = NotificationSchedulerTool()
notification_template = NotificationTemplateTool()
