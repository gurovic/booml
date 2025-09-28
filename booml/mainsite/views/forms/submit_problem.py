from django import forms
from mainsite.models.submission import Submission
from mainsite.models.problem import Problem


class SubmissionForm(forms.ModelForm):
    problem_id = forms.IntegerField(widget=forms.HiddenInput())

    class Meta:
        model = Submission
        fields = ["file"]

    def save(self, commit=True):
        
        instance = super().save(commit=False)
        problem_id = self.cleaned_data['problem_id']
        print(Problem.objects.all()[0].id)
        instance.problem = Problem.objects.get(id=int(problem_id))

        if commit:
            instance.save()
        return instance
