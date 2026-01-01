#!/usr/bin/env python
"""
Quick script to seed booking data
Usage: python seed_data.py
"""

import os
import sys
import django
from datetime import date, time, timedelta
from django.utils import timezone

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ERP_Shop.settings")
django.setup()

from booking.models import Booking


def create_sample_bookings():
    """Create sample booking data"""

    print("🌱 Creating sample booking data...")

    # Clear existing bookings
    existing_count = Booking.objects.count()
    if existing_count > 0:
        Booking.objects.all().delete()
        print(f"🗑️  Deleted {existing_count} existing bookings")

    # Sample bookings data
    bookings_data = [
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
        {
            "customer_name": "Habibur Rahman",
            "phone": "+8801912345678",
            "email": "habibur.rahman@email.com",
            "date": date(2024, 11, 13),
            "time": time(19, 0),
            "guests": 4,
            "table": "Table 9",
            "status": "pending",
            "notes": "",
        },
        {
            "customer_name": "Amina Khatun",
            "phone": "+8801723456789",
            "email": "amina.khatun@email.com",
            "date": date(2024, 11, 18),
            "time": time(20, 30),
            "guests": 6,
            "table": "VIP Table 2",
            "status": "confirmed",
            "notes": "Baby shower",
        },
        {
            "customer_name": "Mizanur Rahman",
            "phone": "+8801834567890",
            "email": "mizanur.rahman@email.com",
            "date": date(2024, 11, 3),
            "time": time(12, 0),
            "guests": 7,
            "table": "Garden Table 2",
            "status": "completed",
            "notes": "Reunion dinner",
        },
        {
            "customer_name": "Shahida Begum",
            "phone": "+8801945678901",
            "email": "shahida.begum@email.com",
            "date": date(2024, 11, 16),
            "time": time(18, 30),
            "guests": 2,
            "table": "Table 1",
            "status": "confirmed",
            "notes": "First date",
        },
        {
            "customer_name": "Abdul Karim",
            "phone": "+8801756789012",
            "email": "abdul.karim@email.com",
            "date": date(2024, 11, 25),
            "time": time(13, 30),
            "guests": 12,
            "table": "Garden Table 3",
            "status": "pending",
            "notes": "Wedding anniversary",
        },
    ]

    # Create bookings
    created_count = 0
    for booking_data in bookings_data:
        try:
            booking = Booking.objects.create(**booking_data)
            created_count += 1
            print(f"✅ Created booking for {booking.customer_name}")
        except Exception as e:
            print(f"❌ Error creating booking for {booking_data['customer_name']}: {e}")

    # Show summary
    print(f"\n🎉 Successfully created {created_count} bookings!")

    # Show statistics
    total = Booking.objects.count()
    pending = Booking.objects.filter(status="pending").count()
    confirmed = Booking.objects.filter(status="confirmed").count()
    completed = Booking.objects.filter(status="completed").count()
    cancelled = Booking.objects.filter(status="cancelled").count()

    print(f"\n📊 Booking Statistics:")
    print(f"Total: {total}")
    print(f"Pending: {pending}")
    print(f"Confirmed: {confirmed}")
    print(f"Completed: {completed}")
    print(f"Cancelled: {cancelled}")

    # Show today's bookings
    today = timezone.now().date()
    today_bookings = Booking.objects.filter(date=today)
    print(f"\n📅 Today's bookings ({today}): {today_bookings.count()}")
    for booking in today_bookings:
        print(
            f"  • {booking.time} - {booking.customer_name} (Table: {booking.table}, Guests: {booking.guests})"
        )


if __name__ == "__main__":
    create_sample_bookings()
    print("\n🚀 Ready to test! Run: python manage.py runserver")
    print("📖 API Docs: http://localhost:8000/api/bookings/")
    print("🔧 Admin Panel: http://localhost:8000/admin/")
