from django import forms
from django.core.exceptions import ValidationError
from allauth.account.forms import SignupForm, LoginForm

class CustomSignUpForm(SignupForm):
    email = forms.EmailField(required=True)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email.endswith("@somaiya.edu"):
            raise ValidationError("Only @somaiya.edu emails are allowed.")
        return email

class CustomLoginForm(LoginForm):
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("login")  # 'login' holds the email in allauth

        if email and not email.endswith("@somaiya.edu"):
            raise forms.ValidationError("Only @somaiya.edu emails can log in.")

        return cleaned_data
