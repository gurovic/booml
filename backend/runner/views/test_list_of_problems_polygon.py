from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from unittest.mock import patch
from django.http import HttpResponse
from .list_of_problems_polygon import problem_list_polygon
from ..models.problem import Problem


class ProblemListPolygonViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="u1", email="u1@example.com", password="pass"
        )
        self.other = User.objects.create_user(
            username="u2", email="u2@example.com", password="pass"
        )

        Problem.objects.bulk_create(
            [Problem(title=f"U1 Problem {i}", author=self.user) for i in range(55)]
        )
        Problem.objects.bulk_create(
            [Problem(title=f"U2 Problem {i}", author=self.other) for i in range(3)]
        )

        self.patch_target = f"{problem_list_polygon.__module__}.render"

    def _dummy_response(self):
        return HttpResponse("OK")

    def test_filters_current_user_and_paginates_first_page(self):
        request = self.factory.get("/polygon/?page=1&status=published&search=abc")
        request.user = self.user

        with patch(self.patch_target, return_value=self._dummy_response()) as mock_render:
            problem_list_polygon(request)

        args, kwargs = mock_render.call_args
        template_name = args[1]
        context = args[2]

        self.assertEqual(template_name, "runner/polygon/problem_list.html")

        page_obj = context["page_obj"]
        self.assertEqual(page_obj.paginator.per_page, 50)
        self.assertEqual(page_obj.number, 1)
        self.assertEqual(len(page_obj.object_list), 50)

        qs = context["querystring"]
        self.assertNotIn("page=", qs)
        self.assertIn("status=published", qs)
        self.assertIn("search=abc", qs)

    def test_second_page_has_remaining_items(self):
        request = self.factory.get("/polygon/?page=2")
        request.user = self.user

        with patch(self.patch_target, return_value=self._dummy_response()) as mock_render:
            problem_list_polygon(request)

        args, _ = mock_render.call_args
        context = args[2]
        page_obj = context["page_obj"]
        self.assertEqual(page_obj.number, 2)
        self.assertEqual(len(page_obj.object_list), 5)

    def test_other_user_sees_only_their_items(self):
        request = self.factory.get("/polygon/")
        request.user = self.other

        with patch(self.patch_target, return_value=self._dummy_response()) as mock_render:
            problem_list_polygon(request)

        args, _ = mock_render.call_args
        context = args[2]
        page_obj = context["page_obj"]
        self.assertEqual(page_obj.number, 1)
        self.assertEqual(len(page_obj.object_list), 3)