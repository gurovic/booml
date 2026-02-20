from django import forms
from django.db.models import Max
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
            "allow_upsolving",
            "is_published",
            "status",
            "scoring",
            "registration_type",
            "is_rated",
            "problems",
        ]

    def clean(self):
        cleaned = super().clean()
        start_time = cleaned.get("start_time")
        duration = cleaned.get("duration_minutes")
        allow_upsolving = bool(cleaned.get("allow_upsolving"))

        if duration and not start_time:
            self.add_error("start_time", "Укажите время начала для контеста с дедлайном.")

        if allow_upsolving and (not start_time or not duration):
            self.add_error(
                "allow_upsolving",
                "Дорешка доступна только для контеста с ограничением по времени.",
            )

        return cleaned

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

        # Append new contests to the end of the course list by default.
        if contest.pk is None and course_value is not None:
            max_pos = (
                Contest.objects.filter(course=course_value)
                .aggregate(Max("position"))
                .get("position__max")
            )
            contest.position = (max_pos + 1) if max_pos is not None else 0
        if commit:
            contest.save()
            self.save_m2m()
        return contest
