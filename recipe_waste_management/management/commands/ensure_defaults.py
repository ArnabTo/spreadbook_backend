from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from company.models import Company


class Command(BaseCommand):
    help = "Ensure default user and company exist for testing"

    def handle(self, *args, **options):
        User = get_user_model()

        # Create default user if none exists
        if not User.objects.exists():
            user = User.objects.create_user(
                username="default_user",
                email="default@test.com",
                password="testpass123",
                first_name="Default",
                last_name="User",
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created default user: {user.username}")
            )
        else:
            self.stdout.write("Default user already exists")

        # Create default company if none exists
        if not Company.objects.exists():
            company = Company.objects.create(
                name="Test Restaurant",
                address="123 Test Street",
                phone="123-456-7890",
                email="test@restaurant.com",
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created default company: {company.name}")
            )
        else:
            self.stdout.write("Default company already exists")

        self.stdout.write(self.style.SUCCESS("Default entities are ready!"))
