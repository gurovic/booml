from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.db.models import Prefetch

from ..models import Contest, Course, Problem, Section
from ..services.section_service import build_section_tree, ensure_root_sections


def catalog_tree(request):
    """Show the full hierarchy: sections -> courses -> contests -> problems."""
    ensure_root_sections(request.user if request.user.is_authenticated else None)
    tree = build_section_tree()
    return render(request, "runner/catalog_tree.html", {"tree": tree})


def catalog_section(request, section_id: int):
    """Display a section with its subsections and courses."""
    course_qs = Course.objects.select_related("owner", "section").prefetch_related(
        Prefetch(
            "contests",
            queryset=Contest.objects.order_by("title").prefetch_related("problems"),
        )
    )
    section = get_object_or_404(
        Section.objects.select_related("parent", "owner").prefetch_related(
            Prefetch("children", queryset=Section.objects.order_by("title")),
            Prefetch("courses", queryset=course_qs.order_by("title")),
        ),
        pk=section_id,
    )

    ancestors = []
    current = section.parent
    while current:
        ancestors.append(current)
        current = current.parent
    ancestors.reverse()

    return render(
        request,
        "runner/catalog_section.html",
        {
            "section": section,
            "ancestors": ancestors,
        },
    )


def catalog_course(request, course_id: int):
    """Display a course with its contests."""
    course = get_object_or_404(
        Course.objects.select_related("section", "owner").prefetch_related(
            Prefetch(
                "contests",
                queryset=Contest.objects.order_by("title").prefetch_related("problems"),
            )
        ),
        pk=course_id,
    )

    return render(
        request,
        "runner/catalog_course.html",
        {
            "course": course,
            "contests": list(course.contests.all()),
        },
    )


def catalog_contest(request, contest_id: int):
    """Display contest details with the list of problems."""
    contest = get_object_or_404(
        Contest.objects.select_related("course", "created_by").prefetch_related("problems"),
        pk=contest_id,
    )

    if not contest.is_visible_to(request.user):
        return HttpResponseForbidden("Недостаточно прав для просмотра контеста.")

    problems = list(contest.problems.all())
    return render(
        request,
        "runner/catalog_contest.html",
        {
            "contest": contest,
            "problems": problems,
        },
    )
