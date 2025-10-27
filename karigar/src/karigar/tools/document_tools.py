"""
Document Generation Tools
Generate PDFs, invoices, quotes, proforma invoices
"""

import io
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from .base_tool import BaseTool, ToolResult

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import qrcode
    from PIL import Image
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


class PDFGeneratorTool(BaseTool):
    """Generate REAL PDF documents (invoices, quotes, proforma invoices)"""

    def __init__(self, output_dir: str = "./data/pdfs"):
        super().__init__(
            name="pdf_generator",
            description="Generate PDF documents like invoices, quotes, proforma invoices",
            required_params=["document_type", "artisan_name", "customer_name", "items"]
        )
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    async def execute(self, **kwargs) -> ToolResult:
        """Generate REAL PDF"""
        start_time = datetime.utcnow()

        try:
            document_type = kwargs.get("document_type")  # invoice, quote, proforma
            artisan_name = kwargs.get("artisan_name")
            customer_name = kwargs.get("customer_name")
            items = kwargs.get("items", [])
            amount = kwargs.get("amount", 0)
            gst_rate = kwargs.get("gst_rate", 18)

            if not REPORTLAB_AVAILABLE:
                return self._fallback_pdf(document_type, artisan_name, customer_name, start_time)

            # REAL PDF generation with ReportLab
            filename = f"{document_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(self.output_dir, filename)

            # Create PDF
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()

            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=30,
            )
            elements.append(Paragraph(f"{document_type.upper()}", title_style))
            elements.append(Spacer(1, 0.3*inch))

            # Header info
            header_data = [
                ["From:", f"{artisan_name}"],
                ["To:", f"{customer_name}"],
                ["Date:", datetime.now().strftime("%Y-%m-%d")],
                ["Document Type:", document_type],
            ]
            header_table = Table(header_data, colWidths=[1.5*inch, 4*inch])
            header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 0.3*inch))

            # Items table
            items_data = [["Item", "Quantity", "Unit Price", "Amount"]]
            total_before_tax = 0
            for item in items:
                qty = item.get("quantity", 1)
                price = item.get("price", 0)
                item_total = qty * price
                total_before_tax += item_total
                items_data.append([
                    item.get("name", "Item"),
                    str(qty),
                    f"₹{price:,.2f}",
                    f"₹{item_total:,.2f}"
                ])

            items_data.append(["", "", "", ""])
            gst_amount = total_before_tax * (gst_rate / 100)
            total_amount = total_before_tax + gst_amount
            items_data.append(["", "", "Subtotal:", f"₹{total_before_tax:,.2f}"])
            items_data.append(["", "", f"GST ({gst_rate}%):", f"₹{gst_amount:,.2f}"])
            items_data.append(["", "", "TOTAL:", f"₹{total_amount:,.2f}"])

            items_table = Table(items_data, colWidths=[2*inch, 1*inch, 1.5*inch, 1.5*inch])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, -3), (-1, -1), colors.beige),
                ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
                ('TOPPADDING', (0, -3), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(items_table)
            elements.append(Spacer(1, 0.3*inch))

            # Footer
            footer_text = "Thank you for your business!"
            elements.append(Paragraph(footer_text, styles['Normal']))

            # Build PDF
            doc.build(elements)

            # Get file size
            file_size = os.path.getsize(filepath)

            pdf_content = {
                "filename": filename,
                "filepath": filepath,
                "url": f"/pdfs/{filename}",
                "document_type": document_type,
                "artisan": artisan_name,
                "customer": customer_name,
                "items_count": len(items),
                "amount_before_tax": total_before_tax if len(items) > 0 else amount,
                "gst_amount": gst_amount if len(items) > 0 else amount * (gst_rate / 100),
                "total_amount": total_amount if len(items) > 0 else amount * (1 + gst_rate / 100),
                "file_size": file_size,
                "generated_at": datetime.utcnow().isoformat(),
                "status": "ready_for_download"
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=pdf_content,
                message=f"{document_type.title()} PDF generated successfully at {filepath}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"filename": filename, "size": f"{file_size} bytes"}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"PDF generation failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )

    def _fallback_pdf(self, doc_type: str, artisan: str, customer: str, start_time: datetime) -> ToolResult:
        """Fallback when ReportLab not available"""
        filename = f"{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(self.output_dir, filename)

        # Create text version
        with open(filepath, 'w') as f:
            f.write(f"{doc_type.upper()}\n")
            f.write(f"From: {artisan}\n")
            f.write(f"To: {customer}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write("\nNote: Text version created. Install reportlab for PDF generation.\n")

        execution_time = (datetime.utcnow() - start_time).total_seconds()

        return ToolResult(
            success=True,
            data={"filename": filename, "filepath": filepath, "format": "text"},
            message=f"Document generated as text file (install reportlab for PDF)",
            execution_time=execution_time,
            timestamp=datetime.utcnow()
        )


class QRCodeGeneratorTool(BaseTool):
    """Generate REAL QR codes for payment links and product info"""

    def __init__(self, output_dir: str = "./data/qrcodes"):
        super().__init__(
            name="qrcode_generator",
            description="Generate QR codes for payment links and product info",
            required_params=["data", "qr_type"]
        )
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    async def execute(self, **kwargs) -> ToolResult:
        """Generate REAL QR code image"""
        start_time = datetime.utcnow()

        try:
            data = kwargs.get("data")
            qr_type = kwargs.get("qr_type")  # payment, product, contact
            size = kwargs.get("size", 10)  # box size in pixels

            if not QRCODE_AVAILABLE:
                return self._fallback_qrcode(data, qr_type, start_time)

            # REAL QR code generation with qrcode library
            qr_code_id = f"qr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            filename = f"{qr_code_id}_{qr_type}.png"
            filepath = os.path.join(self.output_dir, filename)

            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=size,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            # Generate image
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(filepath)

            # Get file size
            file_size = os.path.getsize(filepath)

            qr_data = {
                "qr_code_id": qr_code_id,
                "qr_type": qr_type,
                "encoded_data": data,
                "filename": filename,
                "filepath": filepath,
                "url": f"/qrcodes/{filename}",
                "size": f"{size}x{size}",
                "format": "PNG",
                "file_size": file_size,
                "generated_at": datetime.utcnow().isoformat(),
                "status": "ready_for_download"
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=qr_data,
                message=f"QR code generated for {qr_type} at {filepath}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"qr_type": qr_type, "filename": filename, "size": f"{file_size} bytes"}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"QR code generation failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )

    def _fallback_qrcode(self, data: str, qr_type: str, start_time: datetime) -> ToolResult:
        """Fallback when qrcode/PIL not available"""
        qr_code_id = f"qr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        filename = f"{qr_code_id}_{qr_type}.txt"
        filepath = os.path.join(self.output_dir, filename)

        # Create text representation
        with open(filepath, 'w') as f:
            f.write(f"QR CODE PLACEHOLDER\n")
            f.write(f"Type: {qr_type}\n")
            f.write(f"Data: {data}\n")
            f.write(f"ID: {qr_code_id}\n")
            f.write(f"\nNote: Install 'qrcode' and 'pillow' for PNG generation\n")

        execution_time = (datetime.utcnow() - start_time).total_seconds()

        return ToolResult(
            success=True,
            data={"filename": filename, "filepath": filepath, "format": "text", "qr_code_id": qr_code_id},
            message=f"QR code generated as text file (install qrcode and pillow for PNG)",
            execution_time=execution_time,
            timestamp=datetime.utcnow()
        )


class ReportGeneratorTool(BaseTool):
    """Generate business reports (monthly, quarterly, annual)"""

    def __init__(self):
        super().__init__(
            name="report_generator",
            description="Generate business reports (income, production, sales)",
            required_params=["report_type", "artisan_id", "period"]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Generate report"""
        start_time = datetime.utcnow()

        try:
            report_type = kwargs.get("report_type")  # income, production, sales
            artisan_id = kwargs.get("artisan_id")
            period = kwargs.get("period")  # monthly, quarterly, annual

            # Mock report generation
            report_data = {
                "report_type": report_type,
                "artisan_id": artisan_id,
                "period": period,
                "metrics": {
                    "total_orders": 25,
                    "completed_orders": 23,
                    "total_revenue": 125000,
                    "average_order_value": 5000,
                    "customer_satisfaction": 4.5,
                },
                "trends": {
                    "revenue_growth": "15%",
                    "order_growth": "10%",
                    "customer_retention": "92%",
                },
                "recommendations": [
                    "Increase production capacity",
                    "Focus on premium segment",
                    "Build customer loyalty program",
                ]
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=report_data,
                message=f"{period.title()} {report_type} report generated",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"period": period, "report_type": report_type}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Report generation failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


# Tool instances
pdf_generator_tool = PDFGeneratorTool()
qrcode_generator_tool = QRCodeGeneratorTool()
report_generator_tool = ReportGeneratorTool()
