from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal

from products.models.inventory_model import InventoryItem, InventoryCategory
from products.models.unit_model import Unit
from suppliers.models import Supplier


class Command(BaseCommand):
    help = "Populate database with initial inventory data matching frontend"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting inventory data population..."))

        # Create categories
        categories_data = [
            "Meat",
            "Vegetables",
            "Grains",
            "Herbs",
            "Condiments",
            "Dairy",
            "Oils",
        ]

        categories = {}
        for cat_name in categories_data:
            category, created = InventoryCategory.objects.get_or_create(
                name=cat_name,
                defaults={"description": f"{cat_name} ingredients for restaurant"},
            )
            categories[cat_name] = category
            if created:
                self.stdout.write(f"Created category: {cat_name}")

        # Create units
        units_data = ["kg", "bunches", "bottles", "cans", "liters"]
        units = {}
        for unit_name in units_data:
            unit, created = Unit.objects.get_or_create(
                name=unit_name, defaults={"status": True}
            )
            units[unit_name] = unit
            if created:
                self.stdout.write(f"Created unit: {unit_name}")

        # Create suppliers
        suppliers_data = [
            {
                "name": "Fresh Meats Co.",
                "contactPerson": "John Smith",
                "phone": "+1234567890",
                "email": "orders@freshmeats.com",
            },
            {
                "name": "Rice World",
                "contactPerson": "Maria Garcia",
                "phone": "+1234567891",
                "email": "sales@riceworld.com",
            },
            {
                "name": "Green Herbs Ltd",
                "contactPerson": "David Chen",
                "phone": "+1234567892",
                "email": "info@greenherbs.com",
            },
            {
                "name": "Asian Imports",
                "contactPerson": "Kim Lee",
                "phone": "+1234567893",
                "email": "contact@asianimports.com",
            },
            {
                "name": "Thai Foods Inc",
                "contactPerson": "Somchai Thang",
                "phone": "+1234567894",
                "email": "orders@thaifoods.com",
            },
            {
                "name": "Mediterranean Goods",
                "contactPerson": "Giuseppe Romano",
                "phone": "+1234567895",
                "email": "sales@medgoods.com",
            },
            {
                "name": "Farm Fresh",
                "contactPerson": "Sarah Johnson",
                "phone": "+1234567896",
                "email": "orders@farmfresh.com",
            },
        ]

        suppliers = {}
        for supplier_data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                name=supplier_data["name"],
                defaults={
                    "contactPerson": supplier_data["contactPerson"],
                    "phone": supplier_data["phone"],
                    "email": supplier_data["email"],
                    "address": f"123 Main St, City, Country",
                },
            )
            suppliers[supplier_data["name"]] = supplier
            if created:
                self.stdout.write(f'Created supplier: {supplier_data["name"]}')

        # Create initial inventory items matching frontend data
        inventory_data = [
            {
                "name": "Chicken Breast",
                "category": "Meat",
                "current_stock": Decimal("12.00"),
                "unit": "kg",
                "reorder_level": Decimal("50.00"),
                "max_stock": Decimal("150.00"),
                "cost_per_unit": Decimal("8.50"),
                "supplier": "Fresh Meats Co.",
                "sku": "MEAT-001",
            },
            {
                "name": "Basmati Rice",
                "category": "Grains",
                "current_stock": Decimal("45.00"),
                "unit": "kg",
                "reorder_level": Decimal("30.00"),
                "max_stock": Decimal("200.00"),
                "cost_per_unit": Decimal("2.20"),
                "supplier": "Rice World",
                "sku": "GRAIN-001",
            },
            {
                "name": "Thai Basil",
                "category": "Herbs",
                "current_stock": Decimal("5.00"),
                "unit": "bunches",
                "reorder_level": Decimal("20.00"),
                "max_stock": Decimal("50.00"),
                "cost_per_unit": Decimal("1.50"),
                "supplier": "Green Herbs Ltd",
                "sku": "HERB-001",
            },
            {
                "name": "Soy Sauce",
                "category": "Condiments",
                "current_stock": Decimal("8.00"),
                "unit": "bottles",
                "reorder_level": Decimal("15.00"),
                "max_stock": Decimal("50.00"),
                "cost_per_unit": Decimal("3.75"),
                "supplier": "Asian Imports",
                "sku": "COND-001",
            },
            {
                "name": "Coconut Milk",
                "category": "Dairy",
                "current_stock": Decimal("24.00"),
                "unit": "cans",
                "reorder_level": Decimal("30.00"),
                "max_stock": Decimal("100.00"),
                "cost_per_unit": Decimal("1.80"),
                "supplier": "Thai Foods Inc",
                "sku": "DAIRY-001",
            },
            {
                "name": "Lamb Meat",
                "category": "Meat",
                "current_stock": Decimal("35.00"),
                "unit": "kg",
                "reorder_level": Decimal("25.00"),
                "max_stock": Decimal("100.00"),
                "cost_per_unit": Decimal("12.50"),
                "supplier": "Fresh Meats Co.",
                "sku": "MEAT-002",
            },
            {
                "name": "Olive Oil",
                "category": "Oils",
                "current_stock": Decimal("18.00"),
                "unit": "liters",
                "reorder_level": Decimal("20.00"),
                "max_stock": Decimal("60.00"),
                "cost_per_unit": Decimal("8.00"),
                "supplier": "Mediterranean Goods",
                "sku": "OIL-001",
            },
            {
                "name": "Tomatoes",
                "category": "Vegetables",
                "current_stock": Decimal("22.00"),
                "unit": "kg",
                "reorder_level": Decimal("15.00"),
                "max_stock": Decimal("80.00"),
                "cost_per_unit": Decimal("2.50"),
                "supplier": "Farm Fresh",
                "sku": "VEG-001",
            },
        ]

        for item_data in inventory_data:
            item, created = InventoryItem.objects.get_or_create(
                name=item_data["name"],
                defaults={
                    "category": categories[item_data["category"]],
                    "unit": units[item_data["unit"]],
                    "current_stock": item_data["current_stock"],
                    "reorder_level": item_data["reorder_level"],
                    "max_stock": item_data["max_stock"],
                    "cost_per_unit": item_data["cost_per_unit"],
                    "supplier": suppliers[item_data["supplier"]],
                    "sku": item_data["sku"],
                    "description": f'High-quality {item_data["name"]} for restaurant use',
                },
            )
            if created:
                self.stdout.write(f'Created inventory item: {item_data["name"]}')
            else:
                self.stdout.write(f'Updated inventory item: {item_data["name"]}')

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully populated inventory with {len(inventory_data)} items, "
                f"{len(categories_data)} categories, {len(units_data)} units, and "
                f"{len(suppliers_data)} suppliers!"
            )
        )
