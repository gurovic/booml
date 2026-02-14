from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from ...models.notebook_submission import NotebookSubmission
from ..serializers.notebook_submissions import (
    NotebookSubmissionCreateSerializer,
    NotebookSubmissionReadSerializer
)
from ...services.notebook_checker import NotebookSubmissionChecker


class NotebookSubmissionCreateView(generics.CreateAPIView):
    """
    POST /api/notebook-submissions/
    {
        "contest_id": <int>,
        "notebook_id": <int>
    }
    
    Creates a notebook submission and queues it for checking.
    """
    queryset = NotebookSubmission.objects.all()
    serializer_class = NotebookSubmissionCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create submission
        with transaction.atomic():
            notebook_submission = serializer.save()
        
        # Check notebook synchronously (can be made async with Celery later)
        checker = NotebookSubmissionChecker()
        try:
            check_result = checker.check_notebook_submission(notebook_submission)
            
            if not check_result.ok:
                notebook_submission.status = NotebookSubmission.STATUS_FAILED
                notebook_submission.save(update_fields=["status"])
                return Response(
                    {
                        "message": "Notebook checking failed",
                        "errors": check_result.errors,
                        "submission": NotebookSubmissionReadSerializer(
                            notebook_submission,
                            context={"request": request}
                        ).data
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Refresh to get updated status and metrics
            notebook_submission.refresh_from_db()
            
            return Response(
                NotebookSubmissionReadSerializer(
                    notebook_submission,
                    context={"request": request}
                ).data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as exc:
            notebook_submission.status = NotebookSubmission.STATUS_FAILED
            notebook_submission.save(update_fields=["status"])
            return Response(
                {
                    "message": "Failed to check notebook submission",
                    "error": str(exc),
                    "submission": NotebookSubmissionReadSerializer(
                        notebook_submission,
                        context={"request": request}
                    ).data
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotebookSubmissionListView(generics.ListAPIView):
    """
    GET /api/notebook-submissions/
    List all notebook submissions for the current user.
    """
    serializer_class = NotebookSubmissionReadSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination
    
    def get_queryset(self):
        return NotebookSubmission.objects.filter(
            user=self.request.user
        ).select_related("contest", "notebook")


class NotebookSubmissionDetailView(generics.RetrieveAPIView):
    """
    GET /api/notebook-submissions/<id>/
    Get details of a specific notebook submission.
    """
    serializer_class = NotebookSubmissionReadSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return NotebookSubmission.objects.filter(
            user=self.request.user
        ).select_related("contest", "notebook")
