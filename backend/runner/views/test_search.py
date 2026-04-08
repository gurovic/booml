from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from django.contrib.auth.models import User
from unittest.mock import Mock, patch
import json

from ..models import Course, Problem, Contest, Section
from ..views.search import search


class SearchViewTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        # Создаем пользователя для всех моделей
        self.user = User.objects.create_user(
            username='testuser',
            password='12345'
        )

        # Создаем раздел для курсов
        self.section = Section.objects.create(
            title="Программирование",
            owner=self.user
        )

        # Создаем курсы с уникальными названиями для точного поиска
        self.course1 = Course.objects.create(
            title="Python для начинающих",
            owner=self.user,
            section=self.section
        )
        self.course2 = Course.objects.create(
            title="Django для профи",
            owner=self.user,
            section=self.section
        )
        self.course3 = Course.objects.create(
            title="Алгоритмы",
            owner=self.user,
            section=self.section
        )

        # Создаем задачи
        Problem.objects.create(title="Сумма двух чисел", rating=100)
        Problem.objects.create(title="Обратный порядок", rating=200)
        Problem.objects.create(title="Поиск в массиве", rating=300)

        # Создаем контесты с привязкой к разным курсам
        Contest.objects.create(
            title="Новогодний контест",
            created_by=self.user,
            course=self.course1
        )
        Contest.objects.create(
            title="Летний марафон",
            created_by=self.user,
            course=self.course2
        )
        Contest.objects.create(
            title="Отбор на олимпиаду",
            created_by=self.user,
            course=self.course3
        )

    def test_search_empty_query(self):
        request = self.factory.get('/backend/search/', {'q': ''})
        response = search(request)

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['courses'], [])
        self.assertEqual(data['problems'], [])
        self.assertEqual(data['contests'], [])

    def test_search_no_query_param(self):
        request = self.factory.get('/backend/search/')
        response = search(request)

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['courses'], [])
        self.assertEqual(data['problems'], [])
        self.assertEqual(data['contests'], [])

    def test_search_all_types_default(self):
        request = self.factory.get('/backend/search/', {'q': 'Python'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(len(data['courses']), 1)
        self.assertEqual(data['courses'][0]['title'], "Python для начинающих")

        self.assertEqual(data['problems'], [])
        self.assertEqual(data['contests'], [])

    def test_search_all_types_explicit(self):
        request = self.factory.get('/backend/search/', {'q': 'Python', 'type': 'all'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(len(data['courses']), 1)
        self.assertEqual(data['courses'][0]['title'], "Python для начинающих")

        self.assertEqual(data['problems'], [])
        self.assertEqual(data['contests'], [])

    def test_search_courses_only(self):
        # Ищем конкретный курс, чтобы получить ровно 1 результат
        request = self.factory.get('/backend/search/', {'q': 'Python', 'type': 'course'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(len(data['courses']), 1)
        self.assertEqual(data['courses'][0]['title'], "Python для начинающих")
        self.assertEqual(data['problems'], [])
        self.assertEqual(data['contests'], [])

    def test_search_problems_only(self):
        request = self.factory.get('/backend/search/', {'q': 'сумма', 'type': 'problem'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(data['courses'], [])

        self.assertEqual(len(data['problems']), 1)
        self.assertEqual(data['problems'][0]['title'], "Сумма двух чисел")
        self.assertEqual(data['problems'][0]['rating'], 100)

        self.assertEqual(data['contests'], [])

    def test_search_contests_only(self):
        request = self.factory.get('/backend/search/', {'q': 'летний', 'type': 'contest'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(data['courses'], [])
        self.assertEqual(data['problems'], [])

        self.assertEqual(len(data['contests']), 1)
        self.assertEqual(data['contests'][0]['title'], "Летний марафон")

    def test_search_case_insensitive(self):
        request = self.factory.get('/backend/search/', {'q': 'python'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(len(data['courses']), 1)
        self.assertEqual(data['courses'][0]['title'], "Python для начинающих")

    def test_search_partial_match(self):
        request = self.factory.get('/backend/search/', {'q': 'djan'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(len(data['courses']), 1)
        self.assertEqual(data['courses'][0]['title'], "Django для профи")

    def test_search_no_results(self):
        request = self.factory.get('/backend/search/', {'q': 'несуществующийзапрос'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(data['courses'], [])
        self.assertEqual(data['problems'], [])
        self.assertEqual(data['contests'], [])

    def test_search_problems_with_rating_field(self):
        # Получаем ID задачи "Обратный порядок"
        problem = Problem.objects.get(title="Обратный порядок")

        request = self.factory.get('/backend/search/', {'q': 'обратный', 'type': 'problem'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(len(data['problems']), 1)
        result_problem = data['problems'][0]
        self.assertIn('id', result_problem)
        self.assertEqual(result_problem['id'], problem.id)
        self.assertIn('title', result_problem)
        self.assertEqual(result_problem['title'], "Обратный порядок")
        self.assertIn('rating', result_problem)
        self.assertEqual(result_problem['rating'], 200)

    def test_search_courses_fields(self):
        # Получаем ID курса "Алгоритмы"
        course = Course.objects.get(title="Алгоритмы")

        request = self.factory.get('/backend/search/', {'q': 'алгоритмы', 'type': 'course'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(len(data['courses']), 1)
        result_course = data['courses'][0]
        self.assertIn('id', result_course)
        self.assertEqual(result_course['id'], course.id)
        self.assertIn('title', result_course)
        self.assertEqual(result_course['title'], "Алгоритмы")
        self.assertNotIn('rating', result_course)

    def test_search_contests_fields(self):
        # Получаем ID контеста "Новогодний контест"
        contest = Contest.objects.get(title="Новогодний контест")

        request = self.factory.get('/backend/search/', {'q': 'новогодний', 'type': 'contest'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(len(data['contests']), 1)
        result_contest = data['contests'][0]
        self.assertIn('id', result_contest)
        self.assertEqual(result_contest['id'], contest.id)
        self.assertIn('title', result_contest)
        self.assertEqual(result_contest['title'], "Новогодний контест")
        self.assertNotIn('rating', result_contest)

    def test_search_with_multiple_results_in_different_categories(self):
        # Создаем дополнительные элементы
        Problem.objects.create(title="Python задачи", rating=150)

        # Не создаем новый курс, используем существующий
        Contest.objects.create(
            title="Python контест",
            created_by=self.user,
            course=self.course1  # Используем существующий курс
        )

        request = self.factory.get('/backend/search/', {'q': 'Python', 'type': 'all'})
        response = search(request)

        data = json.loads(response.content)

        # Должен найти: 1 курс (Python для начинающих), 1 задачу (Python задачи), 1 контест (Python контест)
        self.assertEqual(len(data['courses']), 1)
        self.assertEqual(len(data['problems']), 1)
        self.assertEqual(len(data['contests']), 1)

        # Проверяем, что это именно те объекты, которые мы ожидаем
        self.assertEqual(data['courses'][0]['title'], "Python для начинающих")
        self.assertEqual(data['problems'][0]['title'], "Python задачи")
        self.assertEqual(data['contests'][0]['title'], "Python контест")

    def test_search_with_exact_match(self):
        request = self.factory.get('/backend/search/', {'q': 'Алгоритмы', 'type': 'course'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(len(data['courses']), 1)
        self.assertEqual(data['courses'][0]['title'], "Алгоритмы")

    def test_invalid_type_param(self):
        request = self.factory.get('/backend/search/', {'q': 'Python', 'type': 'invalid'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(data['courses'], [])
        self.assertEqual(data['problems'], [])
        self.assertEqual(data['contests'], [])

    def test_response_is_json(self):
        request = self.factory.get('/backend/search/', {'q': 'Python'})
        response = search(request)

        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_special_characters_in_query(self):
        request = self.factory.get('/backend/search/', {'q': 'Python#'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(data['courses'], [])
        self.assertEqual(data['problems'], [])
        self.assertEqual(data['contests'], [])

    def test_long_query(self):
        long_query = "a" * 1000
        request = self.factory.get('/backend/search/', {'q': long_query})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(data['courses'], [])
        self.assertEqual(data['problems'], [])
        self.assertEqual(data['contests'], [])

    def test_unicode_query(self):
        request = self.factory.get('/backend/search/', {'q': 'Питон'})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(data['courses'], [])
        self.assertEqual(data['problems'], [])
        self.assertEqual(data['contests'], [])

    def test_whitespace_query(self):
        request = self.factory.get('/backend/search/', {'q': '   '})
        response = search(request)

        data = json.loads(response.content)

        self.assertEqual(data['courses'], [])
        self.assertEqual(data['problems'], [])
        self.assertEqual(data['contests'], [])


class SearchViewUnitTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    @patch('runner.models.Course.objects')
    def test_course_filter_called_correctly(self, mock_course_objects):
        mock_course_objects.filter.return_value.values.return_value = []

        request = self.factory.get('/backend/search/', {'q': 'test', 'type': 'course'})
        search(request)

        mock_course_objects.filter.assert_called_once_with(title__icontains='test')

    @patch('runner.models.Problem.objects')
    def test_problem_filter_called_correctly(self, mock_problem_objects):
        mock_problem_objects.filter.return_value.values.return_value = []

        request = self.factory.get('/backend/search/', {'q': 'test', 'type': 'problem'})
        search(request)

        mock_problem_objects.filter.assert_called_once_with(title__icontains='test')

    @patch('runner.models.Contest.objects')
    def test_contest_filter_called_correctly(self, mock_contest_objects):
        mock_contest_objects.filter.return_value.values.return_value = []

        request = self.factory.get('/backend/search/', {'q': 'test', 'type': 'contest'})
        search(request)

        mock_contest_objects.filter.assert_called_once_with(title__icontains='test')

    @patch('runner.models.Course.objects')
    @patch('runner.models.Problem.objects')
    @patch('runner.models.Contest.objects')
    def test_all_queries_called_for_all_type(self, mock_contest, mock_problem, mock_course):
        mock_course.filter.return_value.values.return_value = []
        mock_problem.filter.return_value.values.return_value = []
        mock_contest.filter.return_value.values.return_value = []

        request = self.factory.get('/backend/search/', {'q': 'test', 'type': 'all'})
        search(request)

        mock_course.filter.assert_called_once_with(title__icontains='test')
        mock_problem.filter.assert_called_once_with(title__icontains='test')
        mock_contest.filter.assert_called_once_with(title__icontains='test')

    def test_values_fields_for_courses(self):
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.values.return_value = []

        with patch('runner.models.Course.objects', mock_queryset):
            request = self.factory.get('/backend/search/', {'q': 'test', 'type': 'course'})
            search(request)

            mock_queryset.values.assert_called_once_with('id', 'title')

    def test_values_fields_for_problems(self):
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.values.return_value = []

        with patch('runner.models.Problem.objects', mock_queryset):
            request = self.factory.get('/backend/search/', {'q': 'test', 'type': 'problem'})
            search(request)

            mock_queryset.values.assert_called_once_with('id', 'title', 'rating')

    def test_values_fields_for_contests(self):
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.values.return_value = []

        with patch('runner.models.Contest.objects', mock_queryset):
            request = self.factory.get('/backend/search/', {'q': 'test', 'type': 'contest'})
            search(request)

            mock_queryset.values.assert_called_once_with('id', 'title')