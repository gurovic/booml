from rest_framework import serializers
from .models import Notebook


class NotebookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notebook
        fields = ["id", "title", "content", "owner", "created_at"]
        read_only_fields = ["id", "owner", "created_at"]
