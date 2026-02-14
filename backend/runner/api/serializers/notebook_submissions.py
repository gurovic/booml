from rest_framework import serializers
from django.contrib.auth import get_user_model

from ...models.notebook_submission import NotebookSubmission
from ...models.contest import Contest
from ...models.notebook import Notebook

User = get_user_model()


class NotebookSubmissionCreateSerializer(serializers.ModelSerializer):
    contest_id = serializers.IntegerField(write_only=True)
    notebook_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = NotebookSubmission
        fields = ["id", "contest_id", "notebook_id", "submitted_at", "status", "total_score"]
        read_only_fields = ["id", "submitted_at", "status", "total_score"]
    
    def validate(self, data):
        contest_id = data.get("contest_id")
        notebook_id = data.get("notebook_id")
        request = self.context.get("request")
        user = request.user
        
        # Validate contest exists and is notebook type
        try:
            contest = Contest.objects.get(pk=contest_id)
        except Contest.DoesNotExist:
            raise serializers.ValidationError({"contest_id": "Contest not found"})
        
        if contest.contest_type != Contest.ContestType.NOTEBOOK:
            raise serializers.ValidationError(
                {"contest_id": "Contest is not a notebook-based contest"}
            )
        
        # Validate notebook exists and belongs to user
        try:
            notebook = Notebook.objects.get(pk=notebook_id)
        except Notebook.DoesNotExist:
            raise serializers.ValidationError({"notebook_id": "Notebook not found"})
        
        if notebook.owner != user:
            raise serializers.ValidationError(
                {"notebook_id": "You can only submit your own notebooks"}
            )
        
        # Check if notebook has task cells
        if not notebook.cells.filter(is_task_cell=True).exists():
            raise serializers.ValidationError(
                {"notebook_id": "Notebook has no task cells to check"}
            )
        
        data["contest"] = contest
        data["notebook"] = notebook
        return data
    
    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        
        contest = validated_data.pop("contest")
        notebook = validated_data.pop("notebook")
        validated_data.pop("contest_id", None)
        validated_data.pop("notebook_id", None)
        
        notebook_submission = NotebookSubmission.objects.create(
            user=user,
            contest=contest,
            notebook=notebook,
            **validated_data
        )
        return notebook_submission


class NotebookSubmissionReadSerializer(serializers.ModelSerializer):
    contest_id = serializers.IntegerField(source="contest.id", read_only=True)
    contest_title = serializers.CharField(source="contest.title", read_only=True)
    notebook_id = serializers.IntegerField(source="notebook.id", read_only=True)
    notebook_title = serializers.CharField(source="notebook.title", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    
    class Meta:
        model = NotebookSubmission
        fields = [
            "id",
            "user",
            "username",
            "contest_id",
            "contest_title",
            "notebook_id",
            "notebook_title",
            "submitted_at",
            "status",
            "metrics",
            "total_score",
        ]
        read_only_fields = fields
