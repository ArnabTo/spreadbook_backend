from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from company.models import Company, Branch
from recipe_waste_management.models import Recipe, RecipeIngredient, WasteRecord
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()


class Command(BaseCommand):
    help = "Seed recipe and waste management data for The Memories Restaurant"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing recipe and waste data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing recipe and waste data...")
            WasteRecord.objects.all().delete()
            RecipeIngredient.objects.all().delete()
            Recipe.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Existing data cleared."))

        # Get or create company and user
        company, created = Company.objects.get_or_create(
            name="The Memories Restaurant",
            defaults={
                "email": "info@thememoriesrestaurant.com",
                "phone": "+880-123-456-7890",
                "address": "Dhaka, Bangladesh",
            },
        )

        user, created = User.objects.get_or_create(
            username="restaurant_admin",
            defaults={
                "email": "admin@thememoriesrestaurant.com",
                "name": "Restaurant Admin",
                "fullName": "Restaurant Admin",
                "companyId": company,
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
                "is_admin": True,
                "is_verified": True,
            },
        )

        if created:
            user.set_password("admin123")
            user.save()
            self.stdout.write(f"✓ Created user: {user.username}")

        # Seed Recipes
        recipes_data = [
            {
                "dish_name": "Pad Thai",
                "category": "thai",
                "serving_size": 1,
                "prep_time": 15,
                "cook_time": 10,
                "selling_price": Decimal("13.99"),
                "instructions": "1. Soak rice noodles in warm water for 30 minutes\n2. Heat oil in wok, stir-fry shrimp until pink\n3. Push shrimp to one side, add beaten eggs\n4. Add noodles and sauce, toss everything together\n5. Add bean sprouts and cook for 2 minutes\n6. Garnish with Thai basil and serve with lime",
                "ingredients": [
                    {
                        "name": "Rice Noodles",
                        "quantity": 200,
                        "unit": "g",
                        "cost": 0.80,
                    },
                    {"name": "Shrimp", "quantity": 100, "unit": "g", "cost": 3.50},
                    {"name": "Eggs", "quantity": 2, "unit": "pcs", "cost": 0.60},
                    {"name": "Bean Sprouts", "quantity": 50, "unit": "g", "cost": 0.20},
                    {"name": "Thai Basil", "quantity": 10, "unit": "g", "cost": 0.30},
                    {
                        "name": "Tamarind Sauce",
                        "quantity": 30,
                        "unit": "ml",
                        "cost": 0.50,
                    },
                ],
            },
            {
                "dish_name": "Chicken Seekh Kebab",
                "category": "kebab",
                "serving_size": 1,
                "prep_time": 20,
                "cook_time": 15,
                "selling_price": Decimal("12.99"),
                "instructions": "1. Mix ground chicken with finely chopped onions\n2. Add spice mix and yogurt, mix well\n3. Let marinate for 15 minutes\n4. Shape mixture around skewers\n5. Grill over medium-high heat for 12-15 minutes\n6. Turn occasionally for even cooking\n7. Serve hot with mint chutney and naan",
                "ingredients": [
                    {
                        "name": "Ground Chicken",
                        "quantity": 150,
                        "unit": "g",
                        "cost": 2.10,
                    },
                    {"name": "Onion", "quantity": 50, "unit": "g", "cost": 0.15},
                    {"name": "Spices Mix", "quantity": 10, "unit": "g", "cost": 0.40},
                    {"name": "Yogurt", "quantity": 30, "unit": "ml", "cost": 0.25},
                    {"name": "Cilantro", "quantity": 10, "unit": "g", "cost": 0.20},
                ],
            },
            {
                "dish_name": "Beef Biryani",
                "category": "indian",
                "serving_size": 1,
                "prep_time": 45,
                "cook_time": 60,
                "selling_price": Decimal("16.99"),
                "instructions": "1. Soak basmati rice for 30 minutes\n2. Marinate beef with yogurt and spices\n3. Cook rice until 70% done\n4. Layer rice and beef in heavy-bottom pot\n5. Cook on dum (slow cooking) for 45 minutes\n6. Garnish with fried onions and serve",
                "ingredients": [
                    {
                        "name": "Basmati Rice",
                        "quantity": 200,
                        "unit": "g",
                        "cost": 1.20,
                    },
                    {"name": "Beef Chunks", "quantity": 200, "unit": "g", "cost": 4.50},
                    {"name": "Yogurt", "quantity": 100, "unit": "ml", "cost": 0.50},
                    {
                        "name": "Biryani Spices",
                        "quantity": 15,
                        "unit": "g",
                        "cost": 0.80,
                    },
                    {"name": "Onions", "quantity": 100, "unit": "g", "cost": 0.30},
                    {"name": "Ghee", "quantity": 30, "unit": "ml", "cost": 0.70},
                ],
            },
            {
                "dish_name": "Fish Curry",
                "category": "seafood",
                "serving_size": 1,
                "prep_time": 20,
                "cook_time": 25,
                "selling_price": Decimal("14.99"),
                "instructions": "1. Cut fish into medium pieces\n2. Heat oil and fry onions until golden\n3. Add ginger-garlic paste and spices\n4. Add tomatoes and cook until soft\n5. Add coconut milk and bring to boil\n6. Add fish pieces and simmer for 15 minutes\n7. Garnish with curry leaves",
                "ingredients": [
                    {"name": "Fish Fillet", "quantity": 200, "unit": "g", "cost": 3.80},
                    {
                        "name": "Coconut Milk",
                        "quantity": 150,
                        "unit": "ml",
                        "cost": 0.90,
                    },
                    {"name": "Onions", "quantity": 80, "unit": "g", "cost": 0.25},
                    {"name": "Tomatoes", "quantity": 100, "unit": "g", "cost": 0.40},
                    {"name": "Curry Spices", "quantity": 12, "unit": "g", "cost": 0.60},
                    {"name": "Curry Leaves", "quantity": 5, "unit": "g", "cost": 0.15},
                ],
            },
            {
                "dish_name": "Vegetable Fried Rice",
                "category": "chinese",
                "serving_size": 1,
                "prep_time": 15,
                "cook_time": 12,
                "selling_price": Decimal("9.99"),
                "instructions": "1. Cook rice and let it cool completely\n2. Heat oil in wok over high heat\n3. Scramble eggs and set aside\n4. Stir-fry vegetables for 3-4 minutes\n5. Add cold rice and mix well\n6. Add soy sauce and seasonings\n7. Add back scrambled eggs and serve hot",
                "ingredients": [
                    {"name": "Cooked Rice", "quantity": 200, "unit": "g", "cost": 0.80},
                    {
                        "name": "Mixed Vegetables",
                        "quantity": 120,
                        "unit": "g",
                        "cost": 1.20,
                    },
                    {"name": "Eggs", "quantity": 2, "unit": "pcs", "cost": 0.60},
                    {"name": "Soy Sauce", "quantity": 20, "unit": "ml", "cost": 0.30},
                    {"name": "Garlic", "quantity": 10, "unit": "g", "cost": 0.15},
                    {
                        "name": "Spring Onions",
                        "quantity": 20,
                        "unit": "g",
                        "cost": 0.25,
                    },
                ],
            },
        ]

        self.stdout.write("Creating recipes...")
        for recipe_data in recipes_data:
            ingredients_data = recipe_data.pop("ingredients")

            recipe = Recipe.objects.create(
                company=company, created_by=user, **recipe_data
            )

            # Create ingredients
            for ingredient_data in ingredients_data:
                RecipeIngredient.objects.create(recipe=recipe, **ingredient_data)

            # Recalculate costs
            recipe.save()

            self.stdout.write(f"✓ Created recipe: {recipe.dish_name}")

        # Seed Waste Records
        waste_data = [
            {
                "date": date.today() - timedelta(days=2),
                "item_name": "Lettuce",
                "quantity": 2.5,
                "unit": "kg",
                "cost": 4.50,
                "reason": "spoiled",
                "notes": "Left in refrigerator too long, wilted and brown",
            },
            {
                "date": date.today() - timedelta(days=1),
                "item_name": "Cooked Rice",
                "quantity": 3.0,
                "unit": "kg",
                "cost": 6.00,
                "reason": "overproduction",
                "notes": "Prepared too much for lunch service, could not sell",
            },
            {
                "date": date.today(),
                "item_name": "Milk",
                "quantity": 1.5,
                "unit": "liters",
                "cost": 2.50,
                "reason": "expired",
                "notes": "Past expiration date, sour smell",
            },
            {
                "date": date.today() - timedelta(days=3),
                "item_name": "Bread Rolls",
                "quantity": 12,
                "unit": "pcs",
                "cost": 3.60,
                "reason": "damaged",
                "notes": "Dropped on floor during busy service",
            },
            {
                "date": date.today() - timedelta(days=4),
                "item_name": "Chicken Pieces",
                "quantity": 1.2,
                "unit": "kg",
                "cost": 8.40,
                "reason": "spoiled",
                "notes": "Freezer malfunction overnight, had to discard",
            },
            {
                "date": date.today() - timedelta(days=5),
                "item_name": "Tomatoes",
                "quantity": 2.0,
                "unit": "kg",
                "cost": 3.20,
                "reason": "overproduction",
                "notes": "Ordered too much for weekend rush that did not materialize",
            },
        ]

        self.stdout.write("Creating waste records...")
        for waste_record in waste_data:
            WasteRecord.objects.create(
                company=company, recorded_by=user, **waste_record
            )
            self.stdout.write(f'✓ Created waste record: {waste_record["item_name"]}')

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {len(recipes_data)} recipes and {len(waste_data)} waste records for The Memories Restaurant!"
            )
        )
