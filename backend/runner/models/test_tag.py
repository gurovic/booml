from django.test import TestCase
from django.utils import timezone
from runner.models.problem import Problem
from runner.models.tag import Tag
from django.db import IntegrityError

class TagModelTest(TestCase):

    def test_create_tag(self):
        tag = Tag.objects.create(name="Machine Learning")

        self.assertEqual(tag.name, "Machine Learning")
        self.assertEqual(str(tag), "Machine Learning")

    def test_unique_tag_name(self):
        Tag.objects.create(name="Math")

        with self.assertRaises(IntegrityError):
            Tag.objects.create(name="Math")

class ProblemTagsTest(TestCase):

    def setUp(self):
        self.problem = Problem.objects.create(
            title="Test Problem",
            statement="Описание задачи",
            rating=1000,
            created_at=timezone.now().date()
        )

        self.tag1 = Tag.objects.create(name="ML")
        self.tag2 = Tag.objects.create(name="Math")

    def test_add_tags_to_problem(self):
        """Добавление тегов работает"""
        self.problem.tags.add(self.tag1, self.tag2)

        self.assertEqual(self.problem.tags.count(), 2)
        self.assertIn(self.tag1, self.problem.tags.all())
        self.assertIn(self.tag2, self.problem.tags.all())

    def test_tags_not_duplicated(self):
        """Повторное добавление того же тега не дублирует запись"""
        self.problem.tags.add(self.tag1)
        self.problem.tags.add(self.tag1)

        self.assertEqual(self.problem.tags.count(), 1)

    def test_remove_tag(self):
        """Удаление тегов"""
        self.problem.tags.add(self.tag1, self.tag2)
        self.problem.tags.remove(self.tag1)

        self.assertEqual(self.problem.tags.count(), 1)
        self.assertNotIn(self.tag1, self.problem.tags.all())