from django.contrib.auth import get_user_model
from django.test import TestCase

from runner.models import Contest, Course, Problem, Section
from runner.services.section_service import build_section_tree

User = get_user_model()


class SectionTreeTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.root = Section.objects.create(title="Авторское", owner=self.owner)
        self.child = Section.objects.create(
            title="Подраздел",
            owner=self.owner,
            parent=self.root,
        )
        self.course = Course.objects.create(
            title="Курс по ML",
            owner=self.owner,
            section=self.child,
        )
        self.contest = Contest.objects.create(
            title="Стартовый контест",
            course=self.course,
            created_by=self.owner,
            is_published=True,
        )
        self.problem_easy = Problem.objects.create(title="A + B", statement="sum")
        self.problem_hard = Problem.objects.create(title="DP path", statement="dp")
        self.contest.problems.add(self.problem_hard, self.problem_easy)

    def test_tree_contains_sections_courses_contests_and_problems(self):
        tree = build_section_tree()

        self.assertEqual(len(tree), 1)
        root = tree[0]
        self.assertEqual(root["type"], "section")
        self.assertEqual(root["title"], "Авторское")

        nested_section = root["children"][0]
        self.assertEqual(nested_section["type"], "section")
        self.assertEqual(nested_section["title"], "Подраздел")

        course_node = nested_section["children"][0]
        self.assertEqual(course_node["type"], "course")
        self.assertEqual(course_node["title"], "Курс по ML")
        self.assertEqual(course_node["contest_count"], 1)
        self.assertEqual(len(course_node["contests"]), 1)

        contest_node = course_node["contests"][0]
        self.assertEqual(contest_node["type"], "contest")
        self.assertEqual(contest_node["problem_count"], 2)
        self.assertEqual(
            sorted(contest_node["problem_ids"]),
            sorted([self.problem_easy.id, self.problem_hard.id]),
        )
        self.assertTrue(all(item["type"] == "problem" for item in contest_node["problems"]))
