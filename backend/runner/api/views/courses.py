from django.db.models import Prefetch
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models.course import Course


def _build_course_tree(courses):
    by_parent = {}
    for course in courses:
        by_parent.setdefault(course.parent_id, []).append(course)

    def build(parent_id):
        nodes = []
        for course in by_parent.get(parent_id, []):
            nodes.append(
                {
                    "id": course.id,
                    "title": course.title,
                    "description": course.description,
                    "children": build(course.id),
                }
            )
        return nodes

    return build(None)


class CourseTreeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        courses = Course.objects.select_related("parent").prefetch_related(
            Prefetch("children", queryset=Course.objects.only("id", "title", "description", "parent"))
        ).all()

        tree = _build_course_tree(list(courses))
        return Response(tree)
