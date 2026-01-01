from django.core.management.base import BaseCommand
from suppliers.models import Supplier


class Command(BaseCommand):
    help = "Create sample supplier data for testing"

    def handle(self, *args, **options):
        # Clear existing suppliers
        Supplier.objects.all().delete()

        # Create sample suppliers
        suppliers_data = [
            {
                "name": "Fresh Meats Bangladesh",
                "supplier_code": "FMB001",
                "address": "123 Kawran Bazar, Dhaka-1215",
                "phone": "+880 1712-345678",
                "email": "rahman@freshmeats.bd",
                "zip_code": "1215",
                "country": "BD",
                "previous_balance": 0,
                "category": "Meat & Poultry",
                "contactPerson": "Md. Rahman",
                "rating": 4.8,
                "totalPurchases": 156,
                "totalSpent": 4520000,
                "paymentTerms": "Net 30",
                "status": "Active",
            },
            {
                "name": "Green Herbs Ltd",
                "supplier_code": "GHL002",
                "address": "456 New Market, Dhaka-1205",
                "phone": "+880 1823-456789",
                "email": "fatima@greenherbs.bd",
                "zip_code": "1205",
                "country": "BD",
                "previous_balance": 0,
                "category": "Herbs & Spices",
                "contactPerson": "Fatima Begum",
                "rating": 4.9,
                "totalPurchases": 203,
                "totalSpent": 1280000,
                "paymentTerms": "Net 15",
                "status": "Active",
            },
            {
                "name": "Dhaka Spice Traders",
                "supplier_code": "DST003",
                "address": "789 Shyampur, Dhaka-1204",
                "phone": "+880 1934-567890",
                "email": "karim@dhakaSpice.bd",
                "zip_code": "1204",
                "country": "BD",
                "previous_balance": 0,
                "category": "Spices & Condiments",
                "contactPerson": "Abdul Karim",
                "rating": 4.6,
                "totalPurchases": 98,
                "totalSpent": 2840000,
                "paymentTerms": "Net 30",
                "status": "Active",
            },
            {
                "name": "Chittagong Fish Market",
                "supplier_code": "CFM004",
                "address": "Fish Market Road, Chittagong-4000",
                "phone": "+880 1845-678901",
                "email": "nasir@ctgfish.bd",
                "zip_code": "4000",
                "country": "BD",
                "previous_balance": 0,
                "category": "Fish & Seafood",
                "contactPerson": "Nasir Ahmed",
                "rating": 4.7,
                "totalPurchases": 89,
                "totalSpent": 3200000,
                "paymentTerms": "Net 15",
                "status": "Active",
            },
            {
                "name": "Sylhet Tea & Dairy",
                "supplier_code": "STD005",
                "address": "Tea Estate Road, Sylhet-3100",
                "phone": "+880 1756-789012",
                "email": "rubina@sylhettea.bd",
                "zip_code": "3100",
                "country": "BD",
                "previous_balance": 0,
                "category": "Beverages & Dairy",
                "contactPerson": "Rubina Khatun",
                "rating": 4.5,
                "totalPurchases": 145,
                "totalSpent": 1850000,
                "paymentTerms": "Net 30",
                "status": "Active",
            },
            {
                "name": "Rajshahi Vegetables",
                "supplier_code": "RV006",
                "address": "Wholesale Market, Rajshahi-6000",
                "phone": "+880 1667-890123",
                "email": "shahid@rajvegs.bd",
                "zip_code": "6000",
                "country": "BD",
                "previous_balance": 0,
                "category": "Vegetables & Fruits",
                "contactPerson": "Shahidul Islam",
                "rating": 4.4,
                "totalPurchases": 167,
                "totalSpent": 2100000,
                "paymentTerms": "Net 20",
                "status": "Inactive",
            },
        ]

        for supplier_data in suppliers_data:
            supplier = Supplier.objects.create(**supplier_data)
            self.stdout.write(self.style.SUCCESS(f"Created supplier: {supplier.name}"))

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {len(suppliers_data)} suppliers")
        )
