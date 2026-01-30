from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import Problem
from ..serializers import ProblemListSerializer, ProblemCreateSerializer


class PolygonProblemListView(generics.ListAPIView):
    """
    GET /api/polygon/problems/
    Returns list of problems created by the current user
    """
    serializer_class = ProblemListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Problem.objects.filter(author=self.request.user).order_by('-id')


class PolygonProblemCreateView(generics.CreateAPIView):
    """
    POST /api/polygon/problems/
    Creates a new problem
    """
    serializer_class = ProblemCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, is_published=False)
