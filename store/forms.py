from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignupForm(UserCreationForm):
    """
    UserCreationForm + a required `email` field.
    django.contrib.auth.models.User already has an `email` column built in —
    UserCreationForm just doesn't expose it by default, so we add it here.
    """
    email = forms.EmailField(required=True, help_text="We'll send your order receipts here.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    field_order = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user