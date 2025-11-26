from django import forms
from ..models import Contest


class ContestForm(forms.ModelForm):
    class Meta:
        model = Contest
        fields = [
            "courses",
            "title",
            "description",
            "source",
            "start_time",
            "duration_minutes",
            "is_published",
            "problems",
        ]

    def save(self, commit=True, created_by=None):
        contest = super().save(commit=False)
        if created_by is not None:
            contest.created_by = created_by
        elif contest.created_by_id is None and commit:
            raise ValueError("created_by is required to save contest")
        if commit:
            contest.save()
            self.save_m2m()
        return contest
