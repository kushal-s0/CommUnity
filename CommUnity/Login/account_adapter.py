from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError

from .forms import domain_error_message, email_domain_allowed


class MyAccountAdapter(DefaultAccountAdapter):
    def clean_email(self, email):
        """Restrict e-mail signup to the college domain."""
        email = super().clean_email(email)
        if not email_domain_allowed(email):
            raise ValidationError(domain_error_message())
        return email
