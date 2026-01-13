from __future__ import annotations

from typing import Iterable

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "Repairs SQLite schema drift for the products app by creating missing tables "
        "and adding missing columns using Django's schema editor."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would change; do not apply schema edits.",
        )
        parser.add_argument(
            "--include-auto-created",
            action="store_true",
            help="Also check auto-created through tables (M2M).",
        )

    def handle(self, *args, **options):
        dry_run: bool = bool(options["dry_run"])
        include_auto_created: bool = bool(options["include_auto_created"])

        if connection.vendor != "sqlite":
            self.stdout.write(
                self.style.WARNING(
                    f"This command currently targets SQLite only (db vendor={connection.vendor})."
                )
            )
            return

        app_config = apps.get_app_config("products")
        models = list(app_config.get_models(include_auto_created=include_auto_created))

        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}

        created_tables: list[str] = []
        added_columns: list[str] = []

        # Use a single schema_editor session so it can batch operations safely.
        with connection.schema_editor() as schema_editor:
            for model in models:
                table = model._meta.db_table

                if table not in existing_tables:
                    msg = f"Missing table: {table} (model={model._meta.label})"
                    if dry_run:
                        self.stdout.write(f"[DRY] {msg} -> would create")
                    else:
                        self.stdout.write(msg + " -> creating")
                        schema_editor.create_model(model)
                        created_tables.append(table)
                    # After creating, no need to add fields.
                    continue

                db_cols = self._get_sqlite_columns(table)
                for field in model._meta.local_fields:
                    col = field.column
                    if col in db_cols:
                        continue

                    msg = f"Missing column: {table}.{col} (field={model._meta.label}.{field.name})"
                    if dry_run:
                        self.stdout.write(f"[DRY] {msg} -> would add")
                        continue

                    self.stdout.write(msg + " -> adding")
                    schema_editor.add_field(model, field)
                    added_columns.append(f"{table}.{col}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry-run complete."))
            return

        if created_tables:
            self.stdout.write(self.style.SUCCESS(f"Created tables: {len(created_tables)}"))
        if added_columns:
            self.stdout.write(self.style.SUCCESS(f"Added columns: {len(added_columns)}"))
        if not created_tables and not added_columns:
            self.stdout.write(self.style.SUCCESS("No schema changes needed."))

    def _get_sqlite_columns(self, table: str) -> set[str]:
        with connection.cursor() as cursor:
            cursor.execute(f"PRAGMA table_info('{table}')")
            return {row[1] for row in cursor.fetchall()}
