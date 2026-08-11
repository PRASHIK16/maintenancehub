"""Forms for the assets app."""
from django import forms
from .models import Asset, AssetStatus


class AssetForm(forms.ModelForm):
    """ModelForm for creating and editing assets."""

    class Meta:
        model = Asset
        fields = [
            "asset_code", "name", "asset_type", "brand", "model_number",
            "serial_number", "location", "status", "purchase_date",
            "warranty_expiry", "notes",
        ]
        widgets = {
            "asset_code": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. AC-001"}),
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Main Hall Air Conditioner"}),
            "asset_type": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. HVAC, Electrical, Plumbing"}),
            "brand": forms.TextInput(attrs={"class": "form-input"}),
            "model_number": forms.TextInput(attrs={"class": "form-input"}),
            "serial_number": forms.TextInput(attrs={"class": "form-input"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "purchase_date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "warranty_expiry": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            from apps.organizations.models import Location
            self.fields["location"].queryset = Location.objects.filter(
                organization=organization, is_active=True
            )
        self.fields["location"].required = False
        self.fields["brand"].required = False
        self.fields["model_number"].required = False
        self.fields["serial_number"].required = False
        self.fields["purchase_date"].required = False
        self.fields["warranty_expiry"].required = False
        self.fields["notes"].required = False
