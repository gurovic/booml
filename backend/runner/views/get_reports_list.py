from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .report_service import ReportGenerator
from .serializers import ReportSerializer
import logging
from .models import Report
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from .models import Task


@api_view(['GET'])
def get_reports_list(request):
    """
    Эндпоинт для получения списка всех отчётов
    """
    reports = Report.objects.all()
    serializer = ReportSerializer(reports, many=True)
    return Response(serializer.data)