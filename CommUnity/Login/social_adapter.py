from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

from .forms import domain_error_message, email_domain_allowed


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = (sociallogin.user.email or '').lower()
        if email and not email_domain_allowed(email):
            messages.error(request, domain_error_message())
            raise ImmediateHttpResponse(redirect('account_login'))

        if sociallogin.is_existing or not email:
            return
        # Link a Google login to an existing e-mail/password account.
        existing_user = get_user_model().objects.filter(email__iexact=email).first()
        if existing_user:
            sociallogin.connect(request, existing_user)

    def is_open_for_signup(self, request, sociallogin):
        return email_domain_allowed(sociallogin.user.email)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        profile = user.userprofile
        if not profile.full_name:
            profile.full_name = user.get_full_name() or user.email.split('@')[0]
            profile.save()
        return user
