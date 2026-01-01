from django.core.management.base import BaseCommand
from menu_items.models import MenuItem


class Command(BaseCommand):
    help = "Create basic menu items for testing POS integration"

    def handle(self, *args, **options):
        # Clear existing items
        MenuItem.objects.all().delete()
        self.stdout.write("Cleared existing menu items")

        # Create basic test items
        test_items = [
            {
                "name": "Chicken Seekh Kebab",
                "category": "kebab",
                "price": 399.99,
                "cost": 200.00,
                "description": "Spicy grilled chicken seekh kebab with mint chutney",
                "available": True,
                "is_featured": True,
                "preparation_time": 15,
                "is_vegetarian": False,
            },
            {
                "name": "Lamb Shish Kebab",
                "category": "kebab",
                "price": 599.99,
                "cost": 300.00,
                "description": "Tender lamb pieces grilled to perfection",
                "available": True,
                "is_featured": True,
                "preparation_time": 18,
                "is_vegetarian": False,
            },
            {
                "name": "Pad Thai",
                "category": "thai",
                "price": 450.99,
                "cost": 200.00,
                "description": "Traditional Thai stir-fried rice noodles",
                "available": True,
                "is_featured": True,
                "preparation_time": 12,
                "is_vegetarian": False,
            },
            {
                "name": "Green Curry",
                "category": "thai",
                "price": 499.99,
                "cost": 250.00,
                "description": "Spicy Thai green curry with coconut milk",
                "available": True,
                "is_featured": False,
                "preparation_time": 20,
                "is_vegetarian": False,
            },
            {
                "name": "Kung Pao Chicken",
                "category": "chinese",
                "price": 429.99,
                "cost": 220.00,
                "description": "Spicy Sichuan chicken with peanuts",
                "available": True,
                "is_featured": False,
                "preparation_time": 15,
                "is_vegetarian": False,
            },
            {
                "name": "Fried Rice",
                "category": "chinese",
                "price": 299.99,
                "cost": 150.00,
                "description": "Wok-fried rice with vegetables and egg",
                "available": True,
                "is_featured": False,
                "preparation_time": 10,
                "is_vegetarian": True,
            },
            {
                "name": "Fresh Lime Soda",
                "category": "drinks",
                "price": 149.99,
                "cost": 50.00,
                "description": "Refreshing lime soda with mint",
                "available": True,
                "is_featured": False,
                "preparation_time": 3,
                "is_vegetarian": True,
            },
            {
                "name": "Mango Lassi",
                "category": "drinks",
                "price": 199.99,
                "cost": 80.00,
                "description": "Creamy mango yogurt drink",
                "available": True,
                "is_featured": True,
                "preparation_time": 5,
                "is_vegetarian": True,
            },
            {
                "name": "Chicken Burger",
                "category": "fastfood",
                "price": 349.99,
                "cost": 180.00,
                "description": "Grilled chicken burger with cheese and fries",
                "available": True,
                "is_featured": True,
                "preparation_time": 12,
                "is_vegetarian": False,
            },
            {
                "name": "French Fries",
                "category": "fastfood",
                "price": 199.99,
                "cost": 80.00,
                "description": "Crispy golden french fries",
                "available": True,
                "is_featured": False,
                "preparation_time": 8,
                "is_vegetarian": True,
            },
        ]

        created_count = 0
        for item_data in test_items:
            menu_item = MenuItem.objects.create(**item_data)
            self.stdout.write(f"Created: {menu_item.name} - ৳{menu_item.price}")
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {created_count} menu items!")
        )

        # Print categories
        categories = MenuItem.objects.values_list("category", flat=True).distinct()
        self.stdout.write(f"Categories created: {', '.join(categories)}")
