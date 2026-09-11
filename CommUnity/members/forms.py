from django import forms

from committees.models import Announcement


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'message']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Registrations open for Hackathon 2.0'}),
            'message': forms.Textarea(attrs={'rows': 7}),
        }
        help_texts = {'message': 'Followers of your club/committee see this in their notifications.'}
