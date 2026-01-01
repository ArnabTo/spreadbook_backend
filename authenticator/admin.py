from authenticator.models import User
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse, path
from django.utils.html import format_html
from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField, AdminPasswordChangeForm
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all required fields, plus a repeated password."""

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"class": "vTextField", "autocomplete": "new-password"}
        ),
        help_text="Enter a strong password with at least 8 characters.",
    )
    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput(
            attrs={"class": "vTextField", "autocomplete": "new-password"}
        ),
        help_text="Enter the same password as before, for verification.",
    )

    class Meta:
        model = User
        fields = (
            "email",
            "name",
            "phoneNumber",
            "companyId",
            "branchAccess",
            "role",
            "is_active",
            "is_staff",
        )
        widgets = {
            "email": forms.EmailInput(
                attrs={"class": "vTextField", "placeholder": "user@example.com"}
            ),
            "name": forms.TextInput(
                attrs={"class": "vTextField", "placeholder": "Full Name"}
            ),
            "phoneNumber": forms.TextInput(
                attrs={"class": "vTextField", "placeholder": "+1234567890"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make certain fields required
        self.fields["email"].required = True
        self.fields["name"].required = True
        self.fields["role"].required = True

    def clean_email(self):
        """Check that the email is unique."""
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")

        # Validate password strength
        if password1 and len(password1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")

        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_verified = True  # Auto-verify admin-created users
        if commit:
            user.save()
            # Save many-to-many relationships
            self.save_m2m()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on the user, but replaces the password field with admin's password hash display field."""

    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text="Raw passwords are not stored, so there is no way to see this "
        "user's password, but you can change the password using "
        '<a href="../password/">this form</a>.',
    )

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "name",
            "phoneNumber",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "is_verified",
            "companyId",
            "branchAccess",
            "fullAddress",
            "business",
            "business_manager_name",
        )
        widgets = {
            "email": forms.EmailInput(attrs={"class": "vTextField"}),
            "name": forms.TextInput(attrs={"class": "vTextField"}),
            "phoneNumber": forms.TextInput(attrs={"class": "vTextField"}),
            "fullAddress": forms.Textarea(
                attrs={"class": "vLargeTextField", "rows": 3}
            ),
            "business": forms.TextInput(attrs={"class": "vTextField"}),
            "business_manager_name": forms.TextInput(attrs={"class": "vTextField"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_email(self):
        """Check that the email is unique (excluding current user)."""
        email = self.cleaned_data.get("email")
        if (
            email
            and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists()
        ):
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Forms for add and change user
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = (
        "id",
        "name",
        "email",
        "phoneNumber",
        "role",
        "_company_display",
        "_branch_access_display",
        "is_active",
        "is_verified",
        "_avatar_display",
        "_actions_display",
    )
    list_filter = (
        "is_superuser",
        "is_staff",
        "is_active",
        "is_verified",
        "role",
        "companyId",
    )
    search_fields = ("email", "phoneNumber", "name", "business")
    ordering = ("-created_at",)
    readonly_fields = ("token", "date_joined", "last_login", "created_at")
    list_per_page = 25
    list_max_show_all = 100

    fieldsets = (
        (
            "Account Information",
            {
                "fields": ("email", "password", "name", "phoneNumber"),
                "classes": ("wide",),
            },
        ),
        (
            "Role & Permissions",
            {
                "fields": (
                    "role",
                    ("is_active", "is_verified", "is_staff", "is_superuser"),
                ),
                "classes": ("wide",),
            },
        ),
        (
            "Business Information",
            {
                "fields": (
                    "companyId",
                    "branchAccess",
                    "business",
                    "business_manager_name",
                ),
                "classes": ("wide",),
            },
        ),
        (
            "Contact & Address",
            {
                "fields": (
                    "fullAddress",
                    ("city", "state", "zipCode"),
                    "country",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Profile Information",
            {
                "fields": ("avatarUrl", "about", "status"),
                "classes": ("collapse",),
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "date_joined",
                    "last_login",
                    "created_at",
                    "token",
                ),
                "classes": ("collapse",),
                "description": "System-generated fields (read-only).",
            },
        ),
        (
            "Advanced Permissions",
            {
                "fields": (
                    "groups",
                    "user_permissions",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    # Simplified fieldsets for adding user
    add_fieldsets = (
        (
            "Create New User",
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "password1",
                    "password2",
                ),
                "description": "Enter the basic information to create a new user.",
            },
        ),
        (
            "Role & Access",
            {
                "classes": ("wide",),
                "fields": (
                    "role",
                    "companyId",
                    "branchAccess",
                    ("is_active", "is_staff"),
                ),
            },
        ),
        (
            "Contact Information",
            {
                "classes": ("collapse",),
                "fields": ("phoneNumber",),
            },
        ),
    )

    filter_horizontal = (
        "groups",
        "user_permissions",
        "branchAccess",
    )

    # Remove custom JavaScript and CSS for simplicity
    # class Media:
    #     js = ("admin/js/user_admin_enhancements.js",)
    #     css = {"all": ("admin/css/custom_admin.css",)}

    def _avatar_display(self, obj):
        """Display user avatar in admin list"""
        if obj.avatarUrl:
            return format_html(
                '<img src="{}" width="30" height="30" style="border-radius: 50%; object-fit: cover;" loading="lazy" />',
                obj.avatarUrl.url,
            )
        else:
            # Show initials if no avatar
            initials = (
                "".join([name[0] for name in obj.name.split()[:2]]).upper()
                if obj.name
                else "U"
            )
            return format_html(
                '<div style="width: 30px; height: 30px; background: #3b82f6; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px;">{}</div>',
                initials,
            )

    _avatar_display.short_description = "Avatar"

    def _company_display(self, obj):
        """Display company name in a user-friendly way"""
        if hasattr(obj, "companyId") and obj.companyId:
            try:
                return obj.companyId.name or f"Company #{obj.companyId.id}"
            except:
                return f"Company #{obj.companyId.id}"
        return "No company"

    _company_display.short_description = "Company"

    def _branch_access_display(self, obj):
        """Display branch access in a user-friendly way"""
        try:
            # Since branchAccess is now a ManyToManyField, get the count
            branch_count = obj.branchAccess.count()
            if branch_count == 0:
                return format_html('<span style="color: #dc2626;">No access</span>')
            elif branch_count == 1:
                branch = obj.branchAccess.first()
                return format_html(
                    '<span style="color: #059669;">{}</span>', branch.name or "1 branch"
                )
            else:
                return format_html(
                    '<span style="color: #2563eb;">{} branches</span>', branch_count
                )
        except:
            return format_html('<span style="color: #dc2626;">No access</span>')

    _branch_access_display.short_description = "Branch Access"

    def _actions_display(self, obj):
        """Display action buttons for each user"""
        change_url = reverse("admin:authenticator_user_change", args=[obj.pk])
        password_url = reverse("admin:auth_user_password_change", args=[obj.pk])

        return format_html(
            """
            <div style="display: flex; gap: 4px;">
                <a href="{}" style="background: #059669; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 11px;">Edit</a>
                <a href="{}" style="background: #dc2626; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 11px;">Password</a>
            </div>
            """,
            change_url,
            password_url,
        )

    _actions_display.short_description = "Actions"

    def get_form(self, request, obj=None, **kwargs):
        """Use special form during user creation"""
        defaults = {}
        if obj is None:
            defaults["form"] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    def save_model(self, request, obj, form, change):
        """Save model with proper handling"""
        if not change:  # Creating new user
            # Password is already hashed in the form's save method
            obj.save()
            messages.success(request, f'User "{obj.name}" was created successfully.')
        else:  # Updating existing user
            obj.save()
            messages.success(request, f'User "{obj.name}" was updated successfully.')

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filter branchAccess to show only branches for the user's company"""
        if db_field.name == "branchAccess":
            # Get the user being edited
            if request.resolver_match.kwargs.get("object_id"):
                try:
                    user_id = request.resolver_match.kwargs["object_id"]
                    user = User.objects.get(pk=user_id)

                    if user.companyId:
                        # Show only branches for this user's company
                        kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                            company=user.companyId
                        )
                    else:
                        # No company selected, show no branches
                        kwargs["queryset"] = db_field.remote_field.model.objects.none()
                except User.DoesNotExist:
                    kwargs["queryset"] = db_field.remote_field.model.objects.none()
            else:
                # For new user creation, show all branches initially
                kwargs["queryset"] = db_field.remote_field.model.objects.all()

        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def response_add(self, request, obj, post_url_continue=None):
        """Customize response after adding a user"""
        if "_addanother" in request.POST:
            messages.success(
                request,
                f'User "{obj.name}" was created successfully. You can add another user.',
            )
        elif "_continue" in request.POST:
            messages.success(
                request,
                f'User "{obj.name}" was created successfully. You can continue editing.',
            )
        else:
            messages.success(request, f'User "{obj.name}" was created successfully.')
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        """Customize response after changing a user"""
        if "_addanother" in request.POST:
            messages.success(
                request,
                f'User "{obj.name}" was updated successfully. You can add another user.',
            )
        elif "_continue" in request.POST:
            messages.success(request, f'User "{obj.name}" was updated successfully.')
        else:
            messages.success(request, f'User "{obj.name}" was updated successfully.')
        return super().response_change(request, obj)

    def delete_model(self, request, obj):
        """Handle user deletion with confirmation"""
        user_name = obj.name
        super().delete_model(request, obj)
        messages.success(request, f'User "{user_name}" was deleted successfully.')

    def get_urls(self):
        """Add custom URLs for admin actions"""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<id>/quick-toggle-active/",
                self.admin_site.admin_view(self.quick_toggle_active),
                name="quick_toggle_active",
            ),
        ]
        return custom_urls + urls

    @method_decorator(staff_member_required)
    def quick_toggle_active(self, request, id):
        """Quick toggle user active status"""
        try:
            user = get_object_or_404(User, pk=id)
            user.is_active = not user.is_active
            user.save()
            status_text = "activated" if user.is_active else "deactivated"
            messages.success(request, f'User "{user.name}" has been {status_text}.')
            return redirect("admin:authenticator_user_changelist")
        except Exception as e:
            messages.error(request, f"Error toggling user status: {str(e)}")
            return redirect("admin:authenticator_user_changelist")


# Note: Unregister the default admin group
admin.site.unregister(Group)
