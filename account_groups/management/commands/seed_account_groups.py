from django.core.management.base import BaseCommand
from account_groups.models import AccountGroupParent

SEED_DATA = [
    "Assets", "Bank", "Capital Account", "Cash", "Creditor",
    "Current Assets", "Current Liability", "Debtor", "Direct Expense",
    "Direct Income", "Duties And Taxes", "Employee Account", "Expense",
    "Fixed Assets", "Income", "Indirect Expense", "Indirect Income",
    "Liabilities", "Manpower Group", "Purchase", "Salary Payable A/C",
    "Sales", "Sales Advance Group",
]


class Command(BaseCommand):
    help = "Seed AccountGroupParent records (idempotent)"

    def handle(self, *args, **options):
        created_count = 0
        for entry in SEED_DATA:
            _, was_created = AccountGroupParent.objects.get_or_create(name=entry)
            if was_created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  + Created: {entry}"))

        if created_count:
            self.stdout.write(
                self.style.SUCCESS(f"\nSeeded {created_count} new AccountGroupParent records.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("All AccountGroupParent records already exist. Nothing to seed.")
            )
