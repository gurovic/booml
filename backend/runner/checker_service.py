import os
from django.conf import settings
from .report_manager import ReportManager
from .report_serializer import ReportJSONSerializer


class CheckerService:
    def __init__(self):
        self.report_manager = ReportManager()
        self.checks = []

    def register_check(self, check_name: str, check_function):
        """Регистрирует проверку для выполнения"""
        self.checks.append((check_name, check_function))

    def run_checks(self, system_version='1.0.0', context=None):
        """Запускает все зарегистрированные проверки и генерирует отчёт"""
        print("Starting checks...")
        self.report_manager.start_timer()

        # Выполняем все проверки
        for check_name, check_func in self.checks:
            try:
                print(f"Running check: {check_name}")
                result = check_func()
                self.report_manager.add_result(
                    check_name=check_name,
                    passed=result,
                    error_info=None if result else {
                        "check_name": check_name,
                        "message": f"Check {check_name} failed",
                        "severity": "medium",
                        "details": {"error_code": "CHECK_FAILED"}
                    }
                )
                print(f"Check {check_name}: {'PASSED' if result else 'FAILED'}")

            except Exception as e:
                print(f"Check {check_name} ERROR: {str(e)}")
                self.report_manager.add_result(
                    check_name=check_name,
                    passed=False,
                    error_info={
                        "check_name": check_name,
                        "message": str(e),
                        "severity": "high",
                        "details": {"exception_type": type(e).__name__}
                    }
                )

        self.report_manager.stop_timer()

        # Создаём отчёт в базе данных
        report_id = self.report_manager.create_report(
            system_version=system_version,
            context=context or {}
        )

        reports_dir = os.path.join(settings.BASE_DIR, 'reports')
        os.makedirs(reports_dir, exist_ok=True)

        file_path = os.path.join(reports_dir, f'report_{report_id}.json')
        ReportJSONSerializer.save_report_to_file(report_id, file_path)

        print(f"Report generated successfully!")
        print(f"Database ID: {report_id}")
        print(f"JSON file: {file_path}")

        return report_id


checker_service = CheckerService()