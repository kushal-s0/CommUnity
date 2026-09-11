from allauth.account.forms import LoginForm, SignupForm
from django import forms
from django.conf import settings


def allowed_domains():
    return [d.strip().lower().lstrip('@') for d in settings.ALLOWED_EMAIL_DOMAINS if d.strip()]


def email_domain_allowed(email):
    domains = allowed_domains()
    return not domains or (email or '').lower().rsplit('@', 1)[-1] in domains


def domain_error_message():
    return "Only " + " / ".join(f"@{d}" for d in allowed_domains()) + " e-mail addresses can use CommUnity."


class CustomSignUpForm(SignupForm):
    full_name = forms.CharField(max_length=255, label='Full name',
                                widget=forms.TextInput(attrs={'placeholder': 'Your name', 'autocomplete': 'name'}))

    field_order = ['full_name', 'email', 'password1', 'password2']

    def save(self, request):
        user = super().save(request)
        profile = user.userprofile
        profile.full_name = self.cleaned_data['full_name']
        profile.save()
        return user


class CustomLoginForm(LoginForm):
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('login')  # allauth keeps the e-mail in 'login'
        if email and not email_domain_allowed(email):
            raise forms.ValidationError(domain_error_message())
        return cleaned_data


class ProfileForm(forms.Form):
    full_name = forms.CharField(max_length=255, label='Full name')
    profile_picture = forms.ImageField(required=False, label='Profile picture')
    department = forms.CharField(max_length=100, required=False)
    designation = forms.CharField(max_length=100, required=False)
    position = forms.CharField(max_length=100, required=False, label='Position / role in team',
                               widget=forms.TextInput(attrs={'placeholder': 'e.g. Technical Head'}))

    def __init__(self, *args, role=None, **kwargs):
        super().__init__(*args, **kwargs)
        if role != 'faculty':
            del self.fields['department']
            del self.fields['designation']
        if role not in ('core_member', 'member'):
            del self.fields['position']
