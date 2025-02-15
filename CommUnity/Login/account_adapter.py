from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError

class MyAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        """
        Allow signup only for Google accounts with @somaiya.edu
        """
        sociallogin = request.session.get('socialaccount_last_login')
        if sociallogin and sociallogin['provider'] == 'google':
            email = sociallogin['email']
            if email.endswith("@somaiya.edu"):
                return True
            return False  # Block signup for non-matching emails
        return True  # Allow normal email-based signup
