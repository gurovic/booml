from rest_framework import generics, permissions
from ..models import Notebook
from ..serializers import NotebookSerializer

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user
class NotebookCreateView(generics.CreateAPIView):
    serializer_class = NotebookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
class NotebookDetailView(generics.RetrieveAPIView):
    queryset = Notebook.objects.all()
    serializer_class = NotebookSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]