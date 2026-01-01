from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class _DryRunRollback(Exception):
    pass


@dataclass
class BackfillTarget:
    label: str
    model: object
    has_branch: bool = True


class Command(BaseCommand):
    help = (
        "Backfill companyId/branch fields for existing rows (multi-tenant hardening). "
        "Safe by default: requires explicit --company-id unless there is exactly one Company."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-id",
            dest="company_id",
            default=None,
            help="Company UUID/PK to set on rows where companyId is NULL.",
        )
        parser.add_argument(
            "--branch-id",
            dest="branch_id",
            default=None,
            help="Branch UUID/PK to set on rows where branch is NULL (optional).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change without writing to DB.",
        )
        parser.add_argument(
            "--include-suppliers",
            action="store_true",
            help="Also backfill suppliers.companyId when NULL.",
        )

    def handle(self, *args, **options):
        from company.models import Company, Branch
        from customers.models import Customer
        from menu_items.models import MenuCategory, MenuItem
        from sales.models import Sale
        from table_managment.models import Table

        include_suppliers = bool(options["include_suppliers"])
        dry_run = bool(options["dry_run"])

        company_id = options.get("company_id")
        branch_id = options.get("branch_id")

        if company_id is None:
            companies = Company.objects.all()
            if companies.count() == 1:
                company = companies.first()
                company_id = str(company.id)
                self.stdout.write(
                    self.style.WARNING(
                        f"No --company-id provided; using sole company: {company_id}"
                    )
                )
            else:
                raise CommandError(
                    "Multiple companies found; please pass --company-id explicitly."
                )

        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist as exc:
            raise CommandError(f"Company not found: {company_id}") from exc

        branch: Optional[Branch] = None
        if branch_id is not None:
            try:
                branch = Branch.objects.get(id=branch_id)
            except Branch.DoesNotExist as exc:
                raise CommandError(f"Branch not found: {branch_id}") from exc
            if str(branch.company_id) != str(company.id):
                raise CommandError("Branch does not belong to provided company")

        targets = [
            BackfillTarget("customers.Customer", Customer),
            BackfillTarget("menu_items.MenuCategory", MenuCategory),
            BackfillTarget("menu_items.MenuItem", MenuItem),
            BackfillTarget("table_managment.Table", Table),
            BackfillTarget("sales.Sale", Sale),
        ]

        if include_suppliers:
            from suppliers.models import Supplier

            targets.append(
                BackfillTarget("suppliers.Supplier", Supplier, has_branch=False)
            )

        total_updates = 0

        try:
            with transaction.atomic():
                for target in targets:
                    qs = target.model.objects.filter(companyId__isnull=True)
                    missing_company = qs.count()

                    if missing_company:
                        self.stdout.write(
                            f"{target.label}: {missing_company} rows missing companyId"
                        )
                        if not dry_run:
                            updated = qs.update(companyId=company)
                            total_updates += updated

                    if branch is not None and target.has_branch:
                        qs_branch = target.model.objects.filter(
                            companyId=company, branch__isnull=True
                        )
                        missing_branch = qs_branch.count()
                        if missing_branch:
                            self.stdout.write(
                                f"{target.label}: {missing_branch} rows missing branch (companyId={company.id})"
                            )
                            if not dry_run:
                                updated = qs_branch.update(branch=branch)
                                total_updates += updated

                # Special-case: Sales can often infer company/branch from served_by
                # This runs AFTER generic company fill, only for remaining NULLs.
                sale_qs = Sale.objects.filter(
                    companyId__isnull=True, served_by__isnull=False
                )
                inferable = sale_qs.count()
                if inferable:
                    self.stdout.write(
                        f"sales.Sale: {inferable} rows can infer companyId from served_by"
                    )
                    if not dry_run:
                        updated_rows = 0
                        for sale in sale_qs.select_related(
                            "served_by", "served_by__companyId"
                        ):
                            if sale.served_by and sale.served_by.companyId:
                                sale.companyId = sale.served_by.companyId
                                # If the user has exactly one branch, set it
                                if (
                                    sale.branch_id is None
                                    and sale.served_by.branchAccess.count() == 1
                                ):
                                    sale.branch = sale.served_by.branchAccess.first()
                                sale.save(update_fields=["companyId", "branch"])
                                updated_rows += 1
                        total_updates += updated_rows

                if dry_run:
                    raise _DryRunRollback()
        except _DryRunRollback:
            self.stdout.write(
                self.style.WARNING("Dry-run complete (no changes written).")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"Backfill complete. Updated rows: {total_updates}")
        )
