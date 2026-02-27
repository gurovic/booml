from django.conf import settings
from django.db import transaction
from rest_framework import generics, permissions, parsers, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from ...models.submission import Submission
from ...models.problem import Problem
from ...models.contest import Contest
from ...models.course import CourseParticipant
from ..serializers import SubmissionCreateSerializer, SubmissionReadSerializer, SubmissionDetailSerializer

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


def _contest_student_ids(contest: Contest) -> set[int]:
    teacher_ids = set(
        CourseParticipant.objects.filter(
            course=contest.course,
            role=CourseParticipant.Role.TEACHER,
        ).values_list("user_id", flat=True)
    )
    if contest.course and contest.course.owner_id:
        teacher_ids.add(contest.course.owner_id)

    if contest.access_type == Contest.AccessType.PRIVATE:
        candidate_ids = set(contest.allowed_participants.values_list("id", flat=True))
    else:
        candidate_ids = set(
            CourseParticipant.objects.filter(
                course=contest.course,
                role=CourseParticipant.Role.STUDENT,
            ).values_list("user_id", flat=True)
        )
        candidate_ids |= set(contest.allowed_participants.values_list("id", flat=True))

    return {uid for uid in candidate_ids if uid and uid not in teacher_ids}


class SubmissionCreateView(generics.CreateAPIView):
    """
    POST /api/submissions/
    multipart/form-data / JSON: { problem_id, file: <csv> } или { problem_id, raw_text: "<csv>" }
    1) создаём Submission (pending)
    2) синхронно запускаем pre-validation
    3) при успехе ставим в очередь основную обработку, отвечаем 201
       при провале возвращаем 400 (submission.status уже 'validation_error')
    """
    queryset = Submission.objects.all()
    serializer_class = SubmissionCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

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


class SubmissionDetailView(generics.RetrieveAPIView):
    """
    GET /api/submissions/<id>/ — детали посылки с преvalidation отчётом.
    """
    serializer_class = SubmissionDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        base_qs = Submission.objects.select_related("problem", "prevalidation")
        contest_id_raw = self.request.query_params.get("contest_id")
        if contest_id_raw in (None, ""):
            return base_qs.filter(user=self.request.user)

        try:
            contest_id = int(contest_id_raw)
        except (TypeError, ValueError):
            return Submission.objects.none()
        if contest_id <= 0:
            return Submission.objects.none()

        contest = (
            Contest.objects.select_related("course")
            .prefetch_related("allowed_participants")
            .filter(pk=contest_id)
            .first()
        )
        if contest is None or not contest.is_user_manager(self.request.user):
            return Submission.objects.none()

        problem_ids = set(contest.problems.filter(is_published=True).values_list("id", flat=True))
        student_ids = _contest_student_ids(contest)
        if not problem_ids or not student_ids:
            return Submission.objects.none()

        return base_qs.filter(problem_id__in=problem_ids, user_id__in=student_ids)


class SubmissionsPagination(PageNumberPagination):
    """
    Pagination for submissions list - 10 items per page (fixed).
    """
    page_size = 10


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
