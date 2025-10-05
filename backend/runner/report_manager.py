import time
from typing import Dict, List
from django.utils import timezone
from .models import CheckReport, CheckMetrics, CheckError


class ReportManager:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self._results = []
        self.report = None

    def start_timer(self):
        """Запускает таймер выполнения проверок"""
        self.start_time = time.time()

    def stop_timer(self):
        """Останавливает таймер выполнения проверок"""
        self.end_time = time.time()

    def add_result(self, check_name: str, passed: bool, error_info: Dict = None):
        """Добавляет результат проверки"""
        self._results.append({
            "check_name": check_name,
            "passed": passed,
            "error_info": error_info
        })

    def get_execution_time(self) -> float:
        """Возвращает время выполнения"""
        return self.end_time - self.start_time if self.end_time else 0

    def get_summary(self) -> Dict:
        """Возвращает сводку по результатам проверок"""
        total = len(self._results)
        passed = sum(1 for r in self._results if r["passed"])
        failed = total - passed
        success_rate = (passed / total) * 100 if total > 0 else 0

        return {
            'total_checks': total,
            'passed_checks': passed,
            'failed_checks': failed,
            'success_rate': success_rate
        }

    def get_errors(self) -> List[Dict]:
        """Возвращает список ошибок"""
        return [r["error_info"] for r in self._results if not r["passed"] and r["error_info"]]

    def _calculate_overall_status(self, metrics_summary: Dict) -> str:
        """Определяет общий статус отчёта"""
        if metrics_summary['failed_checks'] == 0:
            return 'success'
        elif metrics_summary['failed_checks'] / metrics_summary['total_checks'] > 0.5:
            return 'critical_failure'
        else:
            return 'partial_failure'

    def create_report(self, system_version='1.0.0', context=None) -> int:
        """Создаёт отчёт в базе данных и возвращает его ID"""
        metrics_summary = self.get_summary()

        # Создаём основной отчёт
        self.report = CheckReport.objects.create(
            status=self._calculate_overall_status(metrics_summary),
            execution_time=self.get_execution_time(),
            system_version=system_version,
            context=context or {}
        )

        # Добавляем метрики
        CheckMetrics.objects.create(
            report=self.report,
            total_checks=metrics_summary['total_checks'],
            passed_checks=metrics_summary['passed_checks'],
            failed_checks=metrics_summary['failed_checks'],
            success_rate=metrics_summary['success_rate']
        )

        # Добавляем ошибки
        for error in self.get_errors():
            CheckError.objects.create(
                report=self.report,
                check_name=error['check_name'],
                message=error['message'],
                severity=error.get('severity', 'medium'),
                details=error.get('details', {})
            )

        return self.report.id