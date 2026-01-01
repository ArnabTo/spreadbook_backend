from django.core.management.base import BaseCommand
from django.db import transaction, models
from menu_items.models import MenuItem, MenuCategory
from decimal import Decimal
import random
import random


class Command(BaseCommand):
    help = "Seed menu items database with sample data including multiple categories"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing menu items before seeding",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=58,
            help="Number of menu items to create (default: 58)",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing menu items..."))
            MenuItem.objects.all().delete()
            MenuCategory.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("🍽️  Starting menu items seeding..."))

        # Create categories first
        categories = self.create_categories()

        # Create menu items
        menu_items = self.create_menu_items(categories, options["count"])

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Successfully created {len(categories)} categories and {len(menu_items)} menu items!"
            )
        )

        # Print summary
        self.print_summary()

    def create_categories(self):
        """Create menu categories"""
        categories_data = [
            {
                "name": "Appetizers",
                "description": "Delicious starters to begin your meal",
                "display_order": 1,
            },
            {
                "name": "Soups",
                "description": "Hot and comforting soups",
                "display_order": 2,
            },
            {
                "name": "Salads",
                "description": "Fresh and healthy salad options",
                "display_order": 3,
            },
            {
                "name": "Main Course",
                "description": "Hearty main dishes and entrees",
                "display_order": 4,
            },
            {
                "name": "Rice & Biryanis",
                "description": "Traditional rice dishes and aromatic biryanis",
                "display_order": 5,
            },
            {
                "name": "Curries",
                "description": "Spicy and flavorful curry dishes",
                "display_order": 6,
            },
            {
                "name": "Grilled Items",
                "description": "Barbecued and grilled specialties",
                "display_order": 7,
            },
            {
                "name": "Seafood",
                "description": "Fresh fish and seafood preparations",
                "display_order": 8,
            },
            {
                "name": "Vegetarian",
                "description": "Plant-based dishes and vegetarian options",
                "display_order": 9,
            },
            {
                "name": "Desserts",
                "description": "Sweet treats and traditional desserts",
                "display_order": 10,
            },
            {
                "name": "Beverages",
                "description": "Refreshing drinks and beverages",
                "display_order": 11,
            },
            {
                "name": "Breakfast",
                "description": "Morning meal options",
                "display_order": 12,
            },
            {
                "name": "Pizza",
                "description": "Wood-fired pizzas with fresh toppings",
                "display_order": 13,
            },
            {
                "name": "Burgers",
                "description": "Gourmet burgers and sandwiches",
                "display_order": 14,
            },
            {
                "name": "Noodles",
                "description": "Asian-style noodle dishes",
                "display_order": 15,
            },
        ]

        categories = []
        with transaction.atomic():
            for cat_data in categories_data:
                category, created = MenuCategory.objects.get_or_create(
                    name=cat_data["name"], defaults=cat_data
                )
                categories.append(category)
                if created:
                    self.stdout.write(f"Created category: {category.name}")

        return categories

    def create_menu_items(self, categories, count):
        """Create menu items with realistic Bangladeshi restaurant data"""

        menu_items_data = [
            # STARTER ITEM
            {
                "name": "Chicken Wonton (6 Pcs)",
                "category": "Appetizers",
                "price": 180,
                "cost": 90,
                "description": "Crispy chicken wontons served with sweet chili sauce",
                "prep_time": 12,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Chicken Puff (6 Pcs)",
                "category": "Appetizers",
                "price": 260,
                "cost": 130,
                "description": "Flaky pastry filled with spiced chicken",
                "prep_time": 15,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Chicken Roll (6 Pcs)",
                "category": "Appetizers",
                "price": 200,
                "cost": 100,
                "description": "Crispy chicken rolls with vegetables",
                "prep_time": 12,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Cheese Roll (6 Pcs)",
                "category": "Appetizers",
                "price": 180,
                "cost": 90,
                "description": "Golden fried cheese rolls",
                "prep_time": 10,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Veg Chicken (6Pcs)",
                "category": "Appetizers",
                "price": 180,
                "cost": 90,
                "description": "Vegetarian chicken alternative appetizer",
                "prep_time": 12,
                "vegetarian": True,
                "featured": False,
            },
            # SOUP ITEM
            {
                "name": "Hot Desi Soup (1:1)",
                "category": "Soups",
                "price": 450,
                "cost": 180,
                "description": "Traditional spicy desi style soup",
                "prep_time": 20,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Hot Desi Soup (1:10)",
                "category": "Soups",
                "price": 350,
                "cost": 140,
                "description": "Traditional spicy desi style soup - family size",
                "prep_time": 25,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Chicken Corn Soup (1:1)",
                "category": "Soups",
                "price": 320,
                "cost": 130,
                "description": "Creamy chicken and sweet corn soup",
                "prep_time": 15,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Vegetable Soup (1:1)",
                "category": "Soups",
                "price": 200,
                "cost": 80,
                "description": "Fresh mixed vegetable soup",
                "prep_time": 18,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Chicken Clear Soup (1:1)",
                "category": "Soups",
                "price": 350,
                "cost": 140,
                "description": "Light and clear chicken broth",
                "prep_time": 20,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Noodles Chicken Soup (1:1)",
                "category": "Soups",
                "price": 380,
                "cost": 150,
                "description": "Chicken soup with noodles",
                "prep_time": 22,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Noodles Chicken Soup (1:3)",
                "category": "Soups",
                "price": 460,
                "cost": 180,
                "description": "Chicken soup with noodles - large portion",
                "prep_time": 25,
                "vegetarian": False,
                "featured": False,
            },
            # FRIED RICE
            {
                "name": "Mix Fried Rice (1:1)",
                "category": "Rice & Biryanis",
                "price": 300,
                "cost": 120,
                "description": "Mixed fried rice with egg and vegetables",
                "prep_time": 15,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Mix Fried Rice (1:3)",
                "category": "Rice & Biryanis",
                "price": 380,
                "cost": 150,
                "description": "Mixed fried rice with egg and vegetables - large portion",
                "prep_time": 18,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Chicken Fried Rice (1:1)",
                "category": "Rice & Biryanis",
                "price": 320,
                "cost": 130,
                "description": "Fried rice with chicken and vegetables",
                "prep_time": 18,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Chicken Fried Rice (1:3)",
                "category": "Rice & Biryanis",
                "price": 400,
                "cost": 160,
                "description": "Fried rice with chicken and vegetables - large portion",
                "prep_time": 20,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Shrimp Fried Rice (1:1)",
                "category": "Rice & Biryanis",
                "price": 400,
                "cost": 180,
                "description": "Delicious shrimp fried rice",
                "prep_time": 20,
                "vegetarian": False,
                "featured": True,
            },
            # SALAD
            {
                "name": "Chechew Wet Salad",
                "category": "Salads",
                "price": 300,
                "cost": 120,
                "description": "Fresh wet salad with cashews",
                "prep_time": 10,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Chicken Prawn Mixed Salad",
                "category": "Salads",
                "price": 400,
                "cost": 180,
                "description": "Mixed salad with chicken and prawns",
                "prep_time": 15,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Green Salad",
                "category": "Salads",
                "price": 80,
                "cost": 30,
                "description": "Fresh green vegetable salad",
                "prep_time": 5,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Memories Special Salad",
                "category": "Salads",
                "price": 300,
                "cost": 120,
                "description": "Special house salad with unique dressing",
                "prep_time": 12,
                "vegetarian": True,
                "featured": True,
            },
            # PIZZA
            {
                "name": "The Memories Pizza - 12''",
                "category": "Pizza",
                "price": 680,
                "cost": 300,
                "description": "Signature pizza with special toppings",
                "prep_time": 20,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "The Memories Pizza - 16''",
                "category": "Pizza",
                "price": 880,
                "cost": 400,
                "description": "Large signature pizza with special toppings",
                "prep_time": 25,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "The Chicken Pizza - 12''",
                "category": "Pizza",
                "price": 550,
                "cost": 250,
                "description": "Chicken pizza with cheese and vegetables",
                "prep_time": 18,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "The Chicken Pizza - 16''",
                "category": "Pizza",
                "price": 730,
                "cost": 330,
                "description": "Large chicken pizza with cheese and vegetables",
                "prep_time": 22,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Sausage Delight Pizza - 12''",
                "category": "Pizza",
                "price": 580,
                "cost": 270,
                "description": "Pizza with delicious sausages",
                "prep_time": 18,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Sausage Delight Pizza - 16''",
                "category": "Pizza",
                "price": 760,
                "cost": 350,
                "description": "Large pizza with delicious sausages",
                "prep_time": 22,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Margherita Pizza - 12''",
                "category": "Pizza",
                "price": 450,
                "cost": 200,
                "description": "Classic margherita with tomato and cheese",
                "prep_time": 15,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Margherita Pizza - 16''",
                "category": "Pizza",
                "price": 600,
                "cost": 280,
                "description": "Large classic margherita with tomato and cheese",
                "prep_time": 18,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Memories Special Pizza - 12''",
                "category": "Pizza",
                "price": 650,
                "cost": 300,
                "description": "House special pizza with unique blend",
                "prep_time": 20,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Memories Special Pizza - 16''",
                "category": "Pizza",
                "price": 850,
                "cost": 400,
                "description": "Large house special pizza with unique blend",
                "prep_time": 25,
                "vegetarian": False,
                "featured": True,
            },
            # CURRY
            {
                "name": "Chicken Masala (2+4+1/4)",
                "category": "Curries",
                "price": 230,
                "cost": 110,
                "description": "Spicy chicken masala curry",
                "prep_time": 35,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Prawn Masala (1/2+1/4)",
                "category": "Curries",
                "price": 260,
                "cost": 130,
                "description": "Rich prawn masala curry",
                "prep_time": 30,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Chicken Jalfrezi (1/2+1/4)",
                "category": "Curries",
                "price": 240,
                "cost": 120,
                "description": "Chicken jalfrezi with peppers and onions",
                "prep_time": 25,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Chicken Dry (1/2)",
                "category": "Curries",
                "price": 350,
                "cost": 170,
                "description": "Dry spiced chicken preparation",
                "prep_time": 30,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Hot Spice Chicken (1/2)",
                "category": "Curries",
                "price": 320,
                "cost": 150,
                "description": "Extra spicy hot chicken curry",
                "prep_time": 35,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Chicken Vegetable (1/2)",
                "category": "Curries",
                "price": 280,
                "cost": 130,
                "description": "Chicken curry with mixed vegetables",
                "prep_time": 30,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Masala Vegetable (1/2)",
                "category": "Curries",
                "price": 280,
                "cost": 120,
                "description": "Mixed vegetable masala curry",
                "prep_time": 25,
                "vegetarian": True,
                "featured": False,
            },
            # NOODLES/CHOP SUEY
            {
                "name": "Mixed Chowmein (1+1) 3+0+120",
                "category": "Noodles",
                "price": 320,
                "cost": 140,
                "description": "Mixed vegetable chowmein noodles",
                "prep_time": 15,
                "vegetarian": True,
                "featured": True,
            },
            {
                "name": "Prawn Chowmein (1+1) 8+0+180",
                "category": "Noodles",
                "price": 380,
                "cost": 170,
                "description": "Prawn chowmein with vegetables",
                "prep_time": 18,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "BBQ Chowmein (1+3)",
                "category": "Noodles",
                "price": 380,
                "cost": 170,
                "description": "BBQ flavored chowmein noodles",
                "prep_time": 20,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Vegetable Chop Suey (1+1)",
                "category": "Noodles",
                "price": 280,
                "cost": 120,
                "description": "Mixed vegetable chop suey",
                "prep_time": 15,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "American Chop Suey (1+3)",
                "category": "Noodles",
                "price": 320,
                "cost": 140,
                "description": "American style chop suey",
                "prep_time": 18,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Chicken Chop Suey",
                "category": "Noodles",
                "price": 360,
                "cost": 160,
                "description": "Chicken chop suey with vegetables",
                "prep_time": 20,
                "vegetarian": False,
                "featured": True,
            },
            # BURGERS
            {
                "name": "Crustic Burger",
                "category": "Burgers",
                "price": 180,
                "cost": 80,
                "description": "Crispy crustic style burger",
                "prep_time": 12,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "BBQ Chicken Cheese Burger",
                "category": "Burgers",
                "price": 200,
                "cost": 90,
                "description": "BBQ chicken burger with cheese",
                "prep_time": 15,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Cheesy Chicken Burger",
                "category": "Burgers",
                "price": 220,
                "cost": 100,
                "description": "Chicken burger loaded with cheese",
                "prep_time": 15,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Memories Delight Burger",
                "category": "Burgers",
                "price": 280,
                "cost": 130,
                "description": "Special house burger with unique flavors",
                "prep_time": 18,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Zinger Chicken Burger",
                "category": "Burgers",
                "price": 250,
                "cost": 120,
                "description": "Spicy zinger chicken burger",
                "prep_time": 15,
                "vegetarian": False,
                "featured": True,
            },
            # CHICKEN & WINGS
            {
                "name": "Hot Fried Chicken (6 Pcs)",
                "category": "Main Course",
                "price": 180,
                "cost": 80,
                "description": "Spicy hot fried chicken pieces",
                "prep_time": 20,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "BBQ Wings (6 Pcs)",
                "category": "Main Course",
                "price": 220,
                "cost": 100,
                "description": "Barbecue flavored chicken wings",
                "prep_time": 18,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Honey Wings (6 Pcs)",
                "category": "Main Course",
                "price": 260,
                "cost": 120,
                "description": "Honey glazed chicken wings",
                "prep_time": 18,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Chicken Lollipop (6 Pcs)",
                "category": "Main Course",
                "price": 280,
                "cost": 130,
                "description": "Chicken lollipop pieces",
                "prep_time": 22,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Popcorn Chicken",
                "category": "Main Course",
                "price": 250,
                "cost": 110,
                "description": "Bite-sized popcorn chicken",
                "prep_time": 15,
                "vegetarian": False,
                "featured": False,
            },
            # BIRYANIS
            {
                "name": "Chicken Kacchi",
                "category": "Rice & Biryanis",
                "price": 460,
                "cost": 220,
                "description": "Traditional kacchi biryani with chicken",
                "prep_time": 45,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Mutton Kacchi",
                "category": "Rice & Biryanis",
                "price": 580,
                "cost": 280,
                "description": "Premium mutton kacchi biryani",
                "prep_time": 50,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Hyderabadi Dum Biryani",
                "category": "Rice & Biryanis",
                "price": 450,
                "cost": 210,
                "description": "Authentic Hyderabadi style dum biryani",
                "prep_time": 40,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Mashroon Dum Biryani",
                "category": "Rice & Biryanis",
                "price": 460,
                "cost": 200,
                "description": "Mushroom dum biryani for vegetarians",
                "prep_time": 35,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Kachrhi Dum Biryani",
                "category": "Rice & Biryanis",
                "price": 350,
                "cost": 160,
                "description": "Mixed vegetable dum biryani",
                "prep_time": 35,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Teliaki Polo",
                "category": "Rice & Biryanis",
                "price": 380,
                "cost": 170,
                "description": "Traditional Bengali polao rice",
                "prep_time": 30,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Chicken Tikharki",
                "category": "Rice & Biryanis",
                "price": 520,
                "cost": 250,
                "description": "Chicken tikka with spiced rice",
                "prep_time": 35,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Khasi With Tehari Special Rice Dish",
                "category": "Rice & Biryanis",
                "price": 580,
                "cost": 280,
                "description": "Goat meat with special tehari rice",
                "prep_time": 45,
                "vegetarian": False,
                "featured": True,
            },
            # BEVERAGES & COFFEE
            {
                "name": "Hot Coffee",
                "category": "Beverages",
                "price": 180,
                "cost": 60,
                "description": "Freshly brewed hot coffee",
                "prep_time": 5,
                "vegetarian": True,
                "featured": True,
            },
            {
                "name": "Black Coffee",
                "category": "Beverages",
                "price": 120,
                "cost": 40,
                "description": "Strong black coffee",
                "prep_time": 3,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Chocolate Hot Coffee",
                "category": "Beverages",
                "price": 180,
                "cost": 70,
                "description": "Hot coffee with chocolate flavor",
                "prep_time": 5,
                "vegetarian": True,
                "featured": True,
            },
            {
                "name": "Iced Coffee",
                "category": "Beverages",
                "price": 180,
                "cost": 70,
                "description": "Refreshing iced coffee",
                "prep_time": 5,
                "vegetarian": True,
                "featured": True,
            },
            {
                "name": "Masala Hot Coffee",
                "category": "Beverages",
                "price": 200,
                "cost": 80,
                "description": "Spiced masala coffee",
                "prep_time": 8,
                "vegetarian": True,
                "featured": False,
            },
            # SHAKES & DESSERTS
            {
                "name": "Oreo Milk Shake",
                "category": "Beverages",
                "price": 200,
                "cost": 80,
                "description": "Creamy Oreo cookies milkshake",
                "prep_time": 5,
                "vegetarian": True,
                "featured": True,
            },
            {
                "name": "Kit Kat Shake",
                "category": "Beverages",
                "price": 220,
                "cost": 90,
                "description": "Kit Kat chocolate shake",
                "prep_time": 5,
                "vegetarian": True,
                "featured": True,
            },
            {
                "name": "Vanilla Shake",
                "category": "Beverages",
                "price": 180,
                "cost": 70,
                "description": "Classic vanilla milkshake",
                "prep_time": 5,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Strawberry Shake",
                "category": "Beverages",
                "price": 180,
                "cost": 70,
                "description": "Fresh strawberry milkshake",
                "prep_time": 5,
                "vegetarian": True,
                "featured": True,
            },
            {
                "name": "Strawberry Milk Shake",
                "category": "Beverages",
                "price": 180,
                "cost": 70,
                "description": "Creamy strawberry milk shake",
                "prep_time": 5,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Lassi",
                "category": "Beverages",
                "price": 100,
                "cost": 40,
                "description": "Traditional yogurt drink",
                "prep_time": 3,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Chocolate Lassi",
                "category": "Beverages",
                "price": 120,
                "cost": 50,
                "description": "Chocolate flavored lassi",
                "prep_time": 5,
                "vegetarian": True,
                "featured": False,
            },
            # DESSERTS
            {
                "name": "Borhani",
                "category": "Desserts",
                "price": 60,
                "cost": 20,
                "description": "Traditional Bengali yogurt drink with spices",
                "prep_time": 3,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Brown Sheerkoni",
                "category": "Desserts",
                "price": 100,
                "cost": 40,
                "description": "Rich brown colored sheerkoni dessert",
                "prep_time": 5,
                "vegetarian": True,
                "featured": False,
            },
            {
                "name": "Falint Sheerkoni",
                "category": "Desserts",
                "price": 200,
                "cost": 80,
                "description": "Special falint flavored sheerkoni",
                "prep_time": 5,
                "vegetarian": True,
                "featured": True,
            },
            {
                "name": "Karinwall Malai",
                "category": "Desserts",
                "price": 200,
                "cost": 80,
                "description": "Traditional malai dessert",
                "prep_time": 5,
                "vegetarian": True,
                "featured": False,
            },
            # KEBAB
            {
                "name": "Reshmi Laban Kabab (For 2 Person)",
                "category": "Grilled Items",
                "price": 600,
                "cost": 280,
                "description": "Silky smooth reshmi kebab for two people",
                "prep_time": 25,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Hariyai Malaikari Kebab",
                "category": "Grilled Items",
                "price": 280,
                "cost": 130,
                "description": "Green herb malaikari kebab",
                "prep_time": 20,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Butter Chicken Kebab",
                "category": "Grilled Items",
                "price": 300,
                "cost": 140,
                "description": "Rich butter chicken kebab",
                "prep_time": 22,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Chicken Cream Kebab",
                "category": "Grilled Items",
                "price": 300,
                "cost": 140,
                "description": "Creamy chicken kebab",
                "prep_time": 20,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Chicken Reshmi Kebab",
                "category": "Grilled Items",
                "price": 180,
                "cost": 80,
                "description": "Soft and silky chicken reshmi kebab",
                "prep_time": 18,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Chicken Tandoor Kebab",
                "category": "Grilled Items",
                "price": 180,
                "cost": 80,
                "description": "Traditional tandoor chicken kebab",
                "prep_time": 25,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Chicken BBQ Kebab",
                "category": "Grilled Items",
                "price": 200,
                "cost": 90,
                "description": "Barbecued chicken kebab",
                "prep_time": 20,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Chicken Hariyani Kebab",
                "category": "Grilled Items",
                "price": 200,
                "cost": 90,
                "description": "Green herbs marinated chicken kebab",
                "prep_time": 22,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Chicken Boryani Kebab",
                "category": "Grilled Items",
                "price": 200,
                "cost": 90,
                "description": "Biryani spiced chicken kebab",
                "prep_time": 20,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Chicken Thai Kebab",
                "category": "Grilled Items",
                "price": 200,
                "cost": 90,
                "description": "Thai style chicken kebab",
                "prep_time": 18,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Chicken Wings Kebab (4-5 Pcs)",
                "category": "Grilled Items",
                "price": 200,
                "cost": 90,
                "description": "Grilled chicken wings kebab",
                "prep_time": 20,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Chicken Selamat Kabab (1-5 Pcs)",
                "category": "Grilled Items",
                "price": 250,
                "cost": 110,
                "description": "Special selamat style chicken kebab",
                "prep_time": 25,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Chicken Motka Kebab",
                "category": "Grilled Items",
                "price": 350,
                "cost": 160,
                "description": "Clay pot style chicken kebab",
                "prep_time": 30,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Chicken Tikease Kebab",
                "category": "Grilled Items",
                "price": 220,
                "cost": 100,
                "description": "Special tikease style chicken kebab",
                "prep_time": 20,
                "vegetarian": False,
                "featured": False,
            },
            # SEA FOOD
            {
                "name": "Rupchanda Fish BBQ",
                "category": "Seafood",
                "price": 500,
                "cost": 250,
                "description": "Grilled rupchanda fish BBQ style",
                "prep_time": 25,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Tilapia Fish BBQ",
                "category": "Seafood",
                "price": 400,
                "cost": 200,
                "description": "Barbecued tilapia fish",
                "prep_time": 20,
                "vegetarian": False,
                "featured": True,
            },
            {
                "name": "Suleman Fish BBQ",
                "category": "Seafood",
                "price": 450,
                "cost": 220,
                "description": "Grilled suleman fish",
                "prep_time": 22,
                "vegetarian": False,
                "featured": False,
            },
            {
                "name": "Rullayga Fish BBQ",
                "category": "Seafood",
                "price": 450,
                "cost": 220,
                "description": "BBQ style rullayga fish",
                "prep_time": 25,
                "vegetarian": False,
                "featured": False,
            },
        ]

        # Limit to requested count
        if count < len(menu_items_data):
            menu_items_data = random.sample(menu_items_data, count)
        elif count > len(menu_items_data):
            # Duplicate some items to reach the count
            while len(menu_items_data) < count:
                original_item = random.choice(
                    menu_items_data[:20]
                )  # Pick from first 20
                new_item = original_item.copy()
                new_item["name"] = f"{original_item['name']} Special"
                new_item["price"] += random.randint(20, 100)
                new_item["cost"] += random.randint(10, 50)
                menu_items_data.append(new_item)

        menu_items = []
        with transaction.atomic():
            for item_data in menu_items_data:
                # Convert prices from integers to Decimal
                price = Decimal(str(item_data["price"]))
                cost = Decimal(str(item_data["cost"]))

                # Set random sales data
                total_sold = random.randint(0, 100)
                total_revenue = price * total_sold

                menu_item = MenuItem.objects.create(
                    name=item_data["name"],
                    category=item_data["category"],
                    description=item_data["description"],
                    price=price,
                    cost=cost,
                    available=random.choice([True, True, True, False]),  # 75% available
                    is_featured=item_data["featured"],
                    preparation_time=item_data["prep_time"],
                    is_vegetarian=item_data["vegetarian"],
                    is_vegan=(
                        random.choice([True, False])
                        if item_data["vegetarian"]
                        else False
                    ),
                    contains_gluten=random.choice([True, False]),
                    calories=random.randint(200, 800),
                    total_sold=total_sold,
                    total_revenue=total_revenue,
                    display_order=random.randint(1, 100),
                    ingredients=f"Fresh ingredients for {item_data['name'].lower()}",
                    short_description=item_data["description"][:100],
                )
                menu_items.append(menu_item)

        return menu_items

    def print_summary(self):
        """Print seeding summary"""
        self.stdout.write("\n📊 Menu Items Summary:")
        self.stdout.write("=" * 50)

        # Category summary
        categories = MenuCategory.objects.all()
        for category in categories:
            item_count = MenuItem.objects.filter(category=category.name).count()
            available_count = MenuItem.objects.filter(
                category=category.name, available=True
            ).count()
            self.stdout.write(
                f"📂 {category.name}: {item_count} items ({available_count} available)"
            )

        # Overall statistics
        total_items = MenuItem.objects.count()
        available_items = MenuItem.objects.filter(available=True).count()
        featured_items = MenuItem.objects.filter(is_featured=True).count()
        vegetarian_items = MenuItem.objects.filter(is_vegetarian=True).count()

        total_revenue = sum(item.total_revenue for item in MenuItem.objects.all())
        avg_price = MenuItem.objects.aggregate(models.Avg("price"))["price__avg"] or 0

        self.stdout.write("\n📈 Overall Statistics:")
        self.stdout.write("=" * 30)
        self.stdout.write(f"Total Items: {total_items}")
        self.stdout.write(f"Available: {available_items}")
        self.stdout.write(f"Featured: {featured_items}")
        self.stdout.write(f"Vegetarian: {vegetarian_items}")
        self.stdout.write(f"Total Revenue: ৳{total_revenue:,.2f}")
        self.stdout.write(f"Average Price: ৳{avg_price:.2f}")

        self.stdout.write("\n🎉 Seeding completed successfully!")
        self.stdout.write("You can now:")
        self.stdout.write("• Visit Django Admin to manage items")
        self.stdout.write("• Test the API endpoints")
        self.stdout.write("• View items in the frontend")
