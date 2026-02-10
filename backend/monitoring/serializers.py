from rest_framework import serializers


class SystemMetricsSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    cpu = serializers.DictField(child=serializers.FloatField())
    memory = serializers.DictField(child=serializers.IntegerField())
    disk = serializers.DictField(child=serializers.IntegerField())


class TaskStatisticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    running = serializers.IntegerField()
    accepted = serializers.IntegerField()
    failed = serializers.IntegerField()


class HistoricalStatisticsSerializer(serializers.Serializer):
    daily = TaskStatisticsSerializer()
    weekly = TaskStatisticsSerializer()
    monthly = TaskStatisticsSerializer()