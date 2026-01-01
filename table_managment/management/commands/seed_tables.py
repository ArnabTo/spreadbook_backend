from django.core.management.base import BaseCommand
from django.utils import timezone
from table_managment.models import Table, TableOccupation, TableReservation
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = "Seed database with sample table data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing table data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing table data...")
            Table.objects.all().delete()
            TableOccupation.objects.all().delete()
            TableReservation.objects.all().delete()

        # Create tables
        self.stdout.write("Creating tables...")

        tables_data = [
            {
                "number": 1,
                "seats": 2,
                "section": "Main Dining",
                "floor": "Ground Floor",
                "table_type": "Regular",
            },
            {
                "number": 2,
                "seats": 4,
                "section": "Main Dining",
                "floor": "Ground Floor",
                "table_type": "Regular",
            },
            {
                "number": 3,
                "seats": 2,
                "section": "Main Dining",
                "floor": "Ground Floor",
                "table_type": "Regular",
            },
            {
                "number": 4,
                "seats": 6,
                "section": "Main Dining",
                "floor": "Ground Floor",
                "table_type": "Family",
            },
            {
                "number": 5,
                "seats": 4,
                "section": "Main Dining",
                "floor": "Ground Floor",
                "table_type": "Regular",
            },
            {
                "number": 6,
                "seats": 2,
                "section": "Window Side",
                "floor": "Ground Floor",
                "table_type": "Window",
            },
            {
                "number": 7,
                "seats": 4,
                "section": "Window Side",
                "floor": "Ground Floor",
                "table_type": "Window",
            },
            {
                "number": 8,
                "seats": 8,
                "section": "VIP Section",
                "floor": "Ground Floor",
                "table_type": "VIP",
            },
            {
                "number": 9,
                "seats": 2,
                "section": "Patio",
                "floor": "Ground Floor",
                "table_type": "Outdoor",
            },
            {
                "number": 10,
                "seats": 4,
                "section": "Patio",
                "floor": "Ground Floor",
                "table_type": "Outdoor",
            },
            {
                "number": 11,
                "seats": 4,
                "section": "Upper Dining",
                "floor": "First Floor",
                "table_type": "Regular",
            },
            {
                "number": 12,
                "seats": 6,
                "section": "Upper Dining",
                "floor": "First Floor",
                "table_type": "Family",
            },
        ]

        created_tables = []
        for table_data in tables_data:
            table, created = Table.objects.get_or_create(
                number=table_data["number"], defaults=table_data
            )
            created_tables.append(table)
            if created:
                self.stdout.write(f"Created table {table.number}")
            else:
                self.stdout.write(f"Table {table.number} already exists")

        # Set some tables as occupied/reserved with sample data
        self.stdout.write("Creating sample occupations...")

        # Sample waiters
        waiters = ["John", "Sarah", "Mike", "Emma", "David", "Lisa"]

        # Create some occupied tables
        occupied_tables = [2, 5, 8, 12]
        for table_num in occupied_tables:
            try:
                table = Table.objects.get(number=table_num)

                # Create occupation
                occupation = TableOccupation.objects.create(
                    table=table,
                    customer_name=f"Customer {table_num}",
                    customer_phone=f"+880171234567{table_num}",
                    party_size=random.randint(1, min(table.seats, 6)),
                    waiter=random.choice(waiters),
                    order_amount=round(random.uniform(50, 500), 2),
                    notes=f"Table occupied via seeding command",
                )

                # Update table status
                table.status = "occupied"
                table.save()

                self.stdout.write(f"Created occupation for table {table.number}")

            except Table.DoesNotExist:
                self.stdout.write(f"Table {table_num} not found")

        # Create some reservations
        self.stdout.write("Creating sample reservations...")

        reserved_tables = [4, 10]
        for table_num in reserved_tables:
            try:
                table = Table.objects.get(number=table_num)

                # Create future reservation
                reservation_time = timezone.now() + timedelta(
                    hours=random.randint(1, 8)
                )

                reservation = TableReservation.objects.create(
                    table=table,
                    customer_name=f"Smith Family" if table_num == 4 else "Johnson",
                    customer_phone=f"+880181234567{table_num}",
                    customer_email=f"customer{table_num}@example.com",
                    party_size=random.randint(2, min(table.seats, 6)),
                    reservation_time=reservation_time,
                    duration_hours=2.0,
                    status="confirmed",
                    special_requests=(
                        "Window seat preferred"
                        if table_num == 4
                        else "Birthday celebration"
                    ),
                )

                # Update table status
                table.status = "reserved"
                table.save()

                self.stdout.write(f"Created reservation for table {table.number}")

            except Table.DoesNotExist:
                self.stdout.write(f"Table {table_num} not found")

        # Summary
        total_tables = Table.objects.count()
        occupied_count = Table.objects.filter(status="occupied").count()
        reserved_count = Table.objects.filter(status="reserved").count()
        available_count = Table.objects.filter(status="available").count()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTable seeding completed successfully!\n"
                f"Total tables: {total_tables}\n"
                f"Available: {available_count}\n"
                f"Occupied: {occupied_count}\n"
                f"Reserved: {reserved_count}"
            )
        )
