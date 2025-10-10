from rest_framework import serializers
from .models import Report

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report  # Указываем, какую модель сериализуем
        fields = ['id', 'metric', 'log', 'errors', 'file_name', 'status', 'submitted_at', 'test_data']
        read_only_fields = ['id', 'submitted_at']  # Эти поля нельзя менять через API