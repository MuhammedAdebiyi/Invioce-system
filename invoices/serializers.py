from rest_framework import serializers
from .models import Invoice, Item


class ItemSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = ['id', 'description', 'unit', 'qty', 'unit_rate', 'total_price']

    def get_total_price(self, obj):
        return obj.total_price()


class InvoiceSerializer(serializers.ModelSerializer):
    items = ItemSerializer(many=True)
    subtotal = serializers.FloatField(read_only=True)
    vat = serializers.FloatField(read_only=True)
    total = serializers.FloatField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'invoice_no',
            'invoice_date',
            'vat_date',
            'customer_name',
            'customer_address',
            'contract_no',
            'po_no',
            'subtotal',
            'vat',
            'total',
            'items',
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        invoice = Invoice.objects.create(**validated_data)
        for item_data in items_data:
            Item.objects.create(invoice=invoice, **item_data)
        invoice.calculate_totals()
        return invoice
