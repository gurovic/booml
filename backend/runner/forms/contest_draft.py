from django import forms
from ..models import Contest


class ContestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.course = kwargs.pop("course", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Contest
        fields = [
            "title",
            "description",
            "source",
            "start_time",
            "duration_minutes",
            "is_published",
            "status",
            "problems",
        ]

    def save(self, commit=True, created_by=None, course=None):
        contest = super().save(commit=False)
        contest.course = course or self.course or contest.course
        if contest.course is None:
            raise ValueError("course is required to save contest")
        if created_by is not None:
            contest.created_by = created_by
        elif contest.created_by_id is None and commit:
            raise ValueError("created_by is required to save contest")
        if commit:
            contest.save()
            self.save_m2m()
        return contest
