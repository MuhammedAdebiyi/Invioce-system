# invoices/models.py
from django.db import models
from datetime import date
from django.db.models import Max

class Invoice(models.Model):
    invoice_no = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField(default=date.today)
    vat_date = models.DateField(default=date.today)
    customer_name = models.CharField(max_length=255, blank=True)
    customer_address = models.TextField(blank=True)
    contract_no = models.CharField(max_length=50, blank=True)
    po_no = models.CharField(max_length=50, blank=True)

    subtotal = models.FloatField(default=0.0)
    vat = models.FloatField(default=0.0)
    total = models.FloatField(default=0.0)

    template_image = models.ImageField(upload_to='invoice_templates/', blank=True, null=True)

    def calculate_totals(self):
        items = self.items.all()
        self.subtotal = sum(item.qty * item.unit_rate for item in items)
        self.vat = round(self.subtotal * 0.075, 2)
        self.total = round(self.subtotal + self.vat, 2)
        self.save(update_fields=['subtotal', 'vat', 'total'])

    def __str__(self):
        return f"Invoice {self.invoice_no}"

class Item(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    unit = models.CharField(max_length=20, blank=True)
    qty = models.IntegerField(default=0)
    unit_rate = models.FloatField(default=0.0)

    def total_price(self):
        return self.qty * self.unit_rate

    def __str__(self):
        return f"{self.description} ({self.qty} x {self.unit_rate})"


# Helper to generate reasonably unique invoice numbers
def generate_invoice_no(prefix="INV"):
    # Format: INV-YYYYMMDD-XXXX (sequential per day)
    today = date.today()
    day_prefix = today.strftime("%Y%m%d")
    base = f"{prefix}-{day_prefix}-"
    # Find the highest existing invoice with today's prefix
    last = Invoice.objects.filter(invoice_no__startswith=base).order_by('invoice_no').last()
    if not last:
        seq = 1
    else:
        # extract trailing number
        try:
            seq = int(last.invoice_no.split('-')[-1]) + 1
        except Exception:
            seq = 1
    return f"{base}{seq:04d}"
