"""URL patterns for assets app."""
from django.urls import path
from . import views

app_name = "assets"

urlpatterns = [
    path("", views.AssetListView.as_view(), name="list"),
    path("create/", views.AssetCreateView.as_view(), name="create"),
    path("<int:pk>/", views.AssetDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.AssetEditView.as_view(), name="edit"),
    path("<int:pk>/retire/", views.AssetRetireView.as_view(), name="retire"),
]
