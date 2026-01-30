from rest_framework import serializers

from ...models import Problem


class ProblemListSerializer(serializers.ModelSerializer):
    """Serializer for listing problems in polygon"""
    
    class Meta:
        model = Problem
        fields = ['id', 'title', 'rating', 'is_published', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProblemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating problems in polygon"""
    
    class Meta:
        model = Problem
        fields = ['title', 'rating']
        
    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Название обязательно")
        return value.strip()
