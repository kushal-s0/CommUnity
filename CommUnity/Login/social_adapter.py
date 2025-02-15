from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.http import HttpResponse

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Check if user already exists
        if sociallogin.is_existing:
            return
        
        # Try linking to an existing user with the same email
        if sociallogin.account.provider == "google":
            user_email = sociallogin.user.email
            if not user_email:
                return
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                existing_user = User.objects.get(email=user_email)
                sociallogin.connect(request, existing_user)
            except User.DoesNotExist:
                pass  # No existing user, so they must go through signup
