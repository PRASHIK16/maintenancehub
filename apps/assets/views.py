"""Asset management views."""
from django.views import View
from django.views.generic import ListView, DetailView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from apps.accounts.mixins import OrgRequiredMixin, ManagerRequiredMixin
from .models import Asset, AssetStatus
from .forms import AssetForm


class AssetListView(OrgRequiredMixin, ListView):
    """List all assets for the current organization."""
    template_name = "assets/list.html"
    context_object_name = "assets"
    paginate_by = 25

    def get_queryset(self):
        qs = Asset.objects.filter(
            organization=self.request.user.organization
        ).select_related("location")

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(asset_code__icontains=q) |
                Q(asset_type__icontains=q) |
                Q(serial_number__icontains=q)
            )

        status = self.request.GET.get("status", "")
        if status:
            qs = qs.filter(status=status)

        asset_type = self.request.GET.get("asset_type", "")
        if asset_type:
            qs = qs.filter(asset_type__icontains=asset_type)

        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = self.request.user.organization
        ctx["status_choices"] = AssetStatus.choices
        ctx["total_count"] = Asset.objects.filter(organization=org).count()
        ctx["active_count"] = Asset.objects.filter(
            organization=org, status=AssetStatus.ACTIVE
        ).count()
        ctx["maintenance_count"] = Asset.objects.filter(
            organization=org, status=AssetStatus.UNDER_MAINTENANCE
        ).count()
        return ctx


class AssetDetailView(OrgRequiredMixin, View):
    """Asset detail with maintenance history."""
    template_name = "assets/detail.html"

    def get(self, request, pk):
        asset = get_object_or_404(
            Asset, pk=pk, organization=request.user.organization
        )
        return render(request, self.template_name, {"asset": asset})


class AssetCreateView(ManagerRequiredMixin, View):
    """Create a new asset using AssetForm (managers and above)."""
    template_name = "assets/form.html"

    def get(self, request):
        form = AssetForm(organization=request.user.organization)
        return render(request, self.template_name, {"form": form, "action": "Create"})

    def post(self, request):
        form = AssetForm(request.POST, organization=request.user.organization)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.organization = request.user.organization
            asset.save()
            messages.success(request, f"Asset '{asset.name}' created successfully.")
            return redirect("assets:detail", pk=asset.pk)
        return render(request, self.template_name, {"form": form, "action": "Create"})


class AssetEditView(ManagerRequiredMixin, View):
    """Edit an existing asset."""
    template_name = "assets/form.html"

    def get(self, request, pk):
        asset = get_object_or_404(
            Asset, pk=pk, organization=request.user.organization
        )
        from apps.organizations.models import Location
        locations = Location.objects.filter(
            organization=request.user.organization, is_active=True
        )
        return render(request, self.template_name, {
            "asset": asset, "locations": locations, "action": "Edit"
        })

    def post(self, request, pk):
        asset = get_object_or_404(
            Asset, pk=pk, organization=request.user.organization
        )
        try:
            asset.name = request.POST["name"]
            asset.asset_type = request.POST["asset_type"]
            asset.brand = request.POST.get("brand", "")
            asset.model_number = request.POST.get("model_number", "")
            asset.serial_number = request.POST.get("serial_number", "")
            asset.location_id = request.POST.get("location") or None
            asset.status = request.POST.get("status", asset.status)
            asset.purchase_date = request.POST.get("purchase_date") or None
            asset.warranty_expiry = request.POST.get("warranty_expiry") or None
            asset.notes = request.POST.get("notes", "")
            asset.save()
            messages.success(request, f"Asset '{asset.name}' updated.")
            return redirect("assets:detail", pk=asset.pk)
        except Exception as e:
            messages.error(request, f"Error updating asset: {e}")
            return redirect("assets:edit", pk=asset.pk)


class AssetRetireView(ManagerRequiredMixin, View):
    """Mark an asset as retired."""

    def post(self, request, pk):
        asset = get_object_or_404(
            Asset, pk=pk, organization=request.user.organization
        )
        asset.status = AssetStatus.RETIRED
        asset.save()
        messages.success(request, f"Asset '{asset.name}' has been retired.")
        return redirect("assets:list")
