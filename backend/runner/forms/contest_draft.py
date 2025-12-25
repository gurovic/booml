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
            "scoring",
            "registration_type",
            "is_rated",
            "problems",
        ]

    def save(self, commit=True, created_by=None, course=None):
        contest = super().save(commit=False)
        course_value = course or self.course
        if course_value is not None:
            contest.course = course_value
        elif contest.course_id is None:
            raise ValueError("course is required to save contest")
        if created_by is not None:
            contest.created_by = created_by
        elif contest.created_by_id is None and commit:
            raise ValueError("created_by is required to save contest")
        if commit:
            contest.save()
            self.save_m2m()
        return contest
