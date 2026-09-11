from django import forms
from django.utils import timezone

from events.models import FacultyLockDate


class FacultyLockDateForm(forms.ModelForm):
    class Meta:
        model = FacultyLockDate
        fields = ['locked_date', 'reason']
        labels = {'locked_date': 'Date', 'reason': 'Reason'}
        widgets = {
            'locked_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.TextInput(attrs={'placeholder': 'e.g. End-semester exams, Annual fest'}),
        }

    def clean_locked_date(self):
        locked_date = self.cleaned_data['locked_date']
        if locked_date < timezone.localdate():
            raise forms.ValidationError("You can only reserve today or a future date.")
        return locked_date
