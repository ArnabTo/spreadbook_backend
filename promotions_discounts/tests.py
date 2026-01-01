from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from authenticator.models import User
from company.models import Company, Branch
from .models import Promotion, PromotionUsage


class PromotionModelTest(TestCase):
    """Test Promotion model functionality"""

    def setUp(self):
        self.company = Company.objects.create(
            name="Test Restaurant", email="test@restaurant.com"
        )

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            companyId=self.company,
        )

        self.promotion = Promotion.objects.create(
            name="Test Promotion",
            type="percentage",
            value=20.00,
            code="TEST20",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            min_order_value=0.00,
            max_discount=50.00,
            usage_limit=100,
            company=self.company,
            created_by=self.user,
            description="Test promotion",
        )

    def test_promotion_creation(self):
        """Test promotion is created correctly"""
        self.assertEqual(self.promotion.name, "Test Promotion")
        self.assertEqual(self.promotion.code, "TEST20")
        self.assertEqual(self.promotion.company, self.company)
        self.assertTrue(self.promotion.is_valid())

    def test_promotion_discount_calculation(self):
        """Test discount calculation"""
        order_value = 100.00
        discount = self.promotion.calculate_discount(order_value)
        self.assertEqual(discount, 20.00)  # 20% of 100

        # Test max discount limit
        order_value = 1000.00
        discount = self.promotion.calculate_discount(order_value)
        self.assertEqual(discount, 50.00)  # Max discount cap

    def test_promotion_can_apply_to_order(self):
        """Test order validation"""
        # Should work for order above min value
        self.assertTrue(self.promotion.can_apply_to_order(10.00))

        # Test with min order value
        self.promotion.min_order_value = 50.00
        self.promotion.save()

        self.assertFalse(self.promotion.can_apply_to_order(25.00))
        self.assertTrue(self.promotion.can_apply_to_order(75.00))

    def test_promotion_status_auto_update(self):
        """Test automatic status updates"""
        # Future promotion should be scheduled
        future_promotion = Promotion.objects.create(
            name="Future Promotion",
            code="FUTURE20",
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=10),
            company=self.company,
            type="percentage",
            value=20.00,
        )
        self.assertEqual(future_promotion.status, "scheduled")

        # Past promotion should be expired
        past_promotion = Promotion.objects.create(
            name="Past Promotion",
            code="PAST20",
            start_date=timezone.now() - timedelta(days=10),
            end_date=timezone.now() - timedelta(days=1),
            company=self.company,
            type="percentage",
            value=20.00,
        )
        self.assertEqual(past_promotion.status, "expired")

    def test_usage_percentage(self):
        """Test usage percentage calculation"""
        self.promotion.used_count = 25
        self.promotion.save()
        self.assertEqual(self.promotion.usage_percentage, 25.0)

    def test_is_expiring_soon(self):
        """Test expiring soon check"""
        # Promotion expiring in 3 days
        soon_expiring = Promotion.objects.create(
            name="Soon Expiring",
            code="SOON20",
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=3),
            company=self.company,
            type="percentage",
            value=20.00,
            status="active",
        )
        self.assertTrue(soon_expiring.is_expiring_soon)


