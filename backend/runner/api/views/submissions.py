from django.db import transaction
from rest_framework import generics, permissions, parsers, status
from rest_framework.response import Response

from ...models.submission import Submission
from ..serializers import SubmissionCreateSerializer, SubmissionReadSerializer

from ...services.validation_service import run_pre_validation
from ...problems import enqueue_submission_for_evaluation

def build_descriptor_from_task(task) -> dict:
    """
    Собирает дескриптор для validation_service из Task.
    Сейчас Task не хранит схему — возвращаем пустой dict (это допустимо).
    Если добавишь поля (output_schema/target_*), расширь логику ниже.
    """
    descriptor = {}
    # Пример на будущее:
    # if hasattr(task, "output_schema"):
    #     descriptor["output_schema"] = task.output_schema
    # if hasattr(task, "target_column"):
    #     descriptor["target_column"] = task.target_column
    # if hasattr(task, "target_type"):
    #     descriptor["target_type"] = task.target_type
    return descriptor


class SubmissionCreateView(generics.CreateAPIView):
    """
    POST /api/submissions/
    multipart/form-data: { task_id, file: <csv> }
    1) создаём Submission (pending)
    2) синхронно запускаем pre-validation
    3) при успехе ставим в очередь основную обработку, отвечаем 201
       при провале возвращаем 400 (submission.status уже 'failed')
    """
    queryset = Submission.objects.all()
    serializer_class = SubmissionCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 1) Сохраняем сабмит и файл
        with transaction.atomic():
            submission: Submission = serializer.save()

        # 2) Пре-валидация
        task = submission.task
        descriptor = build_descriptor_from_task(task)
        report = run_pre_validation(submission, descriptor=descriptor)

        # 3) Ветвление по результату
        data = SubmissionReadSerializer(submission, context={"request": request}).data
        if report.valid:
            enqueue_submission_for_evaluation.delay(submission.id)
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            return Response(data, status=status.HTTP_400_BAD_REQUEST)


class MySubmissionsListView(generics.ListAPIView):
    """
    GET /api/submissions/mine/ — список моих сабмитов.
    """
    serializer_class = SubmissionReadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Submission.objects.filter(user=self.request.user).order_by("-submitted_at")

