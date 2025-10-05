import json
from django.core.serializers.json import DjangoJSONEncoder
from .models import CheckReport


class ReportJSONSerializer:
    @staticmethod
    def serialize_report(report_id: int) -> str:
        """Сериализует отчёт в JSON строку"""
        try:
            report = CheckReport.objects.get(id=report_id)
            metrics = report.metrics
            errors = report.errors.all()

            report_data = {
                'timestamp': report.timestamp.isoformat(),
                'status': report.status,
                'metrics': {
                    'total_checks': metrics.total_checks,
                    'passed_checks': metrics.passed_checks,
                    'failed_checks': metrics.failed_checks,
                    'success_rate': round(metrics.success_rate, 2),
                    'execution_time': round(report.execution_time, 2)
                },
                'errors': [
                    {
                        'check_name': error.check_name,
                        'message': error.message,
                        'severity': error.severity,
                        'details': error.details,
                        'timestamp': error.timestamp.isoformat()
                    }
                    for error in errors
                ],
                'context': report.context,
                'system_version': report.system_version
            }

            return json.dumps(report_data, indent=2, ensure_ascii=False, cls=DjangoJSONEncoder)

        except CheckReport.DoesNotExist:
            raise ValueError(f"Report with id {report_id} does not exist")

    @staticmethod
    def save_report_to_file(report_id: int, filepath: str = "report.json") -> str:
        """Сохраняет отчёт в JSON файл"""
        json_data = ReportJSONSerializer.serialize_report(report_id)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json_data)

        return filepath