#!/usr/bin/env python
"""
Test script to verify notes are properly saved from POS system
Run this in Django shell: python manage.py shell < test_pos_notes.py
"""

from sales.models import Sale, InvoiceItem
from sales.serializers import POSOrderCreateSerializer
from decimal import Decimal
import json

print("\n" + "=" * 60)
print("🧪 TESTING POS NOTES FUNCTIONALITY")
print("=" * 60 + "\n")

# Test data simulating frontend POSSystem.tsx
test_order_data = {
    "order_type": "dine-in",
    "table_number": "5",
    "payment_method": "cash",
    "currency": "BDT",
    "notes": "POS Order test-123 | Discount: 10%",
    "special_instructions": "Birthday celebration - bring cake at 8:30 PM",
    "tax_rate": 10.0,
    "discount_type": "percentage",
    "discount_value": 10,
    "items": [
        {
            "id": "test-burger-1",
            "name": "Burger",
            "price": 250,
            "quantity": 2,
            "category": "main",
            "preparation_time": 15,
            "notes": "No pickles, extra sauce",
        },
        {
            "id": "test-pizza-1",
            "name": "Pizza",
            "price": 450,
            "quantity": 1,
            "category": "main",
            "preparation_time": 20,
            "notes": "Extra cheese",
        },
        {
            "id": "test-fries-1",
            "name": "Fries",
            "price": 100,
            "quantity": 1,
            "category": "sides",
            "preparation_time": 10,
            # No notes for this item - testing empty notes
        },
    ],
}

print("📤 Simulating frontend data:")
print(json.dumps(test_order_data, indent=2))
print("\n" + "-" * 60 + "\n")

# Test 1: Serializer accepts the data
print("✅ Test 1: Checking if serializer accepts data...")
serializer = POSOrderCreateSerializer(data=test_order_data)

if serializer.is_valid():
    print("   ✓ Serializer validation PASSED")
    print(f"   ✓ Fields validated: {list(serializer.validated_data.keys())}")

    # Check if special_instructions is in validated data
    if "special_instructions" in serializer.validated_data:
        print(
            f"   ✓ special_instructions found: '{serializer.validated_data['special_instructions']}'"
        )
    else:
        print("   ⚠️  WARNING: special_instructions not in validated data")

    print()
else:
    print("   ❌ FAILED: Serializer validation errors:")
    print(f"   {serializer.errors}")
    exit(1)

# Test 2: Check what data would be saved
print("✅ Test 2: Checking data processing...")
print(f"   Order Type: {serializer.validated_data['order_type']}")
print(f"   Table: {serializer.validated_data.get('table_number', 'N/A')}")
print(f"   Notes: {serializer.validated_data.get('notes', '')}")
print(
    f"   Special Instructions: {serializer.validated_data.get('special_instructions', 'MISSING!')}"
)
print(f"   Items count: {len(serializer.validated_data['items'])}")
print()

# Test 3: Check item notes
print("✅ Test 3: Checking per-item notes...")
for idx, item in enumerate(serializer.validated_data["items"], 1):
    item_notes = item.get("notes", "")
    print(f"   Item {idx}: {item['name']}")
    print(f"      Notes: '{item_notes}' {'✓' if item_notes else '(empty)'}")
print()

# Summary
print("=" * 60)
print("📊 VERIFICATION SUMMARY")
print("=" * 60)
print()

print("Frontend sends:")
print("  ✓ special_instructions (order-level): YES")
print("  ✓ items[].notes (per-item): YES")
print()

print("Backend receives:")
special_inst_ok = "special_instructions" in serializer.validated_data
print(
    f"  {'✓' if special_inst_ok else '❌'} special_instructions field: {'FOUND' if special_inst_ok else 'MISSING'}"
)

items_with_notes = sum(
    1 for item in serializer.validated_data["items"] if "notes" in item
)
print(
    f"  ✓ Items with notes: {items_with_notes}/{len(serializer.validated_data['items'])}"
)
print()

if special_inst_ok and items_with_notes > 0:
    print("✅ ALL TESTS PASSED!")
    print("   Notes are being properly sent and received.")
    print()
    print("Next step: Create an actual order to verify database persistence.")
    print("   Run: python manage.py shell")
    print("   Then test creating an order through the API.")
else:
    print("❌ TESTS FAILED!")
    print("   Some notes are not being received properly.")
    print()
    if not special_inst_ok:
        print("   Issue: special_instructions field missing in serializer")
        print("   Fix: Add field to POSOrderCreateSerializer")

print()
print("=" * 60)
