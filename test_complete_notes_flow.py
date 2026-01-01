"""
Complete end-to-end test: Create order and verify notes are saved to database
Run: python manage.py shell < test_complete_notes_flow.py
"""

from sales.models import Sale, InvoiceItem
from sales.serializers import POSOrderCreateSerializer
from django.contrib.auth import get_user_model
from companies.models import Company, Branch
from decimal import Decimal

User = get_user_model()

print("\n" + "=" * 70)
print("🧪 COMPLETE END-TO-END NOTES TEST")
print("=" * 70 + "\n")

# Get or create test user, company, branch
try:
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("⚠️  No superuser found. Creating test user...")
        user = User.objects.create_superuser(
            username="testadmin", email="test@test.com", password="testpass123"
        )
        print(f"   ✓ Created user: {user.username}")
    else:
        print(f"✓ Using existing user: {user.username}")

    company = Company.objects.first()
    if not company:
        print("⚠️  No company found. Please create a company first.")
        exit(1)
    print(f"✓ Using company: {company.name}")

    branch = Branch.objects.first()
    if branch:
        print(f"✓ Using branch: {branch.name}")
    else:
        print("⚠️  No branch found (optional)")
        branch = None

except Exception as e:
    print(f"❌ Setup error: {e}")
    exit(1)

print("\n" + "-" * 70 + "\n")

# Test order data with notes
test_data = {
    "order_type": "dine-in",
    "table_number": "Test-Table-5",
    "payment_method": "cash",
    "currency": "BDT",
    "notes": "POS Order test-456",
    "special_instructions": "🎂 Birthday celebration - bring cake at 8:30 PM",
    "tax_rate": 10.0,
    "discount_type": "none",
    "discount_value": 0,
    "items": [
        {
            "id": "test-burger",
            "name": "Test Burger",
            "price": 250,
            "quantity": 2,
            "category": "main",
            "preparation_time": 15,
            "notes": "🚫 No pickles, 🥫 extra sauce",
        },
        {
            "id": "test-pizza",
            "name": "Test Pizza",
            "price": 450,
            "quantity": 1,
            "category": "main",
            "preparation_time": 20,
            "notes": "🧀 Extra cheese, 🌶️ extra spicy",
        },
    ],
}

print("📝 Creating order with notes...")
print(f"   Order-level: '{test_data['special_instructions']}'")
print(f"   Item 1: '{test_data['items'][0]['notes']}'")
print(f"   Item 2: '{test_data['items'][1]['notes']}'")
print()

# Create order
try:
    # Create serializer with context
    class MockRequest:
        def __init__(self, user):
            self.user = user

    mock_request = MockRequest(user)

    serializer = POSOrderCreateSerializer(
        data=test_data, context={"request": mock_request}
    )

    if not serializer.is_valid():
        print(f"❌ Validation failed: {serializer.errors}")
        exit(1)

    # Add company and branch to validated data
    serializer.validated_data["companyId"] = company
    serializer.validated_data["branch"] = branch

    # Create the order
    order = serializer.create(serializer.validated_data)

    print(f"✅ Order created successfully!")
    print(f"   Order Number: {order.order_number}")
    print(f"   ID: {order.id}")
    print()

except Exception as e:
    print(f"❌ Failed to create order: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

# Verify notes were saved
print("-" * 70)
print("🔍 VERIFYING NOTES IN DATABASE")
print("-" * 70 + "\n")

# Fetch the order from database
db_order = Sale.objects.get(id=order.id)

print("1️⃣  Order-Level Notes:")
print(f"   Order.notes content:")
print(f"   '{db_order.notes}'")
print()

if "Birthday celebration" in db_order.notes:
    print("   ✅ PASS: Special instructions found in order notes!")
else:
    print("   ❌ FAIL: Special instructions NOT found in order notes!")

print()

# Check per-item notes
print("2️⃣  Per-Item Notes:")
items = InvoiceItem.objects.filter(sell_invoice=db_order)
print(f"   Total items: {items.count()}")
print()

for idx, item in enumerate(items, 1):
    print(f"   Item {idx}: {item.title}")
    print(f"      Quantity: {item.quantity}")
    print(f"      special_instructions: '{item.special_instructions}'")

    if item.special_instructions and item.special_instructions.strip():
        print(f"      ✅ PASS: Item notes saved!")
    else:
        print(f"      ⚠️  NOTICE: No notes for this item")
    print()

# Final summary
print("=" * 70)
print("📊 FINAL VERIFICATION")
print("=" * 70 + "\n")

# Check what we expected vs what we got
expected_order_note = "Birthday celebration"
expected_item1_note = "No pickles"
expected_item2_note = "Extra cheese"

order_note_ok = expected_order_note in db_order.notes
item1_note_ok = (
    items[0].special_instructions
    and expected_item1_note in items[0].special_instructions
)
item2_note_ok = (
    items[1].special_instructions
    and expected_item2_note in items[1].special_instructions
)

print(f"✓ Order created: {db_order.order_number}")
print(
    f"{'✅' if order_note_ok else '❌'} Order-level notes: {'SAVED' if order_note_ok else 'MISSING'}"
)
print(
    f"{'✅' if item1_note_ok else '❌'} Item 1 notes: {'SAVED' if item1_note_ok else 'MISSING'}"
)
print(
    f"{'✅' if item2_note_ok else '❌'} Item 2 notes: {'SAVED' if item2_note_ok else 'MISSING'}"
)
print()

if order_note_ok and item1_note_ok and item2_note_ok:
    print("🎉 SUCCESS! All notes are properly saved to database!")
    print()
    print("✅ Frontend → Backend → Database flow is working perfectly!")
else:
    print("⚠️  Some notes were not saved properly.")
    print("   Please review the serializer and model code.")

print()
print(f"💡 To view this order in admin: /admin/sales/sale/{db_order.id}/")
print()
print("=" * 70)
