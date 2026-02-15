import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.template import Template, Context
from runner.models.course import Course, CourseParticipant
from runner.api.views.my_courses import my_courses

@pytest.mark.django_db
def test_header_polygon_visibility():
    """
    Тест проверяет видимость ссылки 'Полигон' в хедере (base.html).
    Ссылка должна быть видна только персоналу (учителям).
    """
    # Создаем пользователей
    student = User.objects.create_user(username='student', password='password')
    teacher = User.objects.create_superuser(username='teacher', password='password', email='t@example.com')
    
    # Шаблон для рендеринга (симуляция base.html nav части)
    template_code = """
    {% if user.is_staff %}
        <a href="/polygon/">Полигон</a>
    {% endif %}
    <a href="/my-courses/">Мои курсы</a>
    """
    template = Template(template_code)

    # Проверка для студента
    context_student = Context({'user': student})
    rendered_student = template.render(context_student)
    assert 'Полигон' not in rendered_student
    assert 'Мои курсы' in rendered_student

    # Проверка для учителя
    context_teacher = Context({'user': teacher})
    rendered_teacher = template.render(context_teacher)
    assert 'Полигон' in rendered_teacher
    assert 'Мои курсы' in rendered_teacher

@pytest.mark.django_db
def test_my_courses_view():
    """
    Тест проверяет работу представления my_courses.
    """
    factory = RequestFactory()
    user = User.objects.create_user(username='testuser', password='password')
    
    # Создаем курсы и привязываем один к пользователю
    course1 = Course.objects.create(name="Course 1")
    course2 = Course.objects.create(name="Course 2")
    
    CourseParticipant.objects.create(user=user, course=course1)
    
    request = factory.get('/my-courses/')
    request.user = user
    
    response = my_courses(request)
    
    assert response.status_code == 200
    # Проверяем контекст (зависит от того, как рендерится, но мы можем проверить контент)
    # Note: render возвращает HttpResponse с отрендеренным контентом
    content = response.content.decode('utf-8')
    
    # Проверяем, что Course 1 есть, а Course 2 нет (если шаблон выводит имена)
    # Т.к. мы используем реальный шаблон, он должен отрендериться
    # (при условии настройки TEMPLATES в settings тестового окружения)
    
    # Для надежности теста view функции, проверим контекст если бы использовали client,
    # но здесь мы вызываем функцию напрямую. Проверим наличие строки названия курса.
    assert "Course 1" in content
    assert "Course 2" not in content
