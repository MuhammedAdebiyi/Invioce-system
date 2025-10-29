import os
import uuid
from datetime import datetime, date
from io import BytesIO

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

import boto3
import pdfkit
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

from .models import Invoice, Item, generate_invoice_no


# -----------------------------
# AWS Textract setup
# -----------------------------
textract_client = boto3.client(
    "textract",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)


# -----------------------------
# Utility
# -----------------------------
def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# -----------------------------
# 1️⃣ Extract invoice data using Textract
# -----------------------------
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def extract_invoice(request):
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return Response({"error": "No file uploaded"}, status=400)

    fname = uploaded_file.name
    ext = os.path.splitext(fname)[1]
    unique_name = f"{os.path.splitext(fname)[0]}_{uuid.uuid4().hex}{ext}"
    save_path = os.path.join("invoice_templates", unique_name)
    path_on_disk = default_storage.save(save_path, ContentFile(uploaded_file.read()))
    file_bytes = default_storage.open(path_on_disk).read()

    try:
        response = textract_client.analyze_document(
            Document={"Bytes": file_bytes},
            FeatureTypes=["TABLES", "FORMS"],
        )
    except Exception as e:
        return Response({"error": str(e)}, status=500)

    invoice_data = {
        "invoice_no": "",
        "invoice_date": "",
        "vat_date": "",
        "customer_name": "",
        "customer_address": "",
        "contract_no": "",
        "po_no": "",
        "items": [],
        "subtotal": 0,
        "vat": 0,
        "total": 0,
        "template_url": settings.MEDIA_URL + save_path,
        "template_path": save_path,
    }

    # Parse key/value fields
    for block in response.get("Blocks", []):
        if block.get("BlockType") == "KEY_VALUE_SET" and "KEY" in block.get("EntityTypes", []):
            key_text, value_text = "", ""
            for rel in block.get("Relationships", []) or []:
                for rid in rel.get("Ids", []):
                    b = next((bb for bb in response["Blocks"] if bb["Id"] == rid), None)
                    if b and b.get("BlockType") == "WORD":
                        key_text += b.get("Text", "") + " "
                    if b and b.get("BlockType") == "VALUE":
                        value_text += b.get("Text", "") + " "
            key_text, value_text = key_text.strip().lower(), value_text.strip()
            if "invoice no" in key_text:
                invoice_data["invoice_no"] = value_text
            elif "invoice date" in key_text:
                invoice_data["invoice_date"] = value_text
            elif "vat date" in key_text:
                invoice_data["vat_date"] = value_text
            elif "customer" in key_text and "sold" in key_text:
                invoice_data["customer_name"] = value_text
            elif "address" in key_text:
                invoice_data["customer_address"] = value_text
            elif "contract" in key_text:
                invoice_data["contract_no"] = value_text
            elif "po" in key_text:
                invoice_data["po_no"] = value_text

    # Parse table rows
    rows = []
    for block in response.get("Blocks", []):
        if block.get("BlockType") == "TABLE":
            for rel in block.get("Relationships", []) or []:
                if rel.get("Type") == "CHILD":
                    for cid in rel.get("Ids", []):
                        cell = next((b for b in response["Blocks"] if b.get("Id") == cid), None)
                        if cell and cell.get("BlockType") == "CELL":
                            cell_text = ""
                            for r in cell.get("Relationships", []) or []:
                                for wid in r.get("Ids", []):
                                    word = next((b for b in response["Blocks"] if b.get("Id") == wid), None)
                                    if word and word.get("BlockType") == "WORD":
                                        cell_text += word.get("Text", "") + " "
                            rows.append(cell_text.strip())

    for r in range(0, len(rows), 4):
        if r + 3 < len(rows):
            invoice_data["items"].append(
                {
                    "description": rows[r],
                    "unit": rows[r + 1],
                    "qty": safe_float(rows[r + 2]),
                    "unit_rate": safe_float(rows[r + 3]),
                }
            )

    subtotal = sum(i["qty"] * i["unit_rate"] for i in invoice_data["items"])
    vat = round(subtotal * 0.075, 2)
    total = round(subtotal + vat, 2)

    invoice_data["subtotal"] = subtotal
    invoice_data["vat"] = vat
    invoice_data["total"] = total
    invoice_data["invoice_date"] = invoice_data["invoice_date"] or datetime.now().date().isoformat()
    invoice_data["vat_date"] = invoice_data["vat_date"] or invoice_data["invoice_date"]
    invoice_data["invoice_no"] = invoice_data["invoice_no"] or f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    return Response(invoice_data)


