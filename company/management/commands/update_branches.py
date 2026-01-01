from django.core.management.base import BaseCommand
from company.models import Branch


class Command(BaseCommand):
    help = "Update branch data with proper values for testing"

    def handle(self, *args, **options):
        branches = Branch.objects.all()

        for i, branch in enumerate(branches):
            if not branch.fullAddress:
                branch.fullAddress = f"Address for {branch.name}, {branch.city or 'Dhaka'}, {branch.country}"

            if not branch.manager_name:
                branch.manager_name = f"Manager {i+1}"

            if not branch.phoneNumber:
                branch.phoneNumber = f"01914039{i+100:03d}"

            # Set some demo operational data
            branch.todaySales = 1000 + (i * 500)
            branch.monthSales = 25000 + (i * 10000)
            branch.activeOrders = 5 + i
            branch.activeTables = 10 + (i * 2)
            branch.staff = 8 + i

            branch.save()
            self.stdout.write(f"Updated branch: {branch.name}")

        self.stdout.write(self.style.SUCCESS("Successfully updated branch data!"))
