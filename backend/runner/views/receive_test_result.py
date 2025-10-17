from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from ..services.report_service import ReportGenerator
from ..services.serializers import ReportSerializer
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
def receive_test_result(request):
    """
    Эндпоинт для получения результатов проверки от тестирующей системы
    """
    try:
        test_result = request.data

        # Логируем полученные данные для отладки
        logger.info(f"Получены результаты проверки для файла: {test_result.get('file_name')}")

        # Создаём отчёт
        generator = ReportGenerator()
        report = generator.create_report_from_testing_system(test_result)

        # Возвращаем созданный отчёт
        serializer = ReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Ошибка при обработке результатов теста: {str(e)}")
        return Response(
            {'error': f'Ошибка при создании отчёта: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )