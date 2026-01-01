from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, time, timedelta
import random
from booking.models import Booking


class Command(BaseCommand):
    help = "Create sample booking data for testing and demonstration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=50,
            help="Number of bookings to create (default: 50)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing bookings before creating new ones",
        )

    def handle(self, *args, **options):
        count = options["count"]
        clear = options["clear"]

        if clear:
            deleted_count = Booking.objects.count()
            Booking.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {deleted_count} existing bookings")
            )

        # Sample customer data
        customers = [
            {
                "name": "Ahmed Hassan",
                "phone": "+8801712345678",
                "email": "ahmed.hassan@email.com",
            },
            {
                "name": "Fatima Rahman",
                "phone": "+8801823456789",
                "email": "fatima.rahman@email.com",
            },
            {
                "name": "Mohammad Ali",
                "phone": "+8801934567890",
                "email": "mohammad.ali@email.com",
            },
            {
                "name": "Rashida Begum",
                "phone": "+8801745678901",
                "email": "rashida.begum@email.com",
            },
            {
                "name": "Karim Uddin",
                "phone": "+8801856789012",
                "email": "karim.uddin@email.com",
            },
            {
                "name": "Nasreen Akter",
                "phone": "+8801967890123",
                "email": "nasreen.akter@email.com",
            },
            {
                "name": "Ibrahim Khan",
                "phone": "+8801778901234",
                "email": "ibrahim.khan@email.com",
            },
            {
                "name": "Salma Khatun",
                "phone": "+8801889012345",
                "email": "salma.khatun@email.com",
            },
            {
                "name": "Rafiq Ahmed",
                "phone": "+8801790123456",
                "email": "rafiq.ahmed@email.com",
            },
            {
                "name": "Rokeya Sultana",
                "phone": "+8801801234567",
                "email": "rokeya.sultana@email.com",
            },
            {
                "name": "Habibur Rahman",
                "phone": "+8801912345678",
                "email": "habibur.rahman@email.com",
            },
            {
                "name": "Amina Khatun",
                "phone": "+8801723456789",
                "email": "amina.khatun@email.com",
            },
            {
                "name": "Mizanur Rahman",
                "phone": "+8801834567890",
                "email": "mizanur.rahman@email.com",
            },
            {
                "name": "Shahida Begum",
                "phone": "+8801945678901",
                "email": "shahida.begum@email.com",
            },
            {
                "name": "Abdul Karim",
                "phone": "+8801756789012",
                "email": "abdul.karim@email.com",
            },
            {
                "name": "Rehana Akter",
                "phone": "+8801867890123",
                "email": "rehana.akter@email.com",
            },
            {
                "name": "Mamun Hossain",
                "phone": "+8801978901234",
                "email": "mamun.hossain@email.com",
            },
            {
                "name": "Kulsum Begum",
                "phone": "+8801689012345",
                "email": "kulsum.begum@email.com",
            },
            {
                "name": "Fazlul Haque",
                "phone": "+8801790123457",
                "email": "fazlul.haque@email.com",
            },
            {
                "name": "Jahanara Begum",
                "phone": "+8801801234568",
                "email": "jahanara.begum@email.com",
            },
        ]

        # Sample table names
        tables = [
            "Table 1",
            "Table 2",
            "Table 3",
            "Table 4",
            "Table 5",
            "Table 6",
            "Table 7",
            "Table 8",
            "Table 9",
            "Table 10",
            "Table 11",
            "Table 12",
            "Table 13",
            "Table 14",
            "Table 15",
            "VIP Table 1",
            "VIP Table 2",
            "VIP Table 3",
            "Garden Table 1",
            "Garden Table 2",
            "Garden Table 3",
            "Private Room A",
            "Private Room B",
            "Balcony Table 1",
            "Balcony Table 2",
        ]

        # Time slots for restaurant bookings
        time_slots = [
            time(12, 0),  # 12:00 PM
            time(12, 30),  # 12:30 PM
            time(13, 0),  # 1:00 PM
            time(13, 30),  # 1:30 PM
            time(14, 0),  # 2:00 PM
            time(14, 30),  # 2:30 PM
            time(18, 0),  # 6:00 PM
            time(18, 30),  # 6:30 PM
            time(19, 0),  # 7:00 PM
            time(19, 30),  # 7:30 PM
            time(20, 0),  # 8:00 PM
            time(20, 30),  # 8:30 PM
            time(21, 0),  # 9:00 PM
            time(21, 30),  # 9:30 PM
        ]

        # Status distribution (weighted)
        status_choices = ["pending", "confirmed", "cancelled", "completed"]
        status_weights = [0.2, 0.5, 0.1, 0.2]  # Most bookings should be confirmed

        # Special occasion notes
        special_notes = [
            "Birthday celebration",
            "Anniversary dinner",
            "Business meeting",
            "Family gathering",
            "Date night",
            "Graduation celebration",
            "Wedding anniversary",
            "First date",
            "Proposal dinner",
            "Team lunch",
            "Client dinner",
            "Retirement party",
            "Baby shower",
            "Reunion dinner",
            "",  # Empty note for regular bookings
            "",
            "",
            "",
        ]

        bookings_created = 0
        today = timezone.now().date()

        # Create bookings spanning from 30 days ago to 60 days in the future
        start_date = today - timedelta(days=30)
        end_date = today + timedelta(days=60)

        for _ in range(count):
            # Random date within range
            random_days = random.randint(0, (end_date - start_date).days)
            booking_date = start_date + timedelta(days=random_days)

            # Determine status based on date
            if booking_date < today:
                # Past bookings are either completed or cancelled
                status = random.choices(["completed", "cancelled"], weights=[0.8, 0.2])[
                    0
                ]
            elif booking_date == today:
                # Today's bookings can be any status
                status = random.choices(status_choices, weights=[0.1, 0.6, 0.1, 0.2])[0]
            else:
                # Future bookings are pending or confirmed
                status = random.choices(["pending", "confirmed"], weights=[0.3, 0.7])[0]

            # Random customer
            customer = random.choice(customers)

            # Random guest count (weighted towards smaller groups)
            guest_weights = [0.1, 0.25, 0.2, 0.15, 0.1, 0.08, 0.05, 0.03, 0.02, 0.02]
            guests = random.choices(range(1, 11), weights=guest_weights)[0]

            # Larger groups more likely to get VIP/Private tables
            if guests >= 8:
                available_tables = [
                    t for t in tables if "VIP" in t or "Private" in t or "Garden" in t
                ]
            elif guests >= 6:
                available_tables = [
                    t
                    for t in tables
                    if "VIP" in t
                    or "Garden" in t
                    or "Balcony" in t
                    or t.startswith("Table")
                ]
            else:
                available_tables = tables

            try:
                booking = Booking.objects.create(
                    customer_name=customer["name"],
                    phone=customer["phone"],
                    email=customer["email"],
                    date=booking_date,
                    time=random.choice(time_slots),
                    guests=guests,
                    table=random.choice(available_tables),
                    status=status,
                    notes=random.choice(special_notes),
                )
                bookings_created += 1

                if bookings_created % 10 == 0:
                    self.stdout.write(f"Created {bookings_created} bookings...")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating booking: {e}"))
                continue

        # Display summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(
            self.style.SUCCESS(f"✅ Successfully created {bookings_created} bookings!")
        )

        # Show statistics
        total_bookings = Booking.objects.count()
        status_stats = {}
        for status_choice in ["pending", "confirmed", "cancelled", "completed"]:
            count = Booking.objects.filter(status=status_choice).count()
            status_stats[status_choice] = count

        self.stdout.write("\n📊 Booking Statistics:")
        self.stdout.write(f"Total bookings: {total_bookings}")
        for status, count in status_stats.items():
            percentage = (count / total_bookings * 100) if total_bookings > 0 else 0
            self.stdout.write(f"{status.capitalize()}: {count} ({percentage:.1f}%)")

        # Show recent bookings
        today_bookings = Booking.objects.filter(date=today).count()
        upcoming_bookings = Booking.objects.filter(date__gt=today).count()
        past_bookings = Booking.objects.filter(date__lt=today).count()

        self.stdout.write("\n📅 Date Distribution:")
        self.stdout.write(f"Past bookings: {past_bookings}")
        self.stdout.write(f"Today's bookings: {today_bookings}")
        self.stdout.write(f"Upcoming bookings: {upcoming_bookings}")

        self.stdout.write("\n🎯 Next Steps:")
        self.stdout.write("• Run the development server: python manage.py runserver")
        self.stdout.write("• Test API endpoints: http://localhost:8000/api/bookings/")
        self.stdout.write("• Access Django admin: http://localhost:8000/admin/")
        self.stdout.write(
            self.style.SUCCESS("\n🎉 Booking system is ready for testing!")
        )
