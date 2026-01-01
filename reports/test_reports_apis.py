#!/usr/bin/env python3
"""
Test script for Reports Center APIs
This script tests all the reports endpoints to ensure they're working correctly.
"""
import sys
import os

# Add the Django project path to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ERP_Shop.settings")

import django

django.setup()

from django.test import Client
from django.urls import reverse
import json


def test_reports_endpoints():
    """Test all reports endpoints"""
    client = Client()

    # List of all report endpoints to test
    endpoints = [
        ("reports:sales_overview_report", "Sales Overview Report"),
        ("reports:product_analysis_report", "Product Analysis Report"),
        ("reports:staff_performance_report", "Staff Performance Report"),
        ("reports:inventory_analysis_report", "Inventory Analysis Report"),
        ("reports:financial_analytics_report", "Financial Analytics Report"),
        ("reports:customer_analytics_report", "Customer Analytics Report"),
        ("reports:reports_summary", "Reports Summary"),
    ]

    print("🔍 Testing Reports Center APIs...")
    print("=" * 60)

    successful = 0
    failed = 0

    for endpoint_name, description in endpoints:
        try:
            url = reverse(endpoint_name)
            response = client.get(url)

            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    print(f"✅ {description}: PASSED")
                    successful += 1
                else:
                    print(f"❌ {description}: FAILED - success=False")
                    print(f"   Error: {data.get('error', 'Unknown error')}")
                    failed += 1
            else:
                print(f"❌ {description}: FAILED - HTTP {response.status_code}")
                failed += 1

        except Exception as e:
            print(f"❌ {description}: FAILED - Exception: {str(e)}")
            failed += 1

    print("=" * 60)
    print(f"📊 Summary: {successful} passed, {failed} failed")
    print(f"✨ Success rate: {(successful / (successful + failed) * 100):.1f}%")

    return successful, failed


def test_report_with_different_periods():
    """Test reports with different time periods"""
    client = Client()
    periods = ["today", "week", "month", "quarter", "year"]

    print("\n🕐 Testing different time periods...")
    print("=" * 60)

    endpoint_name = "reports:sales_overview_report"

    for period in periods:
        try:
            url = reverse(endpoint_name)
            response = client.get(url, {"period": period})

            if response.status_code == 200:
                data = response.json()
                if data.get("success", False) and data["data"]["period"] == period:
                    print(f"✅ Period '{period}': PASSED")
                else:
                    print(f"❌ Period '{period}': FAILED")
            else:
                print(f"❌ Period '{period}': FAILED - HTTP {response.status_code}")

        except Exception as e:
            print(f"❌ Period '{period}': FAILED - Exception: {str(e)}")


def test_export_functionality():
    """Test export functionality"""
    client = Client()

    print("\n📤 Testing export functionality...")
    print("=" * 60)

    export_tests = [
        ("sales_overview", "json"),
        ("product_analysis", "json"),
        ("staff_performance", "json"),
        ("financial_analytics", "csv"),
        ("customer_analytics", "pdf"),
    ]

    for report_type, format_type in export_tests:
        try:
            url = reverse("reports:export_report")
            response = client.get(
                url, {"report_type": report_type, "format": format_type}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    print(f"✅ Export {report_type} ({format_type}): PASSED")
                else:
                    print(f"❌ Export {report_type} ({format_type}): FAILED")
            else:
                print(
                    f"❌ Export {report_type} ({format_type}): FAILED - HTTP {response.status_code}"
                )

        except Exception as e:
            print(
                f"❌ Export {report_type} ({format_type}): FAILED - Exception: {str(e)}"
            )


def display_sample_data():
    """Display sample data from one report"""
    client = Client()

    print("\n📋 Sample Report Data...")
    print("=" * 60)

    try:
        url = reverse("reports:sales_overview_report")
        response = client.get(url, {"period": "month"})

        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                report_data = data["data"]
                summary = report_data["summary"]

                print(f"📅 Period: {report_data['period']}")
                print(
                    f"📊 Total Revenue: {summary['currency']}{summary['total_revenue']:,.2f}"
                )
                print(f"📦 Total Orders: {summary['total_orders']:,}")
                print(
                    f"💰 Average Order Value: {summary['currency']}{summary['avg_order_value']:,.2f}"
                )
                print(
                    f"🏆 Max Order Value: {summary['currency']}{summary['max_order_value']:,.2f}"
                )

                if report_data.get("daily_breakdown"):
                    print(
                        f"📈 Daily breakdown entries: {len(report_data['daily_breakdown'])}"
                    )

                if report_data.get("payment_methods"):
                    print(
                        f"💳 Payment methods tracked: {len(report_data['payment_methods'])}"
                    )

            else:
                print("❌ Failed to retrieve sample data")
        else:
            print(f"❌ HTTP {response.status_code} error")

    except Exception as e:
        print(f"❌ Exception: {str(e)}")


if __name__ == "__main__":
    print("🚀 Reports Center API Test Suite")
    print("=" * 60)

    # Test all endpoints
    successful, failed = test_reports_endpoints()

    # Test different periods
    test_report_with_different_periods()

    # Test export functionality
    test_export_functionality()

    # Show sample data
    display_sample_data()

    print("\n" + "=" * 60)
    print("🎉 Testing completed!")

    if failed == 0:
        print("🌟 All tests passed! Reports Center is ready to use.")
    else:
        print(f"⚠️  {failed} tests failed. Please check the issues above.")
