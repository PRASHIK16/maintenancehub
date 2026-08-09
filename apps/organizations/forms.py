"""Organization settings forms."""
from django import forms
from .models import Organization, Location, Team


class OrganizationProfileForm(forms.ModelForm):
    """Edit organization profile."""
    class Meta:
        model = Organization
        fields = [
            "name", "org_type", "description",
            "website", "phone", "email",
            "address", "city", "state", "country",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Organization name"}),
            "org_type": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-textarea", "rows": 3, "placeholder": "Brief description"}),
            "website": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+91 ..."}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "contact@example.com"}),
            "address": forms.TextInput(attrs={"class": "form-input", "placeholder": "Street address"}),
            "city": forms.TextInput(attrs={"class": "form-input", "placeholder": "City"}),
            "state": forms.TextInput(attrs={"class": "form-input", "placeholder": "State"}),
            "country": forms.TextInput(attrs={"class": "form-input", "placeholder": "Country"}),
        }


class OrganizationFeaturesForm(forms.ModelForm):
    """Feature flag settings."""
    class Meta:
        model = Organization
        fields = [
            "enable_asset_management",
            "enable_preventive_maintenance",
            "enable_ai_classification",
            "enable_sla",
        ]
        labels = {
            "enable_asset_management": "Asset Management",
            "enable_preventive_maintenance": "Preventive Maintenance Scheduling",
            "enable_ai_classification": "AI-Assisted Ticket Classification",
            "enable_sla": "SLA Tracking & Enforcement",
        }
        help_texts = {
            "enable_asset_management": "Track equipment, appliances and infrastructure items",
            "enable_preventive_maintenance": "Schedule recurring inspections and maintenance tasks",
            "enable_ai_classification": "Automatically suggest category and priority when tickets are created",
            "enable_sla": "Enforce response and resolution time targets per priority level",
        }


class LocationForm(forms.ModelForm):
    """Create or edit a location."""
    class Meta:
        model = Location
        fields = ["name", "location_type", "parent", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Block A, Lab 101"}),
            "location_type": forms.Select(attrs={"class": "form-select"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-textarea", "rows": 2, "placeholder": "Optional description"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = Location.objects.filter(
            organization=organization
        ).exclude(pk=self.instance.pk if self.instance.pk else None)
        self.fields["parent"].empty_label = "— Top level (no parent) —"
        self.fields["parent"].required = False


class TeamForm(forms.ModelForm):
    """Create or edit a maintenance team."""
    class Meta:
        model = Team
        fields = ["name", "description", "color", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Electrical Team"}),
            "description": forms.Textarea(attrs={"class": "form-textarea", "rows": 2, "placeholder": "Team responsibilities"}),
            "color": forms.TextInput(attrs={"class": "form-input", "type": "color", "style": "height:42px;padding:4px 6px;"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }
