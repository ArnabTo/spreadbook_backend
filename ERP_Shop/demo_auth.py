from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from rest_framework.authentication import BaseAuthentication, TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


def _get_or_create_demo_user():
    """Return a stable 'demo' user for auth-disabled mode.

    Prefers an existing active superuser/staff user. If none exists, it creates a
    superuser-like account with an unusable password.
    """

    UserModel = get_user_model()

    # Prefer an existing privileged active user if one exists.
    user = (
        UserModel.objects.filter(is_active=True)
        .order_by("-is_superuser", "-is_staff", "id")
        .first()
    )
    if user is not None:
        return user

    # Otherwise create a deterministic demo user.
    # The project uses a custom user model: authenticator.User.
    required_fields = {"username", "email"}
    model_fields = {f.name for f in UserModel._meta.get_fields()}
    if not required_fields.issubset(model_fields):
        raise ImproperlyConfigured(
            "DJANGO_DISABLE_AUTH is enabled, but the user model is missing required fields"
        )

    demo = UserModel(
        username="demo",
        email="demo@example.com",
        is_active=True,
        is_staff=True,
        is_superuser=True,
    )

    # Custom fields on authenticator.User
    if "name" in model_fields and not getattr(demo, "name", None):
        demo.name = "Demo User"
    if "role" in model_fields and not getattr(demo, "role", None):
        demo.role = "super_admin"
    if "status" in model_fields and not getattr(demo, "status", None):
        demo.status = "active"
    if "is_verified" in model_fields:
        demo.is_verified = True

    demo.set_unusable_password()
    demo.save()
    return demo


class DemoAuthentication(BaseAuthentication):
    """Authenticate every request as the demo user when auth is disabled."""

    def authenticate(self, request):
        if not getattr(settings, "DJANGO_DISABLE_AUTH", False):
            return None
        return (_get_or_create_demo_user(), None)


class TokenAuthenticationWithDemo(TokenAuthentication):
    """Token auth that falls back to demo user when auth is disabled.

    This is important because many viewsets hardcode TokenAuthentication.
    """

    def authenticate(self, request):
        if not getattr(settings, "DJANGO_DISABLE_AUTH", False):
            return super().authenticate(request)

        try:
            result = super().authenticate(request)
        except AuthenticationFailed:
            # Ignore invalid/missing tokens in auth-disabled mode.
            result = None

        if result is not None:
            return result

        return (_get_or_create_demo_user(), None)
