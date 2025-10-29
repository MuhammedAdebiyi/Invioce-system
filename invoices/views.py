import pdfkit
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator
from django.conf import settings
import os, json
from .models import Invoice, Item

@method_decorator(csrf_exempt, name='dispatch')
class GenerateInvoicePdfView(View):
    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))

            # Extract or create invoice
            invoice, created = Invoice.objects.get_or_create(
                invoice_no=data.get("invoice_no"),
                defaults={
                    "customer_name": data.get("customer_name", ""),
                    "customer_address": data.get("customer_address", ""),
                    "contract_no": data.get("contract_no", ""),
                    "po_no": data.get("po_no", ""),
                },
            )

            # Clear existing items before re-adding
            invoice.items.all().delete()

            # Add line items
            for item_data in data.get("items", []):
                Item.objects.create(
                    invoice=invoice,
                    description=item_data.get("description", ""),
                    unit=item_data.get("unit", ""),
                    qty=item_data.get("qty", 0),
                    unit_rate=item_data.get("unit_rate", 0.0),
                )

            # Calculate totals
            invoice.calculate_totals()

            # Render the invoice HTML template
            html_content = render_to_string("invoices/invoice_template.html", {"invoice": invoice})

            # Output file path
            output_path = os.path.join(settings.BASE_DIR, "generated_invoice.pdf")

            # PDF options (A4, no margins)
            options = {
                "page-size": "A4",
                "margin-top": "0mm",
                "margin-right": "0mm",
                "margin-bottom": "0mm",
                "margin-left": "0mm",
                "encoding": "UTF-8",
                "enable-local-file-access": "",
            }

            # Generate PDF with pdfkit
            pdfkit.from_string(html_content, output_path, options=options)

            # Return PDF as response
            with open(output_path, "rb") as pdf:
                response = HttpResponse(pdf.read(), content_type="application/pdf")
                response["Content-Disposition"] = f'inline; filename="{invoice.invoice_no}.pdf"'
                return response

        except Exception as e:
            return HttpResponse(f"Error generating invoice PDF: {str(e)}", status=400)

from django.conf import settings

template_path = os.path.join(settings.BASE_DIR, 'invoices', 'ISMADTECHNICAL_TEMPLATE.jpg')
