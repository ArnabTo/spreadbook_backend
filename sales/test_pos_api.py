from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from sales.models import Sale, InvoiceItem
import json

User = get_user_model()


class POSOrderAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Use an unrestricted user to bypass company/branch scoping in API tests.
        self.user = User.objects.create_superuser(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

    def test_create_pos_order(self):
        """Test creating a POS order via API"""
        order_data = {
            "order_type": "dine-in",
            "table_number": "5",
            "payment_method": "cash",
            "currency": "BDT",
            "tax_rate": 10.0,
            "service_charge_rate": 5.0,
            "tip_amount": 50.0,
            "items": [
                {
                    "id": "menu-item-1",
                    "name": "Burger",
                    "price": 250.00,
                    "quantity": 2,
                    "category": "main-course",
                    "preparation_time": 15,
                },
                {
                    "id": "menu-item-2",
                    "name": "Fries",
                    "price": 80.00,
                    "quantity": 1,
                    "category": "sides",
                    "preparation_time": 10,
                },
            ],
        }

        response = self.client.post("/api/pos/orders/", order_data, format="json")

        print("Response status:", response.status_code)
        print("Response data:", json.dumps(response.data, indent=2))

        # Should create order successfully
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that order was created
        self.assertTrue(Sale.objects.filter(order_number__isnull=False).exists())

        order = Sale.objects.filter(order_number__isnull=False).first()
        self.assertIsNotNone(order)
        # Backend canonicalizes legacy order_type aliases like "dine-in" into "In-Store".
        self.assertEqual(order.order_type, "In-Store")
        self.assertEqual(order.table_number, "5")

        # Check items were created
        self.assertEqual(order.items.count(), 2)

        # Check totals were calculated
        self.assertGreater(order.totalAmount, 0)
        self.assertTrue(order.order_number.startswith("INV-"))

        # Verify service charge + tip math using the API response payload fields.
        # Subtotal = (250*2) + (80*1) = 580
        # Tax (10%) = 58
        # Service charge (5%) = 29
        # Tip = 50
        # Total = 580 + 58 + 29 + 50 = 717
        expected_subtotal = 580.0
        expected_tax_amount = 58.0
        expected_service_charge_amount = 29.0
        expected_tip_amount = 50.0
        expected_total_amount = 717.0

        self.assertAlmostEqual(
            float(response.data.get("subtotal") or 0), expected_subtotal, places=2
        )
        self.assertAlmostEqual(
            float(response.data.get("tax_amount") or 0), expected_tax_amount, places=2
        )
        self.assertAlmostEqual(
            float(response.data.get("service_charge_amount") or 0),
            expected_service_charge_amount,
            places=2,
        )
        self.assertAlmostEqual(
            float(response.data.get("tip_amount") or 0), expected_tip_amount, places=2
        )
        self.assertAlmostEqual(
            float(response.data.get("total_amount") or 0),
            expected_total_amount,
            places=2,
        )

    def test_create_pos_order_cash_received_is_quantized(self):
        """POS cash fields should accept high-precision floats and be rounded to 2dp."""
        order_data = {
            "order_type": "dine-in",
            "table_number": "5",
            "payment_method": "cash",
            "currency": "BDT",
            "tax_rate": 0.0,
            "cash_received": 100.1299,
            "change_amount": 0.0049,
            "items": [
                {
                    "id": "menu-item-1",
                    "name": "Burger",
                    "price": 10.00,
                    "quantity": 1,
                    "category": "main-course",
                    "preparation_time": 15,
                }
            ],
        }

        response = self.client.post("/api/pos/orders/", order_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = Sale.objects.filter(order_number__isnull=False).order_by("-id").first()
        self.assertIsNotNone(order)

        # Cash info is appended to notes in POSOrderCreateSerializer.
        self.assertIn("Cash Received: 100.13", order.notes)
        self.assertIn("Change: 0.00", order.notes)

    def test_refund_paid_pos_order_partial(self):
        """Test creating a partial refund for a paid POS order."""
        order_data = {
            "order_type": "dine-in",
            "table_number": "5",
            "payment_method": "cash",
            "currency": "BDT",
            "tax_rate": 0.0,
            "items": [
                {
                    "id": "menu-item-1",
                    "name": "Burger",
                    "price": 250.00,
                    "quantity": 2,
                    "category": "main-course",
                    "preparation_time": 15,
                },
            ],
        }

        create_resp = self.client.post("/api/pos/orders/", order_data, format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)

        order_id = create_resp.data["id"]
        order = Sale.objects.get(id=order_id)
        order.status = "paid"
        order.is_paid = True
        order.save(update_fields=["status", "is_paid"])

        invoice_item_id = create_resp.data["order_items"][0]["id"]

        refund_payload = {
            "reason": "Customer returned 1 item",
            "payment_method": "cash",
            "items": [{"invoice_item_id": invoice_item_id, "quantity": 1}],
        }

        refund_resp = self.client.post(
            f"/api/pos/orders/{order_id}/refund/", refund_payload, format="json"
        )

        self.assertEqual(refund_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(refund_resp.data.get("items") or []), 1)

        # Professional behavior: partial refunds do NOT mark the order as fully returned.
        order.refresh_from_db()
        self.assertFalse(order.is_return)

        # Refund the remaining quantity => order becomes fully returned.
        refund2_payload = {
            "reason": "Customer returned remaining item",
            "payment_method": "cash",
            "items": [{"invoice_item_id": invoice_item_id, "quantity": 1}],
        }
        refund2_resp = self.client.post(
            f"/api/pos/orders/{order_id}/refund/", refund2_payload, format="json"
        )
        self.assertEqual(refund2_resp.status_code, status.HTTP_201_CREATED)

        order.refresh_from_db()
        self.assertTrue(order.is_return)

        # Deleting a refund should recalculate the order return status.
        refund_id = refund_resp.data["id"]
        del_resp = self.client.delete(f"/api/pos/refunds/{refund_id}/")
        self.assertIn(
            del_resp.status_code, [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]
        )

        order.refresh_from_db()
        self.assertFalse(order.is_return)

    def test_refund_restock_to_inventory_increases_product_stock(self):
        """Refunds should add refunded quantities back into Product.in_stock when enabled."""
        from products.models.product_model import Product

        product = Product.objects.create(
            name="Test Product",
            price=100.0,
            in_stock=10,
        )

        order_data = {
            "order_type": "In-Store",
            "payment_method": "cash",
            "currency": "BDT",
            "tax_rate": 0.0,
            "service_charge_rate": 0.0,
            "tip_amount": 0.0,
            "items": [
                {
                    "id": str(product.id),
                    "name": "Test Product",
                    "price": 100.00,
                    "quantity": 2,
                    "category": "products",
                    "preparation_time": 0,
                }
            ],
        }

        create_resp = self.client.post("/api/pos/orders/", order_data, format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        order_id = create_resp.data["id"]

        # Stock should be reduced on sale creation.
        product.refresh_from_db()
        self.assertEqual(int(product.in_stock or 0), 8)

        # Mark paid (refund requires paid).
        order = Sale.objects.get(id=order_id)
        order.status = "paid"
        order.is_paid = True
        order.save(update_fields=["status", "is_paid"])

        invoice_item_id = create_resp.data["order_items"][0]["id"]

        # Omit restock_to_inventory => default True.
        refund_payload = {
            "payment_method": "cash",
            "items": [{"invoice_item_id": invoice_item_id, "quantity": 1}],
        }
        refund_resp = self.client.post(
            f"/api/pos/orders/{order_id}/refund/", refund_payload, format="json"
        )
        self.assertEqual(refund_resp.status_code, status.HTTP_201_CREATED)

        product.refresh_from_db()
        self.assertEqual(int(product.in_stock or 0), 9)

    def test_quick_purchase_convert_to_product_creates_stock_item(self):
        """Quick purchases can be converted into a Product with remaining stock."""
        # Create a quick purchase: bought 10, sold 4 => remaining 6.
        qp_payload = {
            "name": "Quick Item",
            "category": "products",
            "unit_cost": "50.00",
            "unit_price": "80.00",
            "qty_purchased": 10,
            "qty_sold": 4,
            "notes": "Bought for a customer order",
        }
        create_resp = self.client.post(
            "/api/supplychain/purchase/quick-purchases/", qp_payload, format="json"
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        qp_id = create_resp.data["uuid"]

        convert_resp = self.client.post(
            f"/api/supplychain/purchase/quick-purchases/{qp_id}/convert-to-product/",
            {},
            format="json",
        )
        self.assertEqual(convert_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(convert_resp.data.get("status"), "converted")
        self.assertIsNotNone(convert_resp.data.get("product_id"))

        # Product should exist with remaining_qty stock.
        from products.models.product_model import Product

        p = Product.objects.get(id=convert_resp.data["product_id"])
        self.assertEqual(p.name, "Quick Item")
        self.assertEqual(int(p.in_stock or 0), 6)
