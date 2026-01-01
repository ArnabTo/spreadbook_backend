"""
Quick booking data seeder - Run this in Django shell
Usage:
  python manage.py shell
  >>> exec(open('quick_seed.py').read())
"""

from booking.models import Booking
from datetime import date, time

# Clear existing data
print("Clearing existing bookings...")
Booking.objects.all().delete()

# Quick sample data
bookings = [
    {
        "customer_name": "Ahmed Hassan",
        "phone": "+8801712345678",
        "email": "ahmed.hassan@email.com",
        "date": date(2024, 11, 8),
        "time": time(19, 0),
        "guests": 4,
        "table": "Table 5",
        "status": "confirmed",
        "notes": "Birthday celebration",
    },
    {
        "customer_name": "Fatima Rahman",
        "phone": "+8801823456789",
        "email": "fatima.rahman@email.com",
        "date": date(2024, 11, 9),
        "time": time(20, 30),
        "guests": 2,
        "table": "VIP Table 1",
        "status": "pending",
        "notes": "Anniversary dinner",
    },
    {
        "customer_name": "Mohammad Ali",
        "phone": "+8801934567890",
        "email": "mohammad.ali@email.com",
        "date": date(2024, 11, 7),
        "time": time(18, 30),
        "guests": 6,
        "table": "Table 12",
        "status": "confirmed",
        "notes": "Business meeting",
    },
    {
        "customer_name": "Rashida Begum",
        "phone": "+8801745678901",
        "email": "rashida.begum@email.com",
        "date": date(2024, 11, 10),
        "time": time(13, 0),
        "guests": 8,
        "table": "Private Room A",
        "status": "confirmed",
        "notes": "Family gathering",
    },
    {
        "customer_name": "Karim Uddin",
        "phone": "+8801856789012",
        "email": "karim.uddin@email.com",
        "date": date(2024, 11, 12),
        "time": time(19, 30),
        "guests": 3,
        "table": "Garden Table 1",
        "status": "pending",
        "notes": "Date night",
    },
    {
        "customer_name": "Nasreen Akter",
        "phone": "+8801967890123",
        "email": "nasreen.akter@email.com",
        "date": date(2024, 11, 5),
        "time": time(20, 0),
        "guests": 4,
        "table": "Table 8",
        "status": "completed",
        "notes": "Graduation celebration",
    },
    {
        "customer_name": "Ibrahim Khan",
        "phone": "+8801778901234",
        "email": "ibrahim.khan@email.com",
        "date": date(2024, 11, 15),
        "time": time(18, 0),
        "guests": 2,
        "table": "Balcony Table 1",
        "status": "confirmed",
        "notes": "Proposal dinner",
    },
    {
        "customer_name": "Salma Khatun",
        "phone": "+8801889012345",
        "email": "salma.khatun@email.com",
        "date": date(2024, 11, 11),
        "time": time(12, 30),
        "guests": 5,
        "table": "Table 3",
        "status": "pending",
        "notes": "Team lunch",
    },
    {
        "customer_name": "Rafiq Ahmed",
        "phone": "+8801790123456",
        "email": "rafiq.ahmed@email.com",
        "date": date(2024, 11, 4),
        "time": time(21, 0),
        "guests": 3,
        "table": "Table 7",
        "status": "cancelled",
        "notes": "Client dinner",
    },
    {
        "customer_name": "Rokeya Sultana",
        "phone": "+8801801234567",
        "email": "rokeya.sultana@email.com",
        "date": date(2024, 11, 20),
        "time": time(14, 0),
        "guests": 10,
        "table": "Private Room B",
        "status": "confirmed",
        "notes": "Retirement party",
    },
]

# Create bookings
created = 0
for booking_data in bookings:
    booking = Booking.objects.create(**booking_data)
    created += 1
    print(f"✅ Created: {booking.customer_name} - {booking.date} {booking.time}")

print(f"\n🎉 Created {created} bookings!")

# Show stats
from django.utils import timezone

today = timezone.now().date()
print(f"\n📊 Stats:")
print(f"Total: {Booking.objects.count()}")
print(f"Pending: {Booking.objects.filter(status='pending').count()}")
print(f"Confirmed: {Booking.objects.filter(status='confirmed').count()}")
print(f"Today: {Booking.objects.filter(date=today).count()}")
print(f"Upcoming: {Booking.objects.filter(date__gt=today).count()}")

print("\n✨ Seeding complete!")