# -----------------------------
# 2️⃣ Save + Generate PDF (ReportLab)
# -----------------------------
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def save_invoice(request):
    data = request.data
    try:
        default_template = "invoice_templates/ISMADTECHNICAL_TEMPLATE.jpg"

        invoice = Invoice.objects.create(
            invoice_no=generate_invoice_no(),
            customer_name=data.get("customer_name", ""),
            customer_address=data.get("customer_address", ""),
            contract_no=data.get("contract_no", ""),
            po_no=data.get("po_no", ""),
            invoice_date=datetime.now().date(),
            vat_date=datetime.now().date(),
            template_image=default_template,
        )

        for item in data.get("items", []):
            Item.objects.create(
                invoice=invoice,
                description=item.get("description", ""),
                unit=item.get("unit", ""),
                qty=item.get("qty", 0),
                unit_rate=item.get("unit_rate", 0),
            )

        invoice.calculate_totals()

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        bg_path = os.path.join(settings.BASE_DIR, "invoices", "static", "invoices", "ISMADTECHNICAL_TEMPLATE.jpg")

        if os.path.exists(bg_path):
            bg = ImageReader(bg_path)
            p.drawImage(bg, 0, 0, width=width, height=height, preserveAspectRatio=True, mask="auto")

        p.setFont("Helvetica", 10)
        p.drawString(400, 800, f"Invoice No: {invoice.invoice_no}")
        p.drawString(400, 785, f"Invoice Date: {invoice.invoice_date}")
        p.drawString(50, 750, f"Customer: {invoice.customer_name}")
        p.drawString(50, 735, f"Address: {invoice.customer_address}")
        p.drawString(400, 100, f"Subtotal: {invoice.subtotal:,.2f}")
        p.drawString(400, 85, f"VAT (7.5%): {invoice.vat:,.2f}")
        p.drawString(400, 70, f"Total: {invoice.total:,.2f}")

        p.showPage()
        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{invoice.invoice_no}.pdf"'
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=400)


# -----------------------------
# 3️⃣ Create & Download invoice with pdfkit (wkhtmltopdf)
# -----------------------------
WKHTMLTOPDF_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
if os.path.exists(WKHTMLTOPDF_PATH):
    PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
else:
    PDFKIT_CONFIG = pdfkit.configuration()


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def create_and_download_invoice(request):
    try:
        data = request.data or {}

        # ✅ Correct absolute path for your image
        abs_path = os.path.join(
            settings.BASE_DIR, "invoices", "static", "invoices", "ISMADTECHNICAL_TEMPLATE.jpg"
        )

        if not os.path.exists(abs_path):
            raise FileNotFoundError(
                f"Template not found at {abs_path}. Make sure ISMADTECHNICAL_TEMPLATE.jpg is inside invoices/static/invoices/"
            )

        invoice_no = data.get("invoice_no") or generate_invoice_no()
        invoice = Invoice.objects.create(
            invoice_no=invoice_no,
            customer_name=data.get("customer_name", ""),
            customer_address=data.get("customer_address", ""),
            contract_no=data.get("contract_no", ""),
            po_no=data.get("po_no", ""),
            invoice_date=data.get("invoice_date") or date.today(),
            vat_date=data.get("vat_date") or date.today(),
            template_image=f"invoice_templates/{os.path.basename(abs_path)}",
        )

        for it in data.get("items", []):
            Item.objects.create(
                invoice=invoice,
                description=it.get("description", ""),
                unit=it.get("unit", ""),
                qty=int(it.get("qty", 0)),
                unit_rate=float(it.get("unit_rate", 0.0)),
            )

        invoice.calculate_totals()

        items_for_template = [
            {
                "sn": idx,
                "description": it.description,
                "unit": it.unit,
                "qty": it.qty,
                "rate": it.unit_rate,
                "amount": it.total_price(),
            }
            for idx, it in enumerate(invoice.items.all(), start=1)
        ]

        context = {
            "tin_no": getattr(settings, "COMPANY_TIN", "19839807-0001"),
            "vat_date": invoice.vat_date,
            "invoice_no": invoice.invoice_no,
            "invoice_date": invoice.invoice_date,
            "customer_name": invoice.customer_name,
            "customer_address": invoice.customer_address,
            "items": items_for_template,
            "subtotal": invoice.subtotal,
            "vat": invoice.vat,
            "total": invoice.total,
            "template_image": "file:///" + abs_path.replace("\\", "/"),
        }

        html = render_to_string("invoices/invoice_template.html", context)
        options = {
            "enable-local-file-access": None,
            "margin-top": "0mm",
            "margin-bottom": "0mm",
            "margin-left": "0mm",
            "margin-right": "0mm",
            "page-size": "A4",
        }

        pdf_bytes = pdfkit.from_string(html, False, configuration=PDFKIT_CONFIG, options=options)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{invoice.invoice_no}.pdf"'
        return response
    
    except Exception as e:
        return Response({"error": str(e)}, status=400)

