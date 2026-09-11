from django import forms

from faculty.models import Faculty

from .models import Associations


class FacultyChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        name = obj.id.display_name
        return f"{name} ({obj.department})" if obj.department else name


class AssociationForm(forms.ModelForm):
    faculty_incharge = FacultyChoiceField(
        queryset=Faculty.objects.select_related('id__id'),
        label='Faculty in-charge',
        empty_label='Select a faculty member',
        help_text='They will review this request and every event you submit.',
    )

    class Meta:
        model = Associations
        fields = ['name', 'type', 'category', 'description', 'faculty_incharge', 'image']
        labels = {'type': 'This is a', 'image': 'Cover image'}
        widgets = {'description': forms.Textarea(attrs={'rows': 5})}
        help_texts = {'description': 'Your mission, what members do, and how often you meet.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].choices = [('clubs', 'Club'), ('committees', 'Committee')]
        self.fields['category'].choices = [
            (value, 'Uncategorised' if value == 'None' else label) for value, label in Associations.CATEGORY
        ]
