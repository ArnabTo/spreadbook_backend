from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, date
from django.db.models import Q, Count
from .models import Booking
from .serializers import (
    BookingSerializer,
    BookingListSerializer,
    BookingCreateSerializer,
)


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing restaurant bookings
    Provides CRUD operations and additional booking-specific endpoints
    """

    queryset = Booking.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["customer_name", "phone", "email", "table"]
    ordering_fields = ["date", "time", "created_at", "guests"]
    ordering = ["date", "time"]

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()

        # Filter by status
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Filter by date
        date_param = self.request.query_params.get("date")
        if date_param:
            try:
                filter_date = datetime.strptime(date_param, "%Y-%m-%d").date()
                queryset = queryset.filter(date=filter_date)
            except ValueError:
                pass

        # Filter by table
        table_param = self.request.query_params.get("table")
        if table_param:
            queryset = queryset.filter(table__icontains=table_param)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return BookingCreateSerializer
        elif self.action == "list":
            return BookingListSerializer
        return BookingSerializer

    def create(self, request, *args, **kwargs):
        """Create a new booking"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            booking = serializer.save()
            # Return full booking data after creation
            response_serializer = BookingSerializer(booking)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def today(self, request):
        """Get all bookings for today"""
        today = timezone.now().date()
        bookings = self.get_queryset().filter(date=today)
        serializer = BookingListSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """Get all upcoming bookings"""
        now = timezone.now()
        today = now.date()
        current_time = now.time()

        # Get bookings from today onwards, but for today only include future times
        upcoming_bookings = (
            self.get_queryset()
            .filter(Q(date__gt=today) | (Q(date=today) & Q(time__gte=current_time)))
            .exclude(status="cancelled")
        )

        serializer = BookingListSerializer(upcoming_bookings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_status(self, request):
        """Get bookings grouped by status"""

        status_counts = (
            self.get_queryset()
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )

        return Response(
            {"status_counts": list(status_counts), "total": self.get_queryset().count()}
        )

    @action(detail=False, methods=["get"])
    def by_date_range(self, request):
        """Get bookings within a date range"""
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not start_date or not end_date:
            return Response(
                {"error": "start_date and end_date parameters required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bookings = self.get_queryset().filter(date__range=[start, end])
        serializer = BookingListSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def confirm(self, request, pk=None):
        """Confirm a booking"""
        booking = self.get_object()
        booking.status = "confirmed"
        booking.save()
        serializer = BookingSerializer(booking)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        booking.status = "cancelled"
        booking.save()
        serializer = BookingSerializer(booking)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def complete(self, request, pk=None):
        """Mark booking as completed"""
        booking = self.get_object()
        booking.status = "completed"
        booking.save()
        serializer = BookingSerializer(booking)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def available_tables(self, request):
        """Get available tables for a specific date/time"""
        booking_date = request.query_params.get("date")
        booking_time = request.query_params.get("time")

        if not booking_date or not booking_time:
            return Response(
                {"error": "date and time parameters required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            date_obj = datetime.strptime(booking_date, "%Y-%m-%d").date()
            time_obj = datetime.strptime(booking_time, "%H:%M").time()
        except ValueError:
            return Response(
                {
                    "error": "Invalid date/time format. Use YYYY-MM-DD for date and HH:MM for time"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get all booked tables for the specified date/time
        booked_tables = (
            self.get_queryset()
            .filter(date=date_obj, time=time_obj, status__in=["confirmed", "pending"])
            .values_list("table", flat=True)
        )

        # This is a simple example - you might want to implement proper table management
        all_tables = [f"Table {i}" for i in range(1, 21)]  # Assuming 20 tables
        available_tables = [table for table in all_tables if table not in booked_tables]

        return Response(
            {
                "available_tables": available_tables,
                "booked_tables": list(booked_tables),
                "date": booking_date,
                "time": booking_time,
            }
        )
