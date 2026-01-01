from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
import json


class ReportsViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_sales_overview_report(self):
        """Test sales overview report endpoint"""
        url = reverse("reports:sales_overview_report")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("success", response.json())
        self.assertTrue(response.json()["success"])
        self.assertIn("data", response.json())

        data = response.json()["data"]
        self.assertIn("period", data)
        self.assertIn("summary", data)
        self.assertIn("daily_breakdown", data)

    def test_sales_overview_with_period(self):
        """Test sales overview report with different periods"""
        periods = ["today", "week", "month", "quarter", "year"]

        for period in periods:
            url = reverse("reports:sales_overview_report")
            response = self.client.get(url, {"period": period})

            self.assertEqual(response.status_code, 200)
            data = response.json()["data"]
            self.assertEqual(data["period"], period)
            self.assertIn("date_range", data)

    def test_product_analysis_report(self):
        """Test product analysis report endpoint"""
        url = reverse("reports:product_analysis_report")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]
        self.assertIn("top_products_by_quantity", data)
        self.assertIn("top_products_by_revenue", data)
        self.assertIn("category_performance", data)

    def test_staff_performance_report(self):
        """Test staff performance report endpoint"""
        url = reverse("reports:staff_performance_report")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]
        self.assertIn("staff_performance", data)
        self.assertIn("team_summary", data)
        self.assertIn("rankings", data)

    def test_inventory_analysis_report(self):
        """Test inventory analysis report endpoint"""
        url = reverse("reports:inventory_analysis_report")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]
        self.assertIn("consumption_details", data)
        self.assertIn("summary", data)
        self.assertIn("alerts", data)

    def test_financial_analytics_report(self):
        """Test financial analytics report endpoint"""
        url = reverse("reports:financial_analytics_report")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]
        self.assertIn("financial_summary", data)
        self.assertIn("profitability", data)
        self.assertIn("cash_flow", data)

    def test_customer_analytics_report(self):
        """Test customer analytics report endpoint"""
        url = reverse("reports:customer_analytics_report")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]
        self.assertIn("customer_overview", data)
        self.assertIn("customer_segments", data)
        self.assertIn("retention_analysis", data)

    def test_export_report(self):
        """Test export report endpoint"""
        url = reverse("reports:export_report")

        # Test different report types
        report_types = ["sales_overview", "product_analysis", "staff_performance"]

        for report_type in report_types:
            response = self.client.get(
                url, {"report_type": report_type, "format": "json"}
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["success"])

            export_data = response.json()["export_data"]
            self.assertEqual(export_data["report_type"], report_type)
            self.assertEqual(export_data["format"], "json")

    def test_reports_summary(self):
        """Test reports summary endpoint"""
        url = reverse("reports:reports_summary")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        data = response.json()["data"]
        self.assertIn("available_reports", data)
        self.assertIn("categories", data)
        self.assertIn("total_reports", data)
        self.assertGreater(data["total_reports"], 0)

    def test_invalid_period_parameter(self):
        """Test handling of invalid period parameter"""
        url = reverse("reports:sales_overview_report")
        response = self.client.get(url, {"period": "invalid_period"})

        # Should still return 200 but with default period handling
        self.assertEqual(response.status_code, 200)

    def test_export_invalid_report_type(self):
        """Test export with invalid report type"""
        url = reverse("reports:export_report")
        response = self.client.get(
            url, {"report_type": "invalid_report", "format": "json"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertIn("error", response.json())


class ReportsUtilityFunctionsTestCase(TestCase):
    """Test utility functions used in reports"""

    def test_date_range_calculation(self):
        """Test date range calculation for different periods"""
        from reports.views import get_date_range

        # Test today
        start, end = get_date_range("today")
        self.assertEqual(start, end)
        self.assertEqual(start, timezone.now().date())

        # Test week
        start, end = get_date_range("week")
        self.assertEqual((end - start).days, 6)  # One week = 6 days difference

        # Test month
        start, end = get_date_range("month")
        self.assertEqual(start.day, 1)  # Should start from first day of month

    def test_safe_model_query(self):
        """Test safe model query function"""
        from reports.views import safe_model_query

        # Test with valid model
        queryset = safe_model_query("Sale")
        self.assertIsNotNone(queryset)

        # Test with invalid model
        queryset = safe_model_query("NonExistentModel")
        self.assertIsNotNone(queryset)  # Should return mock queryset
        self.assertEqual(queryset.count(), 0)


class ReportsIntegrationTestCase(TestCase):
    """Integration tests for reports functionality"""

    def test_all_reports_endpoints(self):
        """Test that all report endpoints return valid data structures"""
        endpoints = [
            "reports:sales_overview_report",
            "reports:product_analysis_report",
            "reports:staff_performance_report",
            "reports:inventory_analysis_report",
            "reports:financial_analytics_report",
            "reports:customer_analytics_report",
            "reports:reports_summary",
        ]

        for endpoint_name in endpoints:
            url = reverse(endpoint_name)
            response = self.client.get(url)

            self.assertEqual(
                response.status_code, 200, f"Failed for endpoint: {endpoint_name}"
            )

            json_response = response.json()
            self.assertIn(
                "success", json_response, f"Missing success field in {endpoint_name}"
            )
            self.assertTrue(
                json_response["success"], f"Success=False for {endpoint_name}"
            )
            self.assertIn(
                "data", json_response, f"Missing data field in {endpoint_name}"
            )

    def test_period_consistency_across_reports(self):
        """Test that all reports handle periods consistently"""
        periods = ["today", "week", "month"]
        report_endpoints = [
            "reports:sales_overview_report",
            "reports:product_analysis_report",
            "reports:staff_performance_report",
            "reports:inventory_analysis_report",
            "reports:financial_analytics_report",
            "reports:customer_analytics_report",
        ]

        for period in periods:
            for endpoint_name in report_endpoints:
                url = reverse(endpoint_name)
                response = self.client.get(url, {"period": period})

                self.assertEqual(response.status_code, 200)
                data = response.json()["data"]
                self.assertEqual(
                    data["period"],
                    period,
                    f"Period mismatch in {endpoint_name} for period {period}",
                )
                self.assertIn(
                    "date_range",
                    data,
                    f"Missing date_range in {endpoint_name} for period {period}",
                )

    def test_currency_consistency(self):
        """Test that currency is consistently shown across all financial data"""
        endpoints_with_currency = [
            "reports:sales_overview_report",
            "reports:product_analysis_report",
            "reports:financial_analytics_report",
            "reports:customer_analytics_report",
        ]

        for endpoint_name in endpoints_with_currency:
            url = reverse(endpoint_name)
            response = self.client.get(url)

            data = response.json()["data"]

            # Check that currency symbol is present in appropriate places
            if "summary" in data and "currency" in data["summary"]:
                self.assertEqual(data["summary"]["currency"], "৳")
