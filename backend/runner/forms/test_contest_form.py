from django.contrib.auth import get_user_model
from django.test import TestCase

from runner.forms.contest_draft import ContestForm
from runner.models import Course, Section

User = get_user_model()


class ContestFormTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.creator = User.objects.create_user(username="creator", password="pass")
        self.section = Section.objects.create(title="Авторское", owner=self.owner)
        self.course = Course.objects.create(title="Course A", owner=self.owner, section=self.section)

    def test_form_requires_course(self):
        form = ContestForm(
            data={
                "title": "Contest without course",
                "description": "",
                "source": "",
                "start_time": "",
                "duration_minutes": "",
                "is_published": False,
                "status": 0,
                "scoring": "icpc",
                "registration_type": "open",
                "is_rated": False,
            }
        )
        self.assertTrue(form.is_valid())
        with self.assertRaises(ValueError):
            form.save(created_by=self.creator)

    def test_save_sets_course_and_creator(self):
        form = ContestForm(
            data={
                "title": "Contest with course",
                "description": "desc",
                "source": "src",
                "start_time": "",
                "duration_minutes": "",
                "is_published": True,
                "status": 0,
                "scoring": "partial",
                "registration_type": "approval",
                "is_rated": True,
            },
            course=self.course,
        )
        self.assertTrue(form.is_valid())

        contest = form.save(created_by=self.creator)

        self.assertEqual(contest.course, self.course)
        self.assertEqual(contest.created_by, self.creator)
        self.assertTrue(contest.is_published)
        self.assertTrue(contest.is_rated)
        self.assertEqual(contest.scoring, "partial")
        self.assertEqual(contest.registration_type, "approval")
