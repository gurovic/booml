from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import ReportSerializer
from .models import Report

@api_view(['GET'])
def get_reports_list(request):
    """
    Эндпоинт для получения списка всех отчётов
    """
    reports = Report.objects.all()
    serializer = ReportSerializer(reports, many=True)
    return Response(serializer.data)