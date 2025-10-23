import logging
from typing import Dict, Any
from django.core.exceptions import ValidationError
from ..models import Report

logger = logging.getLogger(__name__)


class ReportGenerator:
    def create_report_from_testing_system(self, test_result: Dict[str, Any]) -> Report:
        """
        Создаёт отчёт на основе данных от тестирующей системы

        Args:
            test_result: Словарь с результатами проверки от тестирующей системы
                        Ожидаемые поля: metric, log, errors, file_name, status, test_data

        Returns:
            Report: Созданный объект отчёта
        """
        try:
            # Валидация обязательных полей
            required_fields = ['metric', 'file_name']
            for field in required_fields:
                if field not in test_result:
                    raise ValidationError(f"Отсутствует обязательное поле: {field}")

            report_data = {
                'metric': float(test_result['metric']),
                'log': test_result.get('log', ''),
                'errors': test_result.get('errors', ''),
                'file_name': test_result['file_name'],
                'status': test_result.get('status', 'success'),
                'test_data': test_result.get('test_data')
            }

            report = Report(**report_data)
            report.full_clean()
            report.save()

            logger.info(f"Отчёт для файла {report.file_name} успешно создан (ID: {report.id})")
            return report

        except ValidationError as e:
            logger.error(f"Ошибка валидации при создании отчёта: {e}")
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при создании отчёта: {e}")
            raise