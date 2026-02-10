import psutil
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from datetime import datetime, timedelta
import random
from runner.models.submission import Submission
from django.contrib.auth.mixins import UserPassesTestMixin
import json
from .serializers import SystemMetricsSerializer, TaskStatisticsSerializer, HistoricalStatisticsSerializer
from .models import SystemMetric
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status



def is_admin(user):
    return user.is_staff


class SystemMetricsView(APIView):
    """
    View to provide system metrics like CPU, memory, disk usage
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get system metrics
        # В Docker-контейнере psutil может возвращать информацию только о контейнере
        # Для получения информации о хост-системе используем специальные методы
        
        # CPU использование
        try:
            # Попробуем получить информацию о CPU из смонтированной директории
            cpu_percent = round(psutil.cpu_percent(interval=1))  # Округляем до целого числа
        except:
            cpu_percent = 0

        # Память
        memory_total = memory_available = memory_percent = memory_used = 0
        try:
            # Сначала пробуем получить информацию из смонтированной директории /host/proc
            import os
            if os.path.exists('/host/proc/meminfo'):
                with open('/host/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    for line in meminfo.split('\n'):
                        parts = line.split()
                        if line.startswith('MemTotal:') and len(parts) >= 2:
                            try:
                                memory_total = int(parts[1]) * 1024  # Convert to bytes
                            except ValueError:
                                pass  # Skip if conversion fails
                        elif line.startswith('MemAvailable:') and len(parts) >= 2:
                            try:
                                memory_available = int(parts[1]) * 1024  # Convert to bytes
                            except ValueError:
                                pass  # Skip if conversion fails
                    if memory_total > 0 and memory_available >= 0:
                        memory_used = memory_total - memory_available
                        memory_percent = round((memory_used / memory_total) * 100)  # Целое число без десятичных знаков
            else:
                # Если смонтированной директории нет, используем стандартный psutil
                memory_info = psutil.virtual_memory()
                memory_total = memory_info.total
                memory_available = memory_info.available
                memory_percent = memory_info.percent
                memory_used = memory_info.used
        except Exception:
            # Если ничего не работает, используем стандартный psutil
            try:
                memory_info = psutil.virtual_memory()
                memory_total = memory_info.total
                memory_available = memory_info.available
                memory_percent = memory_info.percent
                memory_used = memory_info.used
            except:
                memory_total = memory_available = memory_percent = memory_used = 0

        # Диск - используем информацию о директории приложения
        disk_total = disk_used = disk_free = disk_percent = 0
        try:
            # Используем директорию проекта для получения информации о диске
            project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            disk_usage = psutil.disk_usage(project_dir)
            disk_total = disk_usage.total
            disk_used = disk_usage.used
            disk_free = disk_usage.free
            disk_percent = round((disk_used / disk_total) * 100) if disk_total > 0 else 0  # Округляем до целого числа
        except:
            # Если не удалось получить информацию о диске проекта, используем корень файловой системы
            try:
                disk_usage = psutil.disk_usage('/')
                disk_total = disk_usage.total
                disk_used = disk_usage.used
                disk_free = disk_usage.free
                disk_percent = round((disk_used / disk_total) * 100) if disk_total > 0 else 0  # Округляем до целого числа
            except:
                # Если ничего не работает, возвращаем нулевые значения
                disk_total = disk_used = disk_free = disk_percent = 0

        # Сохраняем метрики в базу данных
        try:
            # Проверяем, существует ли таблица, перед тем как записывать
            from django.db import connection
            table_exists = False
            
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
                    ['system_metrics']
                )
                table_exists = cursor.fetchone()[0]
            
            # Если таблица существует, сохраняем данные
            if table_exists:
                SystemMetric.objects.create(
                    cpu_percent=cpu_percent,
                    memory_percent=memory_percent,
                    disk_percent=disk_percent
                )
        except Exception as e:
            # Если таблица не существует или другая ошибка, продолжаем работу
            # без сохранения в базу данных
            pass

        # Format the data
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu': {
                'percent': cpu_percent
            },
            'memory': {
                'total': memory_total,
                'available': memory_available,
                'percent': memory_percent,
                'used': memory_used
            },
            'disk': {
                'total': disk_total,
                'used': disk_used,
                'free': disk_free,
                'percent': disk_percent
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
    permission_classes = [IsAuthenticated]
    
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
    permission_classes = [IsAuthenticated]
    
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


class HistoricalMetricsView(APIView):
    """
    View to provide historical system metrics for charts
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Пропускаем проверку существования таблицы, так как она существует
            
            # Получаем последние 50 записей из базы данных
            metrics = SystemMetric.objects.all().order_by('-timestamp')[:50]
            
            # Преобразуем данные для графиков
            timestamps = []
            cpu_history = []
            memory_history = []
            disk_history = []
            
            for metric in metrics:
                timestamps.append(metric.timestamp.strftime('%H:%M:%S'))  # Форматируем время с секундами для уникальности
                cpu_history.append(round(metric.cpu_percent))
                memory_history.append(round(metric.memory_percent))
                disk_history.append(round(metric.disk_percent))

            # Формируем ответ
            historical_metrics = {
                'timestamps': timestamps,
                'cpu_history': cpu_history,
                'memory_history': memory_history,
                'disk_history': disk_history,
            }

        except Exception as e:
            # В случае ошибки возвращаем пустые данные
            historical_metrics = {
                'timestamps': [],
                'cpu_history': [],
                'memory_history': [],
                'disk_history': [],
            }

        return Response(historical_metrics)
