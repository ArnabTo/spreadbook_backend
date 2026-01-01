from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework import permissions
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    UnitType,
    Unit,
    ResortReservation,
    HousekeepingTask,
    MaintenanceTicket,
    Activity,
    Package,
    Folio,
    FolioLineItem,
)
from .serializers import (
    UnitTypeSerializer,
    UnitSerializer,
    ResortReservationSerializer,
    HousekeepingTaskSerializer,
    MaintenanceTicketSerializer,
    ActivitySerializer,
    PackageSerializer,
    FolioSerializer,
    FolioLineItemSerializer,
)


class BranchFilteredQuerysetMixin:
    permission_classes = [permissions.IsAuthenticated]
    branch_filter_field = "branch_id"

    def _get_allowed_branch_ids(self):
        user = getattr(self.request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return set()

        # Allow global access for superusers / software owners
        if (
            getattr(user, "is_superuser", False)
            or getattr(user, "role", None) == "software_owner"
        ):
            return None

        if hasattr(user, "branchAccess") and user.branchAccess.exists():
            return set(
                str(bid) for bid in user.branchAccess.values_list("id", flat=True)
            )

        # No branch assignments: don't implicitly restrict
        return None

    def filter_by_branch(self, queryset):
        branch_id = self.request.query_params.get("branch_id")

        allowed_branch_ids = self._get_allowed_branch_ids()

        if branch_id:
            if (
                allowed_branch_ids is not None
                and str(branch_id) not in allowed_branch_ids
            ):
                raise PermissionDenied("You do not have access to this branch.")
            return queryset.filter(**{self.branch_filter_field: branch_id})

        if allowed_branch_ids is not None:
            return queryset.filter(
                **{f"{self.branch_filter_field}__in": list(allowed_branch_ids)}
            )

        return queryset

    def _enforce_branch_in_serializer(self, serializer):
        allowed_branch_ids = self._get_allowed_branch_ids()
        if allowed_branch_ids is None:
            return

        branch = serializer.validated_data.get("branch")
        if branch is None:
            return

        if str(getattr(branch, "id", branch)) not in allowed_branch_ids:
            raise PermissionDenied("You do not have access to this branch.")

    def perform_create(self, serializer):
        self._enforce_branch_in_serializer(serializer)
        serializer.save(user=getattr(self.request, "user", None))

    def perform_update(self, serializer):
        self._enforce_branch_in_serializer(serializer)
        serializer.save()


class UnitTypeViewSet(BranchFilteredQuerysetMixin, viewsets.ModelViewSet):
    queryset = UnitType.objects.all()
    serializer_class = UnitTypeSerializer

    def get_queryset(self):
        return self.filter_by_branch(super().get_queryset())


class UnitViewSet(BranchFilteredQuerysetMixin, viewsets.ModelViewSet):
    queryset = Unit.objects.select_related("unit_type").all()
    serializer_class = UnitSerializer

    def get_queryset(self):
        return self.filter_by_branch(super().get_queryset())


class ResortReservationViewSet(BranchFilteredQuerysetMixin, viewsets.ModelViewSet):
    queryset = ResortReservation.objects.select_related(
        "guest", "unit_type", "unit"
    ).all()
    serializer_class = ResortReservationSerializer

    def get_queryset(self):
        queryset = self.filter_by_branch(super().get_queryset())
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        guest_id = self.request.query_params.get("guest_id")
        if guest_id:
            queryset = queryset.filter(guest_id=guest_id)

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            queryset = queryset.filter(check_in_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(check_out_date__lte=date_to)
        return queryset

    @action(detail=True, methods=["patch"])
    def check_in(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status not in {"reserved"}:
            raise ValidationError(
                {"status": "Only reserved reservations can be checked in."}
            )

        reservation.status = "checked_in"
        reservation.save(update_fields=["status"])

        Folio.objects.get_or_create(
            reservation=reservation,
            defaults={
                "branch": reservation.branch,
                "currency": reservation.currency or "BDT",
                "status": "open",
                "user": getattr(request, "user", None),
            },
        )

        return Response(self.get_serializer(reservation).data)

    @action(detail=True, methods=["patch"])
    def check_out(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status not in {"checked_in"}:
            raise ValidationError(
                {"status": "Only checked-in reservations can be checked out."}
            )

        reservation.status = "checked_out"
        reservation.save(update_fields=["status"])
        return Response(self.get_serializer(reservation).data)

    @action(detail=True, methods=["patch"])
    def cancel(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status in {"checked_out", "cancelled"}:
            raise ValidationError(
                {"status": "Reservation cannot be cancelled in its current status."}
            )

        reservation.status = "cancelled"
        reservation.save(update_fields=["status"])
        return Response(self.get_serializer(reservation).data)


class HousekeepingTaskViewSet(BranchFilteredQuerysetMixin, viewsets.ModelViewSet):
    queryset = HousekeepingTask.objects.select_related("unit").all()
    serializer_class = HousekeepingTaskSerializer

    def get_queryset(self):
        queryset = self.filter_by_branch(super().get_queryset())
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        task_type = self.request.query_params.get("task_type")
        if task_type:
            queryset = queryset.filter(task_type=task_type)

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            queryset = queryset.filter(scheduled_for__gte=date_from)
        if date_to:
            queryset = queryset.filter(scheduled_for__lte=date_to)
        return queryset

    @action(detail=True, methods=["patch"])
    def mark_done(self, request, pk=None):
        task = self.get_object()
        if task.status == "done":
            return Response(self.get_serializer(task).data)

        task.status = "done"
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at"])
        return Response(self.get_serializer(task).data)


class MaintenanceTicketViewSet(BranchFilteredQuerysetMixin, viewsets.ModelViewSet):
    queryset = MaintenanceTicket.objects.select_related("unit").all()
    serializer_class = MaintenanceTicketSerializer

    def get_queryset(self):
        queryset = self.filter_by_branch(super().get_queryset())
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        priority = self.request.query_params.get("priority")
        if priority:
            queryset = queryset.filter(priority=priority)
        return queryset

    @action(detail=True, methods=["patch"])
    def mark_resolved(self, request, pk=None):
        ticket = self.get_object()
        if ticket.status in {"resolved", "closed"}:
            return Response(self.get_serializer(ticket).data)

        ticket.status = "resolved"
        ticket.resolved_at = timezone.now()
        ticket.save(update_fields=["status", "resolved_at"])
        return Response(self.get_serializer(ticket).data)


class ActivityViewSet(BranchFilteredQuerysetMixin, viewsets.ModelViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer

    def get_queryset(self):
        return self.filter_by_branch(super().get_queryset())


class PackageViewSet(BranchFilteredQuerysetMixin, viewsets.ModelViewSet):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer

    def get_queryset(self):
        return self.filter_by_branch(super().get_queryset())


class FolioViewSet(BranchFilteredQuerysetMixin, viewsets.ModelViewSet):
    queryset = (
        Folio.objects.select_related("reservation").prefetch_related("items").all()
    )
    serializer_class = FolioSerializer

    def get_queryset(self):
        return self.filter_by_branch(super().get_queryset())

    @action(detail=True, methods=["patch"])
    def close(self, request, pk=None):
        folio = self.get_object()
        if folio.status == "closed":
            return Response(self.get_serializer(folio).data)

        folio.status = "closed"
        folio.save(update_fields=["status"])
        return Response(self.get_serializer(folio).data)

    @action(detail=True, methods=["post"])
    def post_pos_order(self, request, pk=None):
        """Post a restaurant POS order (sales.Sale) into this folio as line items."""

        folio = self.get_object()
        if folio.status == "closed":
            return Response(
                {"error": "Folio is closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sale_id = request.data.get("sale_id") or request.data.get("order_id")
        order_number = request.data.get("order_number")
        allow_mismatch = bool(request.data.get("allow_mismatch"))

        if not sale_id and not order_number:
            return Response(
                {"error": "Provide sale_id (UUID) or order_number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from sales.models import Sale
        except Exception:
            return Response(
                {"error": "Sales module is not available."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        sale_qs = Sale.objects.prefetch_related("items")
        sale = None
        if sale_id:
            sale = sale_qs.filter(id=sale_id).first()
        if sale is None and order_number:
            sale = (
                sale_qs.filter(order_number=order_number)
                .order_by("-order_time")
                .first()
            )
        if sale is None and order_number:
            sale = (
                sale_qs.filter(invoiceNumber=order_number)
                .order_by("-order_time")
                .first()
            )

        if sale is None:
            return Response(
                {"error": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reservation = folio.reservation
        if (
            sale.customer_id
            and str(sale.customer_id) != str(reservation.guest_id)
            and not allow_mismatch
        ):
            return Response(
                {
                    "error": "Order customer does not match reservation guest.",
                    "details": {
                        "order_customer": str(sale.customer_id),
                        "reservation_guest": str(reservation.guest_id),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = 0
        for item in getattr(sale, "items", []).all() if hasattr(sale, "items") else []:
            if not getattr(item, "title", None):
                continue
            FolioLineItem.objects.create(
                folio=folio,
                source="restaurant",
                description=f"{sale.order_number or sale.invoiceNumber or sale.id}: {item.title}",
                quantity=item.quantity or 1,
                unit_price=item.price or 0,
                user=getattr(request, "user", None),
            )
            created += 1

        return Response(
            {
                "success": True,
                "created_items": created,
                "folio": self.get_serializer(folio).data,
            }
        )


class FolioLineItemViewSet(BranchFilteredQuerysetMixin, viewsets.ModelViewSet):
    branch_filter_field = "folio__branch_id"
    queryset = FolioLineItem.objects.select_related("folio").all()
    serializer_class = FolioLineItemSerializer

    def get_queryset(self):
        return self.filter_by_branch(super().get_queryset())

    def perform_create(self, serializer):
        folio = serializer.validated_data.get("folio")
        if folio and folio.status == "closed":
            raise ValidationError({"folio": "Cannot add items to a closed folio."})

        allowed_branch_ids = self._get_allowed_branch_ids()
        if (
            allowed_branch_ids is not None
            and folio
            and str(folio.branch_id) not in allowed_branch_ids
        ):
            raise PermissionDenied("You do not have access to this branch.")

        serializer.save(user=getattr(self.request, "user", None))
