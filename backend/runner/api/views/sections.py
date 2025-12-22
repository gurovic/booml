from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response

from ...models import Section
from ..permissions import IsTeacher
from ..serializers.sections import (
    SectionCreateSerializer,
    SectionReadSerializer,
    SectionUpdateSerializer,
)


class SectionCreateView(generics.CreateAPIView):
    """
    Create a section. Only teachers can create sections.
    """

    serializer_class = SectionCreateSerializer
    permission_classes = [IsTeacher]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        section = serializer.save()
        data = SectionReadSerializer(section, context={"request": request}).data
        return Response(data, status=201)


class SectionUpdateView(generics.UpdateAPIView):
    """
    Update a section. Only teachers can update sections.
    """

    serializer_class = SectionUpdateSerializer
    permission_classes = [IsTeacher]
    lookup_url_kwarg = "section_id"

    def get_object(self):
        section_id = self.kwargs.get(self.lookup_url_kwarg)
        return get_object_or_404(Section, pk=section_id)

    def update(self, request, *args, **kwargs):
        section = self.get_object()
        serializer = self.get_serializer(section, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        section = serializer.save()
        data = SectionReadSerializer(section, context={"request": request}).data
        return Response(data)


class SectionDeleteView(generics.DestroyAPIView):
    """
    Delete a section. Only teachers can delete sections.
    """

    permission_classes = [IsTeacher]
    lookup_url_kwarg = "section_id"

    def get_object(self):
        section_id = self.kwargs.get(self.lookup_url_kwarg)
        return get_object_or_404(Section, pk=section_id)


class SectionListView(generics.ListAPIView):
    """
    List all root sections (sections without a parent).
    """

    serializer_class = SectionReadSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self):
        return Section.objects.filter(parent__isnull=True).order_by("order", "-created_at")


class SectionDetailView(generics.RetrieveAPIView):
    """
    Get details of a section including its children or courses.
    """

    serializer_class = SectionReadSerializer
    permission_classes = [IsTeacher]
    lookup_url_kwarg = "section_id"

    def get_object(self):
        section_id = self.kwargs.get(self.lookup_url_kwarg)
        return get_object_or_404(Section, pk=section_id)
