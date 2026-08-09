"""
MaintenanceHub — Ticket Forms
"""
from django import forms
from django.core.exceptions import ValidationError

from .models import Ticket, TicketComment, Priority
from apps.organizations.models import Location


class MultipleFileInput(forms.FileInput):
    """Custom widget supporting multiple file selection (Django 4.2+)."""
    allow_multiple_selected = True

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"]["multiple"] = True
        super().__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        return files.getlist(name)


class MultipleFileField(forms.FileField):
    """FileField that accepts multiple files."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        # data is a list of files from MultipleFileInput
        if not data:
            return []
        result = []
        for item in data:
            result.append(super().clean(item, initial))
        return result


class TicketCreateForm(forms.ModelForm):
    attachments = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            "class": "hidden",
            "id": "ticket-file-upload",
            "accept": "image/*,.pdf,.doc,.docx",
        })
    )

    class Meta:
        model = Ticket
        fields = [
            "title", "description", "category", "location",
            "priority", "preferred_visit_time", "contact_phone",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Brief description of the issue",
                "autofocus": True,
            }),
            "description": forms.Textarea(attrs={
                "class": "form-textarea",
                "rows": 4,
                "placeholder": "Describe the issue in detail. When did it start? What have you tried?",
            }),
            "category": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "preferred_visit_time": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "e.g. Weekday mornings, Anytime except weekends",
            }),
            "contact_phone": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "+91 9876 543210",
            }),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["category"].queryset = (
                __import__("apps.tickets.models", fromlist=["Category"])
                .Category.objects.filter(organization=organization, parent__isnull=True, is_active=True)
            )
            self.fields["location"].queryset = Location.objects.filter(
                organization=organization, is_active=True
            )
        self.fields["category"].empty_label = "Select category"
        self.fields["location"].empty_label = "Select location"


class TicketUpdateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "priority", "category", "location"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            from apps.tickets.models import Category
            self.fields["category"].queryset = Category.objects.filter(
                organization=organization, parent__isnull=True, is_active=True
            )
            self.fields["location"].queryset = Location.objects.filter(
                organization=organization, is_active=True
            )


class CommentForm(forms.Form):
    body = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-textarea",
            "rows": 3,
            "placeholder": "Write your comment here…",
        }),
        min_length=1,
    )
    is_internal = forms.BooleanField(required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import UserRole
        if user and user.role == UserRole.USER:
            self.fields.pop("is_internal", None)


class AssignTicketForm(forms.Form):
    assigned_to = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Select staff member",
    )
    team = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="No team",
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 2}),
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            from apps.accounts.models import User, UserRole
            from apps.organizations.models import Team
            self.fields["assigned_to"].queryset = User.objects.filter(
                organization=organization,
                role__in=[UserRole.STAFF, UserRole.MANAGER],
                is_active=True,
            )
            self.fields["team"].queryset = Team.objects.filter(
                organization=organization,
                is_active=True,
            )
