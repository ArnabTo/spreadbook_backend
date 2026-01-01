from django.core.management.base import BaseCommand, CommandError
from authenticator.models import User
from django.contrib.auth.models import Group, Permission
from django.db import IntegrityError
import getpass


class Command(BaseCommand):
    help = "Create a new user with admin privileges"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            help="Email address for the new user",
        )
        parser.add_argument(
            "--name",
            type=str,
            help="Full name for the new user",
        )
        parser.add_argument(
            "--role",
            type=str,
            default="admin",
            choices=["admin", "manager", "cashier", "staff"],
            help="Role for the new user (default: admin)",
        )
        parser.add_argument(
            "--superuser",
            action="store_true",
            help="Make this user a superuser",
        )
        parser.add_argument(
            "--staff",
            action="store_true",
            help="Give this user staff access",
        )
        parser.add_argument(
            "--phone",
            type=str,
            help="Phone number for the new user",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Run in non-interactive mode",
        )

    def handle(self, *args, **options):
        """
        Create a new user with the specified options
        """
        self.stdout.write(
            self.style.SUCCESS("=== Restaurant Management System - Create User ===\n")
        )

        try:
            # Get user details
            if options["no_input"]:
                email = options["email"]
                name = options["name"]
                if not email or not name:
                    raise CommandError(
                        "Email and name are required when using --no-input"
                    )
            else:
                email = options["email"] or self.get_email()
                name = options["name"] or self.get_name()

            role = options["role"]
            phone = (
                options["phone"] or self.get_phone()
                if not options["no_input"]
                else options["phone"]
            )
            is_superuser = options["superuser"]
            is_staff = options["staff"] or is_superuser  # Superusers are always staff

            # Get password
            if options["no_input"]:
                password = "admin123"  # Default password for non-interactive mode
                self.stdout.write(
                    self.style.WARNING(
                        f"Using default password: {password}\n"
                        "Please change this password immediately after login!"
                    )
                )
            else:
                password = self.get_password()

            # Validate email uniqueness
            if User.objects.filter(email=email).exists():
                raise CommandError(f'A user with email "{email}" already exists.')

            # Create user
            user = User.objects.create_user(
                email=email,
                name=name,
                password=password,
                phoneNumber=phone,
                role=role,
                is_staff=is_staff,
                is_superuser=is_superuser,
                is_verified=True,  # Auto-verify admin-created users
            )

            # Set additional permissions based on role
            if role == "admin" or is_superuser:
                # Give admin users all permissions
                all_permissions = Permission.objects.all()
                user.user_permissions.set(all_permissions)
            elif role == "manager":
                # Give manager users specific permissions
                manager_permissions = Permission.objects.filter(
                    codename__in=[
                        "view_user",
                        "add_user",
                        "change_user",
                        "view_sale",
                        "add_sale",
                        "change_sale",
                        "view_product",
                        "add_product",
                        "change_product",
                        "view_customer",
                        "add_customer",
                        "change_customer",
                    ]
                )
                user.user_permissions.set(manager_permissions)

            # Success message
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(self.style.SUCCESS("✓ User created successfully!"))
            self.stdout.write("=" * 50)
            self.stdout.write(f"Email: {user.email}")
            self.stdout.write(f"Name: {user.name}")
            self.stdout.write(f"Role: {user.role}")
            self.stdout.write(f'Phone: {user.phoneNumber or "Not provided"}')
            self.stdout.write(f'Staff Access: {"Yes" if user.is_staff else "No"}')
            self.stdout.write(f'Superuser: {"Yes" if user.is_superuser else "No"}')
            self.stdout.write(f"User ID: {user.id}")
            self.stdout.write("=" * 50)

            if not options["no_input"]:
                self.stdout.write(
                    self.style.SUCCESS(
                        "\n🎉 The user can now log in to the admin panel!"
                    )
                )
                self.stdout.write(f"Admin URL: http://localhost:8000/admin/")

        except IntegrityError as e:
            raise CommandError(f"Database error: {e}")
        except Exception as e:
            raise CommandError(f"Error creating user: {e}")

    def get_email(self):
        """Get email from user input with validation"""
        while True:
            email = input("Email address: ").strip()
            if email:
                if "@" in email and "." in email.split("@")[-1]:
                    if User.objects.filter(email=email).exists():
                        self.stdout.write(
                            self.style.ERROR(
                                f'User with email "{email}" already exists.'
                            )
                        )
                        continue
                    return email
                else:
                    self.stdout.write(
                        self.style.ERROR("Please enter a valid email address.")
                    )
            else:
                self.stdout.write(self.style.ERROR("Email address is required."))

    def get_name(self):
        """Get name from user input with validation"""
        while True:
            name = input("Full name: ").strip()
            if name:
                return name
            else:
                self.stdout.write(self.style.ERROR("Full name is required."))

    def get_phone(self):
        """Get phone number from user input (optional)"""
        phone = input("Phone number (optional): ").strip()
        return phone if phone else None

    def get_password(self):
        """Get password from user input with validation"""
        while True:
            password = getpass.getpass("Password: ")
            if len(password) < 8:
                self.stdout.write(
                    self.style.ERROR("Password must be at least 8 characters long.")
                )
                continue

            password2 = getpass.getpass("Password (again): ")
            if password != password2:
                self.stdout.write(self.style.ERROR("Passwords do not match."))
                continue

            return password
