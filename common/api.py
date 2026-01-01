from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Per-user in-app notifications."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.read:
            notification.read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["read", "read_at"])
        return Response({"ok": True})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, read=False).update(
            read=True, read_at=timezone.now()
        )
        return Response({"ok": True})

    @action(detail=True, methods=["delete"])
    def delete_one(self, request, pk=None):
        notification = self.get_object()
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["delete"])
    def clear(self, request):
        Notification.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
