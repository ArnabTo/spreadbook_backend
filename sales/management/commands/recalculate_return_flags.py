from __future__ import annotations

from django.core.management.base import BaseCommand

from sales.models import Sale
from sales.refund_utils import recalculate_sale_is_return


class Command(BaseCommand):
    help = "Recalculate Sale.is_return for orders that have refunds."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Recalculate for all orders (slower). Default: only orders with refunds.",
        )

    def handle(self, *args, **options):
        only_with_refunds = not bool(options.get("all"))

        qs = Sale.objects.all()
        if only_with_refunds:
            qs = qs.filter(refunds__isnull=False).distinct()

        total = qs.count()
        updated = 0

        for sale in qs.iterator():
            before = bool(sale.is_return)
            after = bool(recalculate_sale_is_return(sale))
            if before != after:
                updated += 1

        scope = "orders with refunds" if only_with_refunds else "all orders"
        self.stdout.write(
            self.style.SUCCESS(
                f"Recalculated return flags for {total} {scope}. Updated: {updated}."
            )
        )
