from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q, Avg, Sum, Count
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from rest_framework.exceptions import PermissionDenied
from common.drf_scoping import (
    apply_company_branch_scope,
    get_allowed_branch_ids_for_user,
    get_company_ids_for_user,
    is_unrestricted_user,
)

from .models import Table, TableOccupation, TableReservation
from .serializers import (
    TableSerializer,
    TableOccupationSerializer,
    TableReservationSerializer,
    AssignTableSerializer,
    ClearTableSerializer,
    TableStatsSerializer,
    BulkTableUpdateSerializer,
)


class TableViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing restaurant tables
    """

    permission_classes = [permissions.IsAuthenticated]

    serializer_class = TableSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["number", "section", "floor", "table_type"]
    ordering_fields = ["number", "seats", "status", "section", "created_at"]
    ordering = ["number"]

    def create(self, request, *args, **kwargs):
        """Create a new table with error handling"""
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            # Log the error for debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Table creation error: {str(e)}, Data: {request.data}")

            # Return a more detailed error response
            if "number" in str(e).lower() and "unique" in str(e).lower():
                return Response(
                    {
                        "error": f"Table number {request.data.get('number')} already exists"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {"error": f"Failed to create table: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get_queryset(self):
        """Apply query parameter filters"""
        queryset = Table.objects.filter(is_active=True)

        # Apply filters
        status_filter = self.request.query_params.get("status", None)
        section = self.request.query_params.get("section", None)
        floor = self.request.query_params.get("floor", None)
        min_seats = self.request.query_params.get("min_seats", None)
        max_seats = self.request.query_params.get("max_seats", None)

        if status_filter and status_filter != "all":
            queryset = queryset.filter(status=status_filter)

        if section:
            queryset = queryset.filter(section__icontains=section)

        if floor:
            queryset = queryset.filter(floor__icontains=floor)

        if min_seats:
            try:
                queryset = queryset.filter(seats__gte=int(min_seats))
            except ValueError:
                pass

        if max_seats:
            try:
                queryset = queryset.filter(seats__lte=int(max_seats))
            except ValueError:
                pass

        queryset = apply_company_branch_scope(
            request=self.request,
            queryset=queryset,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )

        return queryset

    def _resolve_company(self):
        user = self.request.user
        if getattr(user, "companyId", None):
            return user.companyId

        branches = user.branchAccess.select_related("company")
        company_ids = set(branches.values_list("company_id", flat=True))
        if len(company_ids) == 1 and branches.exists():
            return branches.first().company

        return None

    def perform_create(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return

        company = self._resolve_company()
        if not company:
            raise PermissionDenied("User is not associated with a company")

        branch = serializer.validated_data.get("branch")
        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if branch is not None:
            if str(branch.company_id) != str(company.id):
                raise PermissionDenied("Branch does not belong to your company")
            if (
                allowed_branch_ids is not None
                and str(branch.id) not in allowed_branch_ids
            ):
                raise PermissionDenied("You do not have access to this branch")
        elif allowed_branch_ids is not None and len(allowed_branch_ids) == 1:
            branch_id = next(iter(allowed_branch_ids))
            branch = user.branchAccess.get(id=branch_id)

        serializer.save(companyId=company, branch=branch)

    def perform_update(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return

        company_ids = get_company_ids_for_user(user)
        if not company_ids or str(serializer.instance.companyId_id) not in company_ids:
            raise PermissionDenied("You do not have access to this table")

        branch = serializer.validated_data.get("branch", serializer.instance.branch)
        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if (
            branch is not None
            and allowed_branch_ids is not None
            and str(branch.id) not in allowed_branch_ids
        ):
            raise PermissionDenied("You do not have access to this branch")

        serializer.save(companyId=serializer.instance.companyId)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Assign a table to customers"""
        table = self.get_object()

        if table.status != "available":
            return Response(
                {"error": f"Table {table.number} is not available"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AssignTableSerializer(
            data=request.data, context={"table_id": table.id}
        )
        serializer.is_valid(raise_exception=True)

        # Create occupation
        occupation = TableOccupation.objects.create(
            table=table, **serializer.validated_data
        )

        # Update table status
        table.status = "occupied"
        table.save()

        return Response(
            {
                "message": f"Table {table.number} assigned successfully",
                "occupation_id": str(occupation.id),
                "table": TableSerializer(table).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def clear(self, request, pk=None):
        """Clear a table and end occupation"""
        table = self.get_object()

        if table.status != "occupied":
            return Response(
                {"error": f"Table {table.number} is not occupied"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ClearTableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # End current occupation
        occupation = table.current_occupation
        if occupation:
            final_amount = serializer.validated_data.get("final_amount")
            notes = serializer.validated_data.get("notes", "")

            if final_amount is not None:
                occupation.order_amount = final_amount
            if notes:
                occupation.notes = (occupation.notes or "") + f"\nFinal notes: {notes}"

            occupation.end_occupation(final_amount)

        return Response(
            {
                "message": f"Table {table.number} cleared successfully",
                "table": TableSerializer(table).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def update_order(self, request, pk=None):
        """Update order amount for occupied table"""
        table = self.get_object()

        if table.status != "occupied":
            return Response(
                {"error": f"Table {table.number} is not occupied"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_amount = request.data.get("order_amount")
        if order_amount is None:
            return Response(
                {"error": "order_amount is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order_amount = float(order_amount)
            if order_amount < 0:
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid order amount"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Update current occupation
        occupation = table.current_occupation
        if occupation:
            occupation.order_amount = order_amount
            occupation.save()

        return Response(
            {
                "message": f"Order amount updated for table {table.number}",
                "table": TableSerializer(table).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """Bulk update multiple tables"""
        serializer = BulkTableUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        table_ids = serializer.validated_data["table_ids"]
        action_type = serializer.validated_data["action"]

        tables = Table.objects.filter(id__in=table_ids)
        updated_count = 0

        if action_type == "mark_available":
            # End any active occupations first
            for table in tables:
                occupation = table.current_occupation
                if occupation:
                    occupation.end_occupation()
            updated_count = tables.update(status="available")

        elif action_type == "mark_maintenance":
            # End any active occupations first
            for table in tables:
                occupation = table.current_occupation
                if occupation:
                    occupation.end_occupation()
            updated_count = tables.update(status="maintenance")

        elif action_type == "clear_tables":
            for table in tables.filter(status="occupied"):
                occupation = table.current_occupation
                if occupation:
                    occupation.end_occupation()
                    updated_count += 1

        return Response(
            {
                "message": f"Successfully updated {updated_count} tables",
                "updated_count": updated_count,
                "action": action_type,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get comprehensive table statistics"""
        queryset = self.get_queryset()

        # Basic counts
        total_tables = queryset.count()
        available_tables = queryset.filter(status="available").count()
        occupied_tables = queryset.filter(status="occupied").count()
        reserved_tables = queryset.filter(status="reserved").count()
        maintenance_tables = queryset.filter(status="maintenance").count()

        # Seat statistics
        total_seats = queryset.aggregate(total=Coalesce(Sum("seats"), 0))["total"]

        occupied_seats = queryset.filter(status="occupied").aggregate(
            total=Coalesce(Sum("seats"), 0)
        )["total"]

        occupancy_rate = (occupied_seats / total_seats * 100) if total_seats > 0 else 0

        # Time and revenue statistics
        today = timezone.now().date()
        today_start = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.min.time())
        )

        # Get today's occupations
        today_occupations = TableOccupation.objects.filter(start_time__gte=today_start)

        # Calculate average occupation time
        completed_occupations = today_occupations.exclude(end_time__isnull=True)
        if completed_occupations.exists():
            # Calculate duration for each occupation and then average
            total_duration = 0
            count = 0
            for occupation in completed_occupations:
                if occupation.end_time and occupation.start_time:
                    duration_seconds = (
                        occupation.end_time - occupation.start_time
                    ).total_seconds()
                    total_duration += duration_seconds
                    count += 1

            if count > 0:
                avg_seconds = total_duration / count
                avg_minutes = int(avg_seconds / 60)
                avg_occupation_time = f"{avg_minutes}m"
            else:
                avg_occupation_time = "0m"
        else:
            avg_occupation_time = "0m"

        # Revenue calculation
        total_revenue_today = today_occupations.aggregate(
            total=Coalesce(Sum("order_amount"), 0.0)
        )["total"]

        # Active counts
        active_occupations = TableOccupation.objects.filter(is_active=True).count()

        # Upcoming reservations (next 24 hours)
        tomorrow = timezone.now() + timedelta(days=1)
        upcoming_reservations = TableReservation.objects.filter(
            reservation_time__gte=timezone.now(),
            reservation_time__lte=tomorrow,
            status="confirmed",
        ).count()

        stats_data = {
            "total_tables": total_tables,
            "available_tables": available_tables,
            "occupied_tables": occupied_tables,
            "reserved_tables": reserved_tables,
            "maintenance_tables": maintenance_tables,
            "total_seats": total_seats,
            "occupied_seats": occupied_seats,
            "occupancy_rate": round(occupancy_rate, 2),
            "avg_occupation_time": avg_occupation_time,
            "total_revenue_today": total_revenue_today,
            "active_occupations": active_occupations,
            "upcoming_reservations": upcoming_reservations,
        }

        return Response(stats_data)

    @action(detail=False, methods=["get"])
    def sections(self, request):
        """Get all available sections"""
        sections = (
            Table.objects.filter(is_active=True)
            .values_list("section", flat=True)
            .distinct()
            .order_by("section")
        )
        sections = [s for s in sections if s]  # Remove null values
        return Response({"sections": list(sections), "count": len(sections)})

    @action(detail=False, methods=["get"])
    def floors(self, request):
        """Get all available floors"""
        floors = (
            Table.objects.filter(is_active=True)
            .values_list("floor", flat=True)
            .distinct()
            .order_by("floor")
        )
        floors = [f for f in floors if f]  # Remove null values
        return Response({"floors": list(floors), "count": len(floors)})


class TableOccupationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing table occupations
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TableOccupationSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["customer_name", "customer_phone", "waiter", "table__number"]
    ordering_fields = ["start_time", "end_time", "order_amount"]
    ordering = ["-start_time"]

    def get_queryset(self):
        """Apply filters"""
        queryset = TableOccupation.objects.all()

        is_active = self.request.query_params.get("is_active", None)
        table_id = self.request.query_params.get("table", None)
        waiter = self.request.query_params.get("waiter", None)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        if table_id:
            queryset = queryset.filter(table_id=table_id)

        if waiter:
            queryset = queryset.filter(waiter__icontains=waiter)

        queryset = apply_company_branch_scope(
            request=self.request,
            queryset=queryset,
            company_id_field="table__companyId_id",
            branch_id_field="table__branch_id",
        )

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return

        table = serializer.validated_data.get("table")
        if not table:
            raise PermissionDenied("Table is required")

        company_ids = get_company_ids_for_user(user)
        if not company_ids or str(table.companyId_id) not in company_ids:
            raise PermissionDenied("You do not have access to this table")

        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if (
            allowed_branch_ids is not None
            and table.branch_id
            and str(table.branch_id) not in allowed_branch_ids
        ):
            raise PermissionDenied("You do not have access to this branch")

        serializer.save()


class TableReservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing table reservations
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TableReservationSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "customer_name",
        "customer_phone",
        "customer_email",
        "table__number",
    ]
    ordering_fields = ["reservation_time", "created_at", "party_size"]
    ordering = ["reservation_time"]

    def get_queryset(self):
        """Apply filters"""
        queryset = TableReservation.objects.all()

        status_filter = self.request.query_params.get("status", None)
        table_id = self.request.query_params.get("table", None)
        date_filter = self.request.query_params.get("date", None)

        if status_filter and status_filter != "all":
            queryset = queryset.filter(status=status_filter)

        if table_id:
            queryset = queryset.filter(table_id=table_id)

        if date_filter:
            try:
                from datetime import datetime

                date_obj = datetime.strptime(date_filter, "%Y-%m-%d").date()
                queryset = queryset.filter(reservation_time__date=date_obj)
            except ValueError:
                pass

        queryset = apply_company_branch_scope(
            request=self.request,
            queryset=queryset,
            company_id_field="table__companyId_id",
            branch_id_field="table__branch_id",
        )

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return

        table = serializer.validated_data.get("table")
        if not table:
            raise PermissionDenied("Table is required")

        company_ids = get_company_ids_for_user(user)
        if not company_ids or str(table.companyId_id) not in company_ids:
            raise PermissionDenied("You do not have access to this table")

        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if (
            allowed_branch_ids is not None
            and table.branch_id
            and str(table.branch_id) not in allowed_branch_ids
        ):
            raise PermissionDenied("You do not have access to this branch")

        serializer.save()

    @action(detail=True, methods=["post"])
    def mark_arrived(self, request, pk=None):
        """Mark reservation as arrived and create occupation"""
        reservation = self.get_object()

        if reservation.status != "confirmed":
            return Response(
                {"error": "Only confirmed reservations can be marked as arrived"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        waiter = request.data.get("waiter", "")

        try:
            occupation = reservation.mark_as_arrived(waiter)
            return Response(
                {
                    "message": "Reservation marked as arrived",
                    "occupation_id": str(occupation.id),
                    "table": TableSerializer(reservation.table).data,
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
