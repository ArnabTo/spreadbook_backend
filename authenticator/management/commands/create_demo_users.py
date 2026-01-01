from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from authenticator.models import User
from django.utils import timezone


class Command(BaseCommand):
    help = "Create demo users matching frontend expectations"

    def handle(self, *args, **options):
        demo_users = [
            # ============ SOFTWARE OWNER & PLATFORM STAFF ============
            {
                "username": "owner",
                "email": "owner@restaurantms.com",
                "name": "Software Owner",
                "fullName": "Software Owner",
                "role": "software_owner",
                "companyId": None,
                "branchAccess": [],
                "status": "active",
            },
            # ============ RESELLERS ============
            {
                "username": "reseller1",
                "email": "john.smith@salespartner.com",
                "name": "John Smith",
                "fullName": "John Smith",
                "role": "reseller",
                "resellerId": "reseller-1",
                "companyId": None,
                "branchAccess": [],
                "status": "active",
            },
            {
                "username": "reseller2",
                "email": "maria.garcia@salespartner.com",
                "name": "Maria Garcia",
                "fullName": "Maria Garcia",
                "role": "reseller",
                "resellerId": "reseller-2",
                "companyId": None,
                "branchAccess": [],
                "status": "active",
            },
            {
                "username": "reseller3",
                "email": "ahmed.hassan@salespartner.com",
                "name": "Ahmed Hassan",
                "fullName": "Ahmed Hassan",
                "role": "reseller",
                "resellerId": "reseller-3",
                "companyId": None,
                "branchAccess": [],
                "status": "active",
            },
            # ============ COMPANY 1: Gourmet Palace Group (5 branches) ============
            {
                "username": "michael.chen",
                "email": "michael@gourmetpalace.com",
                "name": "Michael Chen",
                "fullName": "Michael Chen",
                "role": "super_admin",
                "companyId": "company-1",
                "branchAccess": ["all"],
                "status": "active",
            },
            {
                "username": "lisa.chen",
                "email": "lisa@gourmetpalace.com",
                "name": "Lisa Chen",
                "fullName": "Lisa Chen",
                "role": "admin",
                "companyId": "company-1",
                "branchAccess": ["branch-c1-1", "branch-c1-2", "branch-c1-3"],
                "status": "active",
            },
            {
                "username": "robert.downtown",
                "email": "robert@gourmetpalace.com",
                "name": "Robert Wilson",
                "fullName": "Robert Wilson",
                "role": "manager",
                "companyId": "company-1",
                "branchAccess": ["branch-c1-1"],
                "status": "active",
            },
            {
                "username": "emily.downtown",
                "email": "emily@gourmetpalace.com",
                "name": "Emily Davis",
                "fullName": "Emily Davis",
                "role": "waiter",
                "companyId": "company-1",
                "branchAccess": ["branch-c1-1"],
                "status": "active",
            },
            # ============ COMPANY 2: Quick Bites Fast Food (12 branches) ============
            {
                "username": "sarah.johnson",
                "email": "sarah@quickbites.com",
                "name": "Sarah Johnson",
                "fullName": "Sarah Johnson",
                "role": "super_admin",
                "companyId": "company-2",
                "branchAccess": ["all"],
                "status": "active",
            },
            {
                "username": "james.ops",
                "email": "james@quickbites.com",
                "name": "James Martinez",
                "fullName": "James Martinez",
                "role": "admin",
                "companyId": "company-2",
                "branchAccess": [
                    "branch-c2-1",
                    "branch-c2-2",
                    "branch-c2-3",
                    "branch-c2-4",
                ],
                "status": "active",
            },
            {
                "username": "anna.mall",
                "email": "anna@quickbites.com",
                "name": "Anna Rodriguez",
                "fullName": "Anna Rodriguez",
                "role": "manager",
                "companyId": "company-2",
                "branchAccess": ["branch-c2-1"],
                "status": "active",
            },
            {
                "username": "tom.mall",
                "email": "tom@quickbites.com",
                "name": "Tom Anderson",
                "fullName": "Tom Anderson",
                "role": "cashier",
                "companyId": "company-2",
                "branchAccess": ["branch-c2-1"],
                "status": "active",
            },
            # ============ COMPANY 3: Artisan Coffee Co. (3 branches) ============
            {
                "username": "emma.williams",
                "email": "emma@artisancoffee.com",
                "name": "Emma Williams",
                "fullName": "Emma Williams",
                "role": "super_admin",
                "companyId": "company-3",
                "branchAccess": ["all"],
                "status": "active",
            },
            {
                "username": "olivia.downtown",
                "email": "olivia@artisancoffee.com",
                "name": "Olivia Brown",
                "fullName": "Olivia Brown",
                "role": "manager",
                "companyId": "company-3",
                "branchAccess": ["branch-c3-1"],
                "status": "active",
            },
            {
                "username": "lucas.downtown",
                "email": "lucas@artisancoffee.com",
                "name": "Lucas Taylor",
                "fullName": "Lucas Taylor",
                "role": "staff",
                "companyId": "company-3",
                "branchAccess": ["branch-c3-1"],
                "status": "active",
            },
            # ============ COMPANY 4: Spice Garden (7 branches) ============
            {
                "username": "raj.patel",
                "email": "raj@spicegarden.com",
                "name": "Raj Patel",
                "fullName": "Raj Patel",
                "role": "super_admin",
                "companyId": "company-4",
                "branchAccess": ["all"],
                "status": "active",
            },
            {
                "username": "priya.ops",
                "email": "priya@spicegarden.com",
                "name": "Priya Sharma",
                "fullName": "Priya Sharma",
                "role": "admin",
                "companyId": "company-4",
                "branchAccess": ["branch-c4-1", "branch-c4-2", "branch-c4-3"],
                "status": "active",
            },
            {
                "username": "kumar.chef",
                "email": "kumar@spicegarden.com",
                "name": "Kumar Singh",
                "fullName": "Kumar Singh",
                "role": "chef",
                "companyId": "company-4",
                "branchAccess": ["branch-c4-1"],
                "status": "active",
            },
            # ============ COMPANY 5: Cloud Kitchen Express (2 branches) ============
            {
                "username": "david.kim",
                "email": "david@cloudkitchen.com",
                "name": "David Kim",
                "fullName": "David Kim",
                "role": "super_admin",
                "companyId": "company-5",
                "branchAccess": ["all"],
                "status": "active",
            },
            {
                "username": "jane.ops",
                "email": "jane@cloudkitchen.com",
                "name": "Jane Park",
                "fullName": "Jane Park",
                "role": "manager",
                "companyId": "company-5",
                "branchAccess": ["branch-c5-1"],
                "status": "active",
            },
            # ============ COMPANY 6: Pizza Paradise (4 branches) ============
            {
                "username": "marco.rossi",
                "email": "marco@pizzaparadise.com",
                "name": "Marco Rossi",
                "fullName": "Marco Rossi",
                "role": "super_admin",
                "companyId": "company-6",
                "branchAccess": ["all"],
                "status": "active",
            },
            {
                "username": "sofia.north",
                "email": "sofia@pizzaparadise.com",
                "name": "Sofia Bianchi",
                "fullName": "Sofia Bianchi",
                "role": "manager",
                "companyId": "company-6",
                "branchAccess": ["branch-c6-1"],
                "status": "active",
            },
            # ============ COMPANY 8: Sushi Master (3 branches) ============
            {
                "username": "yuki.tanaka",
                "email": "yuki@sushimaster.com",
                "name": "Yuki Tanaka",
                "fullName": "Yuki Tanaka",
                "role": "super_admin",
                "companyId": "company-8",
                "branchAccess": ["all"],
                "status": "active",
            },
            {
                "username": "kenji.chef",
                "email": "kenji@sushimaster.com",
                "name": "Kenji Yamamoto",
                "fullName": "Kenji Yamamoto",
                "role": "manager",
                "companyId": "company-8",
                "branchAccess": ["branch-c8-1"],
                "status": "active",
            },
        ]

        created_count = 0
        updated_count = 0

        for user_data in demo_users:
            username = user_data["username"]

            try:
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": user_data["email"],
                        "name": user_data["name"],
                        "fullName": user_data["fullName"],
                        "role": user_data["role"],
                        "companyId": user_data.get("companyId"),
                        "resellerId": user_data.get("resellerId"),
                        "status": user_data["status"],
                        "is_active": True,
                        "password": make_password("demo123"),  # Default password
                        "created_at": timezone.now(),
                    },
                )

                # Set M2M branch access after save
                try:
                    branch_ids = user_data.get("branchAccess", []) or []
                    branch_ids = [int(b) for b in branch_ids if str(b).isdigit()]
                    if branch_ids:
                        from company.models import Branch

                        branches = Branch.objects.filter(id__in=branch_ids)
                        user.branchAccess.set(branches)
                    else:
                        user.branchAccess.clear()
                except Exception:
                    pass

                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created user: {username} ({user_data["role"]})'
                        )
                    )
                else:
                    # Update existing user
                    user.email = user_data["email"]
                    user.name = user_data["name"]
                    user.fullName = user_data["fullName"]
                    user.role = user_data["role"]
                    user.companyId = user_data.get("companyId")
                    user.resellerId = user_data.get("resellerId")
                    user.status = user_data["status"]
                    user.save()

                    # Update M2M branch access after save
                    try:
                        branch_ids = user_data.get("branchAccess", []) or []
                        branch_ids = [int(b) for b in branch_ids if str(b).isdigit()]
                        if branch_ids:
                            from company.models import Branch

                            branches = Branch.objects.filter(id__in=branch_ids)
                            user.branchAccess.set(branches)
                        else:
                            user.branchAccess.clear()
                    except Exception:
                        pass
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'Updated user: {username} ({user_data["role"]})'
                        )
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error creating user {username}: {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDemo users setup complete!"
                f"\nCreated: {created_count}"
                f"\nUpdated: {updated_count}"
                f"\n\nDemo passwords:"
                f"\n- Software Owner: owner123"
                f"\n- Resellers: reseller123"
                f"\n- Super Admin/Admin: admin123"
                f"\n- Managers: manager123"
                f"\n- Staff/Waiter/Chef/Cashier: staff123"
                f"\n- Fallback: demo123"
            )
        )
