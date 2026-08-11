"""Forms for the maintenance app."""
from django import forms
from .models import PreventiveMaintenance, MaintenanceFrequency, MaintenanceStatus


class PreventiveMaintenanceForm(forms.ModelForm):
    """ModelForm for creating and editing preventive maintenance schedules."""

    class Meta:
        model = PreventiveMaintenance
        fields = [
            "title", "description", "asset", "location", "assigned_team",
            "frequency", "interval_days", "next_due_at",
            "estimated_duration_hours", "checklist", "status",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Monthly HVAC Filter Check"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "asset": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "assigned_team": forms.Select(attrs={"class": "form-select"}),
            "frequency": forms.Select(attrs={"class": "form-select"}),
            "interval_days": forms.NumberInput(attrs={"class": "form-input", "placeholder": "e.g. 45"}),
            "next_due_at": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
            "estimated_duration_hours": forms.NumberInput(
                attrs={"class": "form-input", "step": "0.5", "placeholder": "e.g. 2.5"}
            ),
            "checklist": forms.Textarea(
                attrs={"class": "form-input", "rows": 5, "placeholder": "One item per line"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, organization=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._organization = organization
        self._user = user
        if organization:
            from apps.assets.models import Asset
            from apps.organizations.models import Location, Team
            self.fields["asset"].queryset = Asset.objects.filter(
                organization=organization, status="active"
            )
            self.fields["location"].queryset = Location.objects.filter(
                organization=organization, is_active=True
            )
            self.fields["assigned_team"].queryset = Team.objects.filter(
                organization=organization, is_active=True
            )
        # Optional fields
        for f in ["description", "asset", "location", "assigned_team",
                  "interval_days", "estimated_duration_hours", "checklist"]:
            self.fields[f].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self._organization:
            instance.organization = self._organization
        if self._user:
            instance.created_by = self._user
        if commit:
            instance.save()
        return instance
