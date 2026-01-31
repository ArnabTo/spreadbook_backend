from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = (
        "Backfill ProductBranchInventory for legacy branch-scoped Products. "
        "This is safe to run multiple times.\n\n"
        "It creates (product, branch) rows ONLY for products that already have product.branch set. "
        "Shared catalog products (product.branch is NULL) are not expanded to all branches."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))

        from products.models import Product, ProductBranchInventory

        qs = (
            Product.objects.select_related("companyId", "branch")
            .filter(branch__isnull=False)
            .only(
                "id",
                "companyId_id",
                "branch_id",
                "price",
                "priceSale",
                "regular_price",
                "in_stock",
                "available",
                "low_stock_threshold",
            )
        )

        created = 0
        skipped = 0
        for p in qs.iterator(chunk_size=500):
            exists = ProductBranchInventory.objects.filter(
                product_id=p.id, branch_id=p.branch_id
            ).exists()
            if exists:
                skipped += 1
                continue

            if dry_run:
                created += 1
                continue

            ProductBranchInventory.objects.create(
                product_id=p.id,
                branch_id=p.branch_id,
                companyId_id=p.companyId_id,
                price=p.price or 0,
                priceSale=p.priceSale or 0,
                regular_price=p.regular_price or 0,
                in_stock=int(p.in_stock or 0),
                available=int(p.available or (p.in_stock or 0)),
                low_stock_threshold=int(getattr(p, "low_stock_threshold", 20) or 20),
            )
            created += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: would create {created} ProductBranchInventory rows; {skipped} already existed"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {created} ProductBranchInventory rows; {skipped} already existed"
                )
            )
