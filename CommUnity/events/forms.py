from django import forms

from .models import Event, Location
from .services import slot_errors


class EventForm(forms.ModelForm):
    date_time = forms.DateTimeField(
        label='Date & time',
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
    )
    location = forms.ModelChoiceField(queryset=Location.objects.all(), label='Venue', empty_label='Select a venue')

    class Meta:
        model = Event
        fields = ['title', 'description', 'date_time', 'duration', 'location',
                  'max_participants', 'registration_open', 'poster']
        labels = {
            'title': 'Event title',
            'duration': 'Duration (hours)',
            'max_participants': 'Seat limit',
            'registration_open': 'Let students register on CommUnity',
            'poster': 'Poster / banner',
        }
        help_texts = {
            'max_participants': 'Leave empty for unlimited seats.',
            'description': 'What is the event about, who is it for, and what will participants gain?',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'duration': forms.NumberInput(attrs={'min': 1, 'max': 72}),
            'max_participants': forms.NumberInput(attrs={'min': 1}),
        }

    def clean_duration(self):
        duration = self.cleaned_data['duration']
        if not 1 <= duration <= 72:
            raise forms.ValidationError('Duration must be between 1 and 72 hours.')
        return duration

    def clean(self):
        cleaned = super().clean()
        date_time, duration, location = cleaned.get('date_time'), cleaned.get('duration'), cleaned.get('location')
        if date_time and duration and location:
            for error in slot_errors(date_time, duration, location, exclude_id=self.instance.pk):
                self.add_error(None, error)
        return cleaned


class EventReportForm(forms.Form):
    organizer = forms.CharField(max_length=255, label='Organised by')
    event_type = forms.CharField(
        max_length=255, label='Event type',
        widget=forms.TextInput(attrs={'list': 'event-types', 'placeholder': 'Workshop, seminar, competition…'}),
    )
    attendees = forms.IntegerField(min_value=0, label='Number of attendees')
    speakers = forms.CharField(
        required=False, label='Speakers / guests',
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'One per line, e.g. Dr. A. Mehta – Data Scientist, TCS'}),
    )
    agenda = forms.CharField(
        label='Agenda & proceedings',
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'What happened, in order'}),
    )
    highlights = forms.CharField(required=False, label='Highlights', widget=forms.Textarea(attrs={'rows': 3}))
    outcomes = forms.CharField(label='Key outcomes', widget=forms.Textarea(attrs={'rows': 3}))
    feedback = forms.CharField(required=False, label='Participant feedback', widget=forms.Textarea(attrs={'rows': 3}))
    media_links = forms.CharField(
        required=False, label='Photo / video links',
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Google Drive, Instagram, YouTube…'}),
    )


class ReportEditForm(forms.Form):
    report_content = forms.CharField(
        label='Report',
        widget=forms.Textarea(attrs={'rows': 26, 'class': 'mono'}),
        help_text='Markdown: "## Heading", "- bullet", **bold**. The PDF is rebuilt when you save.',
    )
