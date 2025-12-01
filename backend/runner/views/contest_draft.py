from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from ..models import Course, CourseParticipant
from ..forms.contest_draft import ContestForm

@login_required
def create_contest(request, course_id):
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    course = get_object_or_404(Course, pk=course_id)
    is_teacher = course.participants.filter(
        user=request.user,
        role=CourseParticipant.Role.TEACHER,
    ).exists()
    if not is_teacher:
        return JsonResponse({"detail": "Only teachers can create contests for this course"}, status=403)

    form = ContestForm(request.POST, course=course)
    if form.is_valid():
        contest = form.save(created_by=request.user, course=course)
        return JsonResponse(
            {
                "id": contest.id,
                "title": contest.title,
                "course": contest.course_id,
                "is_published": contest.is_published,
                "status": contest.status,
            },
            status=201,
        )

    return JsonResponse({"errors": form.errors}, status=400)

@login_required
def contest_success(request):
    return JsonResponse({"detail": "success"})
