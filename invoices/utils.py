from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

def generate_invoice_pdf(invoice):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"Invoice: {invoice.invoice_no}")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"Invoice Date: {invoice.invoice_date}")
    c.drawString(50, height - 100, f"Customer: {invoice.customer_name}")
    c.drawString(50, height - 120, f"Address: {invoice.customer_address}")

    # Table header
    c.drawString(50, height - 160, "Description")
    c.drawString(250, height - 160, "Unit")
    c.drawString(350, height - 160, "Qty")
    c.drawString(400, height - 160, "Unit Rate")
    c.drawString(500, height - 160, "Amount")

    y = height - 180
    for item in invoice.items.all():
        c.drawString(50, y, item.description)
        c.drawString(250, y, item.unit)
        c.drawString(350, y, str(item.qty))
        c.drawString(400, y, str(item.unit_rate))
        c.drawString(500, y, str(round(item.qty * item.unit_rate, 2)))
        y -= 20

    c.drawString(400, y - 20, f"Subtotal: {invoice.subtotal}")
    c.drawString(400, y - 40, f"VAT (7.5%): {invoice.vat}")
    c.drawString(400, y - 60, f"Total: {invoice.total}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
