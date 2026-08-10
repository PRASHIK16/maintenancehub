"""
MaintenanceHub — Account Forms
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import User


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-input",
            "placeholder": "you@organization.com",
            "autocomplete": "email",
            "autofocus": True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Enter your password",
            "autocomplete": "current-password",
        })
    )
    remember_me = forms.BooleanField(required=False)


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Minimum 8 characters",
            "autocomplete": "new-password",
            "aria-describedby": "password-hint",
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Repeat your password",
            "autocomplete": "new-password",
        })
    )

    class Meta:
        model = User
        fields = ["full_name", "email", "phone"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Your full name", "autofocus": True}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "you@organization.com"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+91 9876 543210 (optional)"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
        if password and confirm and password != confirm:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "phone", "avatar", "bio", "unit_number",
                  "email_notifications", "push_notifications", "theme_preference"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+91 9876 543210"}),
            "bio": forms.Textarea(attrs={"class": "form-textarea", "rows": 3}),
            "unit_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Room 304, Flat 2B"}),
            "theme_preference": forms.Select(attrs={"class": "form-select"}),
        }
