"""
KARIGAR Tools Module
Central registry of all tools available to agents
"""

from .base_tool import BaseTool, ToolResult, ToolRegistry, tool_registry
from .supplier_tools import (
    SupplierSearchTool,
    QuoteGeneratorTool,
    SupplierValidationTool,
    supplier_search_tool,
    quote_generator_tool,
    supplier_validation_tool,
)
from .document_tools import (
    PDFGeneratorTool,
    QRCodeGeneratorTool,
    ReportGeneratorTool,
    pdf_generator_tool,
    qrcode_generator_tool,
    report_generator_tool,
)
from .payment_tools import (
    PaymentLinkGeneratorTool,
    PaymentStatusTool,
    RefundProcessorTool,
    CommissionCalculatorTool,
    payment_link_generator,
    payment_status_tool,
    refund_processor,
    commission_calculator,
)
from .research_tools import (
    WebScraperTool,
    MarketResearchTool,
    CompetitorAnalysisTool,
    TrendDetectionTool,
    web_scraper,
    market_research,
    competitor_analysis,
    trend_detection,
)
from .notification_tools import (
    EmailNotificationTool,
    SMSNotificationTool,
    WhatsAppNotificationTool,
    PushNotificationTool,
    NotificationSchedulerTool,
    NotificationTemplateTool,
    email_notification,
    sms_notification,
    whatsapp_notification,
    push_notification,
    notification_scheduler,
    notification_template,
)


def register_all_tools():
    """Register all tools in the global registry"""
    # Supplier Tools
    tool_registry.register(supplier_search_tool)
    tool_registry.register(quote_generator_tool)
    tool_registry.register(supplier_validation_tool)

    # Document Tools
    tool_registry.register(pdf_generator_tool)
    tool_registry.register(qrcode_generator_tool)
    tool_registry.register(report_generator_tool)

    # Payment Tools
    tool_registry.register(payment_link_generator)
    tool_registry.register(payment_status_tool)
    tool_registry.register(refund_processor)
    tool_registry.register(commission_calculator)

    # Research Tools
    tool_registry.register(web_scraper)
    tool_registry.register(market_research)
    tool_registry.register(competitor_analysis)
    tool_registry.register(trend_detection)

    # Notification Tools
    tool_registry.register(email_notification)
    tool_registry.register(sms_notification)
    tool_registry.register(whatsapp_notification)
    tool_registry.register(push_notification)
    tool_registry.register(notification_scheduler)
    tool_registry.register(notification_template)


# Auto-register all tools on import
register_all_tools()

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "tool_registry",
    # Supplier Tools
    "SupplierSearchTool",
    "QuoteGeneratorTool",
    "SupplierValidationTool",
    "supplier_search_tool",
    "quote_generator_tool",
    "supplier_validation_tool",
    # Document Tools
    "PDFGeneratorTool",
    "QRCodeGeneratorTool",
    "ReportGeneratorTool",
    "pdf_generator_tool",
    "qrcode_generator_tool",
    "report_generator_tool",
    # Payment Tools
    "PaymentLinkGeneratorTool",
    "PaymentStatusTool",
    "RefundProcessorTool",
    "CommissionCalculatorTool",
    "payment_link_generator",
    "payment_status_tool",
    "refund_processor",
    "commission_calculator",
    # Research Tools
    "WebScraperTool",
    "MarketResearchTool",
    "CompetitorAnalysisTool",
    "TrendDetectionTool",
    "web_scraper",
    "market_research",
    "competitor_analysis",
    "trend_detection",
    # Function
    "register_all_tools",
]
