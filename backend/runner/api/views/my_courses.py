from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from runner.models.course import Course, CourseParticipant

@login_required
def my_courses(request):
    """
    Представление для отображения курсов, в которых участвует текущий пользователь.
    """
    # Получаем ID курсов, где пользователь является участником
    participant_records = CourseParticipant.objects.filter(user=request.user)
    course_ids = participant_records.values_list('course_id', flat=True)
    
    # Получаем сами курсы
    courses = Course.objects.filter(id__in=course_ids)
    
    return render(request, 'runner/my_courses.html', {'courses': courses})
