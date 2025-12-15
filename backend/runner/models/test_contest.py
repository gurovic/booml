from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from runner.models import Contest, Course, CourseParticipant, Section

User = get_user_model()


class ContestVisibilityTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.outsider = User.objects.create_user(username="outsider", password="pass")

        self.section = Section.objects.create(title="Авторское", owner=self.teacher)
        self.course = Course.objects.create(
            title="Course A",
            owner=self.teacher,
            section=self.section,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseParticipant.Role.TEACHER,
            is_owner=True,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.student,
            role=CourseParticipant.Role.STUDENT,
        )

    def test_published_contest_visible_to_participants_only(self):
        contest = Contest.objects.create(
            course=self.course,
            title="Contest 1",
            created_by=self.teacher,
            is_published=True,
        )

        self.assertTrue(contest.is_visible_to(self.teacher))
        self.assertTrue(contest.is_visible_to(self.student))
        self.assertFalse(contest.is_visible_to(self.outsider))

    def test_draft_contest_visible_only_to_teachers(self):
        contest = Contest.objects.create(
            course=self.course,
            title="Draft Contest",
            created_by=self.teacher,
            is_published=False,
        )

        self.assertTrue(contest.is_visible_to(self.teacher))
        self.assertFalse(contest.is_visible_to(self.student))
        self.assertFalse(contest.is_visible_to(self.outsider))

    def test_defaults_for_scoring_registration_rating(self):
        contest = Contest.objects.create(
            course=self.course,
            title="Defaults",
            created_by=self.teacher,
            is_published=True,
        )

        self.assertEqual(contest.scoring, Contest.Scoring.IOI)
        self.assertEqual(contest.registration_type, Contest.Registration.OPEN)
        self.assertFalse(contest.is_rated)

    def test_private_contest_visibility_requires_allow_list(self):
        contest = Contest.objects.create(
            course=self.course,
            title="Private",
            created_by=self.teacher,
            is_published=True,
            access_type=Contest.AccessType.PRIVATE,
        )
        contest.allowed_participants.add(self.student)

        self.assertTrue(contest.is_visible_to(self.teacher))
        self.assertTrue(contest.is_visible_to(self.student))
        self.assertFalse(contest.is_visible_to(self.outsider))

    def test_link_contest_allows_course_participants(self):
        contest = Contest.objects.create(
            course=self.course,
            title="Link",
            created_by=self.teacher,
            is_published=True,
            access_type=Contest.AccessType.LINK,
        )

        self.assertTrue(contest.is_visible_to(self.student))
        self.assertFalse(contest.is_visible_to(self.outsider))

    def test_contest_cannot_be_saved_without_course(self):
        with self.assertRaises(ValidationError):
            Contest.objects.create(
                title="Orphan",
                created_by=self.teacher,
            )
