import psutil
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from datetime import datetime, timedelta
from runner.models.submission import Submission
from django.contrib.auth.mixins import UserPassesTestMixin
import json
from .serializers import SystemMetricsSerializer, TaskStatisticsSerializer, HistoricalStatisticsSerializer
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


def is_admin(user):
    return user.is_staff


class SystemMetricsView(APIView):
    """
    View to provide system metrics like CPU, memory, disk usage
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()
        disk_usage = psutil.disk_usage('/')
        
        # Format the data
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu': {
                'percent': cpu_percent
            },
            'memory': {
                'total': memory_info.total,
                'available': memory_info.available,
                'percent': memory_info.percent,
                'used': memory_info.used
            },
            'disk': {
                'total': disk_usage.total,
                'used': disk_usage.used,
                'free': disk_usage.free,
                'percent': (disk_usage.used / disk_usage.total) * 100
            }
        }
        
        serializer = SystemMetricsSerializer(data=metrics)
        if serializer.is_valid():
            return Response(serializer.validated_data)
        else:
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class TaskStatisticsView(APIView):
    """
    View to provide task statistics
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Get submission statistics
        total_submissions = Submission.objects.count()
        pending_submissions = Submission.objects.filter(status='pending').count()
        running_submissions = Submission.objects.filter(status='running').count()
        accepted_submissions = Submission.objects.filter(status='accepted').count()
        failed_submissions = Submission.objects.filter(status='failed').count()
        
        stats = {
            'total': total_submissions,
            'pending': pending_submissions,
            'running': running_submissions,
            'accepted': accepted_submissions,
            'failed': failed_submissions
        }
        
        serializer = TaskStatisticsSerializer(data=stats)
        if serializer.is_valid():
            return Response(serializer.validated_data)
        else:
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class HistoricalStatisticsView(APIView):
    """
    View to provide historical statistics
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Calculate statistics for different periods
        now = datetime.now()
        
        # Last 24 hours
        day_start = now - timedelta(days=1)
        submissions_last_day = Submission.objects.filter(
            submitted_at__gte=day_start
        ).count()
        
        # Last 7 days
        week_start = now - timedelta(weeks=1)
        submissions_last_week = Submission.objects.filter(
            submitted_at__gte=week_start
        ).count()
        
        # Last 30 days
        month_start = now - timedelta(days=30)
        submissions_last_month = Submission.objects.filter(
            submitted_at__gte=month_start
        ).count()
        
        # Group by status for each period
        daily_stats = {
            'total': submissions_last_day,
            'pending': Submission.objects.filter(
                submitted_at__gte=day_start,
                status='pending'
            ).count(),
            'running': Submission.objects.filter(
                submitted_at__gte=day_start,
                status='running'
            ).count(),
            'accepted': Submission.objects.filter(
                submitted_at__gte=day_start,
                status='accepted'
            ).count(),
            'failed': Submission.objects.filter(
                submitted_at__gte=day_start,
                status='failed'
            ).count(),
        }
        
        weekly_stats = {
            'total': submissions_last_week,
            'pending': Submission.objects.filter(
                submitted_at__gte=week_start,
                status='pending'
            ).count(),
            'running': Submission.objects.filter(
                submitted_at__gte=week_start,
                status='running'
            ).count(),
            'accepted': Submission.objects.filter(
                submitted_at__gte=week_start,
                status='accepted'
            ).count(),
            'failed': Submission.objects.filter(
                submitted_at__gte=week_start,
                status='failed'
            ).count(),
        }
        
        monthly_stats = {
            'total': submissions_last_month,
            'pending': Submission.objects.filter(
                submitted_at__gte=month_start,
                status='pending'
            ).count(),
            'running': Submission.objects.filter(
                submitted_at__gte=month_start,
                status='running'
            ).count(),
            'accepted': Submission.objects.filter(
                submitted_at__gte=month_start,
                status='accepted'
            ).count(),
            'failed': Submission.objects.filter(
                submitted_at__gte=month_start,
                status='failed'
            ).count(),
        }
        
        stats = {
            'daily': daily_stats,
            'weekly': weekly_stats,
            'monthly': monthly_stats
        }
        
        serializer = HistoricalStatisticsSerializer(data=stats)
        if serializer.is_valid():
            return Response(serializer.validated_data)
        else:
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)