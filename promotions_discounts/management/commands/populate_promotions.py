from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from company.models import Company, Branch
from authenticator.models import User
from promotions_discounts.models import Promotion


class Command(BaseCommand):
    help = "Populate promotions and discounts with sample data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-id",
            type=str,
            help="Specific company ID to create promotions for",
        )

    def handle(self, *args, **options):
        company_id = options.get("company_id")

        if company_id:
            try:
                companies = [Company.objects.get(id=company_id)]
            except Company.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Company with ID {company_id} does not exist")
                )
                return
        else:
            companies = Company.objects.all()

        if not companies.exists():
            self.stdout.write(
                self.style.ERROR("No companies found. Please create a company first.")
            )
            return

        # Sample promotion data matching frontend interface
        sample_promotions = [
            {
                "name": "Happy Hour 20% OFF",
                "type": "percentage",
                "value": 20.00,
                "code": "HAPPY20",
                "start_date": timezone.now(),
                "end_date": timezone.now() + timedelta(days=90),
                "min_order_value": 0.00,
                "max_discount": 50.00,
                "usage_limit": 1000,
                "applicable_on": "category",
                "target_items": ["Drinks"],
                "status": "active",
                "description": "Happy hour special on all drinks",
            },
            {
                "name": "Weekend Special",
                "type": "fixed",
                "value": 10.00,
                "code": "WEEKEND10",
                "start_date": timezone.now(),
                "end_date": timezone.now() + timedelta(days=60),
                "min_order_value": 50.00,
                "max_discount": 10.00,
                "usage_limit": 500,
                "applicable_on": "all",
                "target_items": [],
                "status": "active",
                "description": "$10 off on orders above $50 during weekends",
            },
            {
                "name": "Buy 1 Get 1 Kebab",
                "type": "bogo",
                "value": 100.00,
                "code": "BOGO-KEBAB",
                "start_date": timezone.now() + timedelta(days=7),
                "end_date": timezone.now() + timedelta(days=30),
                "min_order_value": 0.00,
                "max_discount": 999.00,
                "usage_limit": 200,
                "applicable_on": "category",
                "target_items": ["Kebab"],
                "status": "scheduled",
                "description": "Buy one get one free on all kebab items",
            },
            {
                "name": "First Order Discount",
                "type": "percentage",
                "value": 25.00,
                "code": "FIRST25",
                "start_date": timezone.now(),
                "end_date": timezone.now() + timedelta(days=365),
                "min_order_value": 30.00,
                "max_discount": 15.00,
                "usage_limit": 9999,
                "applicable_on": "all",
                "target_items": [],
                "status": "active",
                "description": "25% off for first-time customers",
            },
            {
                "name": "Summer Special 15% OFF",
                "type": "percentage",
                "value": 15.00,
                "code": "SUMMER15",
                "start_date": timezone.now(),
                "end_date": timezone.now() + timedelta(days=45),
                "min_order_value": 25.00,
                "max_discount": 30.00,
                "usage_limit": 750,
                "applicable_on": "all",
                "target_items": [],
                "status": "active",
                "description": "Summer special 15% discount on all items",
            },
            {
                "name": "Free Dessert Promo",
                "type": "freeItem",
                "value": 0.00,
                "code": "FREEDESSERT",
                "start_date": timezone.now(),
                "end_date": timezone.now() + timedelta(days=30),
                "min_order_value": 75.00,
                "max_discount": 12.00,
                "usage_limit": 300,
                "applicable_on": "category",
                "target_items": ["Desserts"],
                "status": "active",
                "description": "Free dessert on orders above $75",
            },
        ]

        created_count = 0

        for company in companies:
            # Get admin user for this company
            admin_user = User.objects.filter(
                companyId=company, role__in=["admin", "super_admin", "manager"]
            ).first()

            if not admin_user:
                admin_user = User.objects.filter(companyId=company).first()

            for promo_data in sample_promotions:
                # Check if promotion with this code already exists for this company
                existing = Promotion.objects.filter(
                    company=company, code=promo_data["code"]
                ).exists()

                if existing:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Promotion {promo_data["code"]} already exists for {company.name}'
                        )
                    )
                    continue

                # Create promotion
                promotion = Promotion.objects.create(
                    company=company, created_by=admin_user, **promo_data
                )

                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created promotion: {promotion.name} ({promotion.code}) for {company.name}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {created_count} promotions across {len(companies)} companies"
            )
        )

        # Display summary
        total_promotions = Promotion.objects.count()
        active_promotions = Promotion.objects.filter(status="active").count()
        scheduled_promotions = Promotion.objects.filter(status="scheduled").count()

        self.stdout.write("\n=== PROMOTION SUMMARY ===")
        self.stdout.write(f"Total promotions: {total_promotions}")
        self.stdout.write(f"Active promotions: {active_promotions}")
        self.stdout.write(f"Scheduled promotions: {scheduled_promotions}")
        self.stdout.write("==========================")
