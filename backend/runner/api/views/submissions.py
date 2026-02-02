from django.conf import settings
from django.db import transaction
from rest_framework import generics, permissions, parsers, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from ...models.submission import Submission
from ...models.problem import Problem
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
        try:
            report = validation_service.run_pre_validation(submission, descriptor=descriptor)
        except Exception as exc:  # pragma: no cover - defensive
            submission.status = Submission.STATUS_FAILED
            submission.save(update_fields=["status"])
            payload = {
                "message": "Не удалось выполнить предварительную проверку файла.",
                "submission": SubmissionReadSerializer(
                    submission, context={"request": request}
                ).data,
            }
            if settings.DEBUG:
                payload["detail"] = str(exc)
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

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

        errors = getattr(report, "errors", None)
        details = None
        if errors:
            if isinstance(errors, list) and errors:
                details = errors[0]
            else:
                details = str(errors)
        payload = {
            "message": "Файл не прошёл предварительную проверку.",
            "detail": details,
            "errors": errors,
            "submission": data,
        }
        if payload["detail"] is None:
            payload.pop("detail")
        if payload["errors"] in (None, []):
            payload.pop("errors")
        return Response(payload, status=status.HTTP_400_BAD_REQUEST)

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


class SubmissionsPagination(PageNumberPagination):
    """
    Pagination for submissions list - 10 items per page.
    """
    page_size = 10
    max_page_size = 100


class ProblemSubmissionsListView(generics.ListAPIView):
    """
    GET /api/submissions/problem/<problem_id>/ — список посылок пользователя по конкретной задаче.
    """
    serializer_class = SubmissionReadSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SubmissionsPagination

    def get_queryset(self):
        problem_id = self.kwargs.get('problem_id')
        try:
            problem = Problem.objects.get(pk=problem_id)
        except Problem.DoesNotExist:
            return Submission.objects.none()
        
        return Submission.objects.filter(
            user=self.request.user,
            problem=problem
        ).order_by("-submitted_at")
