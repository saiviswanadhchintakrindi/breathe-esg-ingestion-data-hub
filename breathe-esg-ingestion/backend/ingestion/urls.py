from django.urls import path, include
from rest_framework.routers import SimpleRouter
from ingestion.views import (
    OrganizationViewSet, FacilityViewSet, RawIngestionSourceViewSet,
    NormalizedRecordViewSet, AuditLogViewSet, IngestAPIView, DashboardSummaryView
)

router = SimpleRouter(trailing_slash=False)
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'facilities', FacilityViewSet, basename='facility')
router.register(r'raw-sources', RawIngestionSourceViewSet, basename='raw-source')
router.register(r'records', NormalizedRecordViewSet, basename='record')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
    path('ingest/', IngestAPIView.as_view(), name='api-ingest'),
    path('dashboard-summary/', DashboardSummaryView.as_view(), name='api-dashboard-summary'),
]
