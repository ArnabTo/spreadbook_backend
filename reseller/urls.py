from django.urls import path
from . import views

app_name = "reseller"

urlpatterns = [
    # Reseller URLs
    path(
        "resellers/",
        views.ResellerListCreateView.as_view(),
        name="reseller-list-create",
    ),
    path(
        "resellers/<int:pk>/",
        views.ResellerDetailView.as_view(),
        name="reseller-detail",
    ),
    path(
        "resellers/<int:pk>/stats/",
        views.ResellerStatsView.as_view(),
        name="reseller-stats",
    ),
    path(
        "resellers/<int:reseller_id>/status/",
        views.update_reseller_status,
        name="update-reseller-status",
    ),
    path(
        "resellers/<int:reseller_id>/commissions/",
        views.reseller_commissions_by_reseller,
        name="reseller-commissions",
    ),
    # Commission URLs
    path(
        "commissions/",
        views.ResellerCommissionListCreateView.as_view(),
        name="commission-list-create",
    ),
    path(
        "commissions/<int:pk>/",
        views.ResellerCommissionDetailView.as_view(),
        name="commission-detail",
    ),
    path(
        "commissions/<int:commission_id>/mark-paid/",
        views.mark_commission_paid,
        name="mark-commission-paid",
    ),
    # Dashboard and statistics
    path("dashboard/stats/", views.reseller_dashboard_stats, name="dashboard-stats"),
]
