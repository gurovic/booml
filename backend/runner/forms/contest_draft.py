from django import forms
from ..models import Contest

class ContestForm(forms.ModelForm):
    class Meta:
        model = Contest
        fields = ['start_time', 'source']
