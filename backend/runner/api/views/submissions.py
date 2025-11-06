from django.db import transaction
from rest_framework import generics, permissions, parsers, status
from rest_framework.response import Response

from ...models.submission import Submission
from ..serializers import SubmissionCreateSerializer, SubmissionReadSerializer

from ...services.validation_service import run_prevalidation
from ...problems import enqueue_submission_for_evaluation


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
        descriptor = submission.problem.descriptor
        report = run_prevalidation(submission)

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

