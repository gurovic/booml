from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .checker_service import checker_service
from .models import CheckReport
from .report_serializer import ReportJSONSerializer


@csrf_exempt
def run_checks_view(request):
    """API endpoint для запуска проверок"""
    if request.method == 'POST':
        try:
            context = json.loads(request.body) if request.body else {}
            report_id = checker_service.run_checks(context=context)

            return JsonResponse({
                'status': 'success',
                'report_id': report_id,
                'message': 'Checks completed successfully'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def get_report_json(request, report_id):
    """API endpoint для получения отчёта в JSON формате"""
    try:
        json_data = ReportJSONSerializer.serialize_report(report_id)
        return HttpResponse(json_data, content_type='application/json')
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=404)


def get_reports_list(request):
    """API endpoint для получения списка отчётов"""
    reports = CheckReport.objects.all()[:10]  # Последние 10 отчётов
    reports_data = [
        {
            'id': report.id,
            'timestamp': report.timestamp.isoformat(),
            'status': report.status,
            'execution_time': report.execution_time
        }
        for report in reports
    ]

    return JsonResponse({'reports': reports_data})