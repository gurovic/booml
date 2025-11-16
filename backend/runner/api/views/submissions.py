from django.db import transaction
from rest_framework import generics, permissions, parsers, status
from rest_framework.response import Response

from ...models.submission import Submission
from ..serializers import SubmissionCreateSerializer, SubmissionReadSerializer

from ...services import validation_service
from ...services import enqueue_submission_for_evaluation


def build_descriptor_from_problem(problem) -> dict:
    """
    Snapshot a descriptor object into a plain dict that can be safely passed
    to validation services (and serialized later if needed).
    """
    descriptor = getattr(problem, "descriptor", None)
    if not descriptor:
        return {}

    output_schema = list(getattr(descriptor, "output_columns", []) or [])
    if not output_schema:
        # Fallback to id + target columns to keep validation usable.
        if descriptor.id_column:
            output_schema.append(descriptor.id_column)
        if descriptor.target_column and descriptor.target_column not in output_schema:
            output_schema.append(descriptor.target_column)

    return {
        "id_column": descriptor.id_column,
        "target_column": descriptor.target_column,
        "target_type": descriptor.target_type,
        "check_order": descriptor.check_order,
        "output_schema": output_schema,
    }


class SubmissionCreateView(generics.CreateAPIView):
    """
    POST /api/submissions/
    multipart/form-data: { problem_id, file: <csv> }
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
        problem = submission.problem
        descriptor = build_descriptor_from_problem(problem)
        report = validation_service.run_pre_validation(submission, descriptor=descriptor)

        # 3) Ветвление по результату
        data = SubmissionReadSerializer(submission, context={"request": request}).data
        report_valid = getattr(report, "is_valid", None)
        if report_valid is None:
            if hasattr(report, "valid"):
                report_valid = report.valid
            else:
                report_valid = getattr(report, "status", "") != "failed"

        if report_valid:
            self._enqueue_submission(submission.id)
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

    def _enqueue_submission(self, submission_id: int) -> None:
        enqueue_submission_for_evaluation(submission_id)


class MySubmissionsListView(generics.ListAPIView):
    """
    GET /api/submissions/mine/ — список моих сабмитов.
    """
    serializer_class = SubmissionReadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Submission.objects.filter(user=self.request.user).order_by("-submitted_at")
