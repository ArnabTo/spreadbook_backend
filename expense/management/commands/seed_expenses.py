from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from expense.models import Expense, ExpenseItem, Category


class Command(BaseCommand):
    help = "Seed expense data for testing"

    def handle(self, *args, **options):
        self.stdout.write("Starting expense data seeding...")

        # Clear existing data
        ExpenseItem.objects.all().delete()
        Expense.objects.all().delete()
        Category.objects.all().delete()

        # Create categories
        categories_data = [
            "Rent & Utilities",
            "Food & Supplies",
            "Equipment & Maintenance",
            "Marketing & Advertising",
            "Staff & Payroll",
            "Insurance & Licenses",
            "Professional Services",
            "Other Expenses",
        ]

        categories = []
        for cat_name in categories_data:
            category, created = Category.objects.get_or_create(name=cat_name)
            categories.append(category)
            if created:
                self.stdout.write(f"Created category: {cat_name}")

        # Sample expense data matching frontend interface
        expenses_data = [
            {
                "description": "Monthly Restaurant Rent",
                "category": "rent",
                "vendor": "Property Management Co.",
                "amount": Decimal("8000.00"),
                "payment_method": "bank_transfer",
                "status": "paid",
                "recurring": True,
                "notes": "Monthly commercial rent payment",
                "expense_date": (timezone.now() - timedelta(days=30)).date(),
                "due_date": (timezone.now() - timedelta(days=25)).date(),
                "items": [
                    {
                        "title": "Base Rent",
                        "description": "Monthly base rent",
                        "quantity": 1,
                        "price": Decimal("7500.00"),
                        "total": Decimal("7500.00"),
                    },
                    {
                        "title": "Service Charge",
                        "description": "Building maintenance",
                        "quantity": 1,
                        "price": Decimal("500.00"),
                        "total": Decimal("500.00"),
                    },
                ],
            },
            {
                "description": "Electricity Bill",
                "category": "utilities",
                "vendor": "City Power Company",
                "amount": Decimal("1245.50"),
                "payment_method": "auto_debit",
                "status": "paid",
                "recurring": True,
                "notes": "Monthly electricity consumption",
                "expense_date": (timezone.now() - timedelta(days=15)).date(),
                "due_date": (timezone.now() - timedelta(days=10)).date(),
                "items": [
                    {
                        "title": "Electricity Usage",
                        "description": "850 kWh",
                        "quantity": 850,
                        "price": Decimal("1.35"),
                        "total": Decimal("1147.50"),
                    },
                    {
                        "title": "Service Fee",
                        "description": "Connection fee",
                        "quantity": 1,
                        "price": Decimal("98.00"),
                        "total": Decimal("98.00"),
                    },
                ],
            },
            {
                "description": "Water & Gas Bill",
                "category": "utilities",
                "vendor": "Municipal Services",
                "amount": Decimal("456.75"),
                "payment_method": "auto_debit",
                "status": "paid",
                "recurring": True,
                "notes": "Water and gas utilities",
                "expense_date": (timezone.now() - timedelta(days=15)).date(),
                "due_date": (timezone.now() - timedelta(days=10)).date(),
                "items": [
                    {
                        "title": "Water Usage",
                        "description": "120 cubic meters",
                        "quantity": 120,
                        "price": Decimal("2.85"),
                        "total": Decimal("342.00"),
                    },
                    {
                        "title": "Gas Usage",
                        "description": "45 cubic meters",
                        "quantity": 45,
                        "price": Decimal("2.55"),
                        "total": Decimal("114.75"),
                    },
                ],
            },
            {
                "description": "Kitchen Equipment Repair",
                "category": "maintenance",
                "vendor": "Commercial Equipment Services",
                "amount": Decimal("850.00"),
                "payment_method": "credit_card",
                "status": "paid",
                "recurring": False,
                "notes": "Repaired industrial oven and refrigerator",
                "expense_date": (timezone.now() - timedelta(days=8)).date(),
                "due_date": None,
                "items": [
                    {
                        "title": "Oven Repair",
                        "description": "Industrial oven thermostat replacement",
                        "quantity": 1,
                        "price": Decimal("450.00"),
                        "total": Decimal("450.00"),
                    },
                    {
                        "title": "Refrigerator Service",
                        "description": "Compressor maintenance",
                        "quantity": 1,
                        "price": Decimal("300.00"),
                        "total": Decimal("300.00"),
                    },
                    {
                        "title": "Service Call",
                        "description": "Technician visit fee",
                        "quantity": 1,
                        "price": Decimal("100.00"),
                        "total": Decimal("100.00"),
                    },
                ],
            },
            {
                "description": "Social Media Advertising",
                "category": "marketing",
                "vendor": "Digital Marketing Agency",
                "amount": Decimal("500.00"),
                "payment_method": "credit_card",
                "status": "pending",
                "recurring": True,
                "notes": "Facebook and Instagram ads campaign",
                "expense_date": timezone.now().date(),
                "due_date": (timezone.now() + timedelta(days=7)).date(),
                "items": [
                    {
                        "title": "Facebook Ads",
                        "description": "Promoted posts and ads",
                        "quantity": 1,
                        "price": Decimal("300.00"),
                        "total": Decimal("300.00"),
                    },
                    {
                        "title": "Instagram Promotion",
                        "description": "Story and feed promotion",
                        "quantity": 1,
                        "price": Decimal("200.00"),
                        "total": Decimal("200.00"),
                    },
                ],
            },
            {
                "description": "Fresh Produce Purchase",
                "category": "supplies",
                "vendor": "Local Farm Suppliers",
                "amount": Decimal("1250.00"),
                "payment_method": "cash",
                "status": "paid",
                "recurring": False,
                "notes": "Weekly fresh vegetables and fruits",
                "expense_date": (timezone.now() - timedelta(days=3)).date(),
                "due_date": None,
                "items": [
                    {
                        "title": "Vegetables",
                        "description": "Mixed fresh vegetables",
                        "quantity": 50,
                        "price": Decimal("15.00"),
                        "total": Decimal("750.00"),
                    },
                    {
                        "title": "Fruits",
                        "description": "Seasonal fruits",
                        "quantity": 25,
                        "price": Decimal("20.00"),
                        "total": Decimal("500.00"),
                    },
                ],
            },
            {
                "description": "Restaurant Insurance Premium",
                "category": "insurance",
                "vendor": "Reliable Insurance Co.",
                "amount": Decimal("2200.00"),
                "payment_method": "bank_transfer",
                "status": "paid",
                "recurring": False,
                "notes": "Quarterly insurance premium",
                "expense_date": (timezone.now() - timedelta(days=5)).date(),
                "due_date": None,
                "items": [
                    {
                        "title": "General Liability",
                        "description": "Public liability coverage",
                        "quantity": 1,
                        "price": Decimal("1200.00"),
                        "total": Decimal("1200.00"),
                    },
                    {
                        "title": "Property Insurance",
                        "description": "Equipment and building coverage",
                        "quantity": 1,
                        "price": Decimal("800.00"),
                        "total": Decimal("800.00"),
                    },
                    {
                        "title": "Workers Compensation",
                        "description": "Staff injury coverage",
                        "quantity": 1,
                        "price": Decimal("200.00"),
                        "total": Decimal("200.00"),
                    },
                ],
            },
            {
                "description": "Cleaning Supplies Stock",
                "category": "supplies",
                "vendor": "Hygiene Supply Company",
                "amount": Decimal("325.75"),
                "payment_method": "debit_card",
                "status": "paid",
                "recurring": True,
                "notes": "Monthly cleaning and sanitizing supplies",
                "expense_date": (timezone.now() - timedelta(days=12)).date(),
                "due_date": None,
                "items": [
                    {
                        "title": "Disinfectants",
                        "description": "Kitchen and surface cleaners",
                        "quantity": 10,
                        "price": Decimal("18.50"),
                        "total": Decimal("185.00"),
                    },
                    {
                        "title": "Paper Products",
                        "description": "Napkins, tissues, towels",
                        "quantity": 15,
                        "price": Decimal("8.25"),
                        "total": Decimal("123.75"),
                    },
                    {
                        "title": "Soap & Sanitizers",
                        "description": "Hand soap and sanitizers",
                        "quantity": 5,
                        "price": Decimal("3.40"),
                        "total": Decimal("17.00"),
                    },
                ],
            },
            {
                "description": "Business License Renewal",
                "category": "licenses",
                "vendor": "City Business Authority",
                "amount": Decimal("450.00"),
                "payment_method": "check",
                "status": "overdue",
                "recurring": False,
                "notes": "Annual business operation license",
                "expense_date": (timezone.now() - timedelta(days=20)).date(),
                "due_date": (timezone.now() - timedelta(days=5)).date(),
                "items": [
                    {
                        "title": "Business License",
                        "description": "Annual operation permit",
                        "quantity": 1,
                        "price": Decimal("350.00"),
                        "total": Decimal("350.00"),
                    },
                    {
                        "title": "Processing Fee",
                        "description": "Government processing fee",
                        "quantity": 1,
                        "price": Decimal("100.00"),
                        "total": Decimal("100.00"),
                    },
                ],
            },
            {
                "description": "Staff Training Program",
                "category": "other",
                "vendor": "Professional Training Institute",
                "amount": Decimal("750.00"),
                "payment_method": "bank_transfer",
                "status": "pending",
                "recurring": False,
                "notes": "Food safety and customer service training",
                "expense_date": timezone.now().date(),
                "due_date": (timezone.now() + timedelta(days=14)).date(),
                "items": [
                    {
                        "title": "Food Safety Course",
                        "description": "8-hour certification program",
                        "quantity": 6,
                        "price": Decimal("75.00"),
                        "total": Decimal("450.00"),
                    },
                    {
                        "title": "Customer Service Training",
                        "description": "4-hour workshop",
                        "quantity": 6,
                        "price": Decimal("50.00"),
                        "total": Decimal("300.00"),
                    },
                ],
            },
        ]

        # Create expenses with items
        created_expenses = 0
        created_items = 0

        for expense_data in expenses_data:
            items_data = expense_data.pop("items", [])

            # Create expense
            expense = Expense.objects.create(**expense_data)
            created_expenses += 1

            # Create expense items
            for item_data in items_data:
                ExpenseItem.objects.create(expense_invoice=expense, **item_data)
                created_items += 1

            self.stdout.write(
                f"Created expense: {expense.description} (${expense.amount})"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {created_expenses} expenses with {created_items} expense items"
            )
        )