class PromotionAPITest(APITestCase):
    """Test Promotion API endpoints"""

    def setUp(self):
        self.company = Company.objects.create(
            name="API Test Restaurant", email="api@restaurant.com"
        )

        self.user = User.objects.create_user(
            username="apiuser",
            email="api@example.com",
            password="testpass123",
            companyId=self.company,
        )

        self.client.force_authenticate(user=self.user)

        self.promotion_data = {
            "name": "API Test Promotion",
            "type": "percentage",
            "value": 15.00,
            "code": "API15",
            "startDate": timezone.now().isoformat(),
            "endDate": (timezone.now() + timedelta(days=30)).isoformat(),
            "minOrderValue": 0.00,
            "maxDiscount": 25.00,
            "usageLimit": 200,
            "applicableOn": "all",
            "targetItems": [],
            "description": "API test promotion",
        }

    def test_create_promotion_api(self):
        """Test creating promotion via API"""
        url = "/api/promotions/create/"
        response = self.client.post(url, self.promotion_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["name"], "API Test Promotion")

    def test_get_all_promotions_api(self):
        """Test getting all promotions via API"""
        # Create a test promotion first
        Promotion.objects.create(
            name="Test List Promotion",
            code="LIST20",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            company=self.company,
            type="percentage",
            value=20.00,
        )

        url = "/api/promotions/all/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["count"], 1)

    def test_validate_promotion_code_api(self):
        """Test promotion code validation via API"""
        promotion = Promotion.objects.create(
            name="Validation Test",
            code="VALID20",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            company=self.company,
            type="percentage",
            value=20.00,
            min_order_value=10.00,
        )

        url = "/api/promotions/validate-code/"
        data = {"code": "VALID20", "order_value": 50.00}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["valid"])
        self.assertEqual(response.data["discount_amount"], 10.0)  # 20% of 50
        self.assertEqual(response.data["final_amount"], 40.0)

    def test_validate_promotion_code_api_b2g1(self):
        """Buy 2 Get 1 free should discount one unit per 3 for eligible items."""
        Promotion.objects.create(
            name="Buy 2 Get 1 Burger",
            code="B2G1-BURGER",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            company=self.company,
            type="b2g1",
            value=0.00,
            applicable_on="item",
            target_items=["burger"],
            min_order_value=0.00,
            max_discount=999999,
            status="active",
        )

        url = "/api/promotions/validate-code/"
        data = {
            "code": "B2G1-BURGER",
            "order_value": 300.00,
            "items": [
                {"id": "burger", "price": 100.0, "quantity": 3, "category": "main"}
            ],
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["valid"])
        self.assertEqual(response.data["discount_amount"], 100.0)
        self.assertEqual(response.data["final_amount"], 200.0)

    def test_validate_promotion_code_api_combo_price(self):
        """Combo promotion should reduce price of a set of required items to the combo price."""
        Promotion.objects.create(
            name="Burger+Fries+Coke Combo",
            code="COMBO-1",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            company=self.company,
            type="combo",
            value=250.00,  # combo price
            applicable_on="item",
            target_items=["burger", "fries", "coke"],
            min_order_value=0.00,
            max_discount=999999,
            status="active",
        )

        url = "/api/promotions/validate-code/"
        data = {
            "code": "COMBO-1",
            "order_value": 350.00,
            "items": [
                {"id": "burger", "price": 200.0, "quantity": 1, "category": "main"},
                {"id": "fries", "price": 100.0, "quantity": 1, "category": "sides"},
                {"id": "coke", "price": 50.0, "quantity": 1, "category": "drinks"},
            ],
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["valid"])
        self.assertEqual(response.data["discount_amount"], 100.0)
        self.assertEqual(response.data["final_amount"], 250.0)

    def test_get_promotion_stats_api(self):
        """Test promotion statistics API"""
        # Create some test promotions
        Promotion.objects.create(
            name="Stats Test 1",
            code="STATS1",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            company=self.company,
            type="percentage",
            value=20.00,
            status="active",
        )

        Promotion.objects.create(
            name="Stats Test 2",
            code="STATS2",
            start_date=timezone.now() + timedelta(days=5),
            end_date=timezone.now() + timedelta(days=35),
            company=self.company,
            type="fixed",
            value=10.00,
            status="scheduled",
        )

        url = "/api/promotions/stats/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        stats = response.data["data"]
        self.assertEqual(stats["total_promotions"], 2)
        self.assertEqual(stats["active_promotions"], 1)
        self.assertEqual(stats["scheduled_promotions"], 1)

    def test_unauthorized_access(self):
        """Test API requires authentication"""
        self.client.force_authenticate(user=None)

        url = "/api/promotions/all/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
