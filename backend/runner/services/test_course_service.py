from django.contrib.auth import get_user_model
from django.test import TestCase

from runner.models import CourseParticipant
from runner.services.course_service import CourseCreateInput, create_course

User = get_user_model()


class CreateCourseTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass")

    def test_create_course_adds_owner_as_teacher(self):
        course = create_course(
            CourseCreateInput(
                title="Intro to ML",
                description="Basics",
                is_open=True,
                owner=self.owner,
            )
        )

        self.assertEqual(course.title, "Intro to ML")
        self.assertTrue(course.is_open)
        self.assertEqual(course.owner, self.owner)

        membership = CourseParticipant.objects.get(course=course, user=self.owner)
        self.assertEqual(membership.role, CourseParticipant.Role.TEACHER)
        self.assertTrue(membership.is_owner)

    def test_create_course_with_extra_participants(self):
        co_teacher = User.objects.create_user(username="teacher2", password="pass")
        student = User.objects.create_user(username="student1", password="pass")

        course = create_course(
            CourseCreateInput(
                title="Course with team",
                owner=self.owner,
                teachers=[co_teacher, self.owner],
                students=[student, co_teacher],
            )
        )

        participants = CourseParticipant.objects.filter(course=course)
        self.assertEqual(participants.count(), 3)

        roles = {p.user_id: p.role for p in participants}
        self.assertEqual(roles[self.owner.id], CourseParticipant.Role.TEACHER)
        self.assertEqual(roles[co_teacher.id], CourseParticipant.Role.TEACHER)
        self.assertEqual(roles[student.id], CourseParticipant.Role.STUDENT)

        owners = CourseParticipant.objects.filter(course=course, is_owner=True)
        self.assertEqual(owners.count(), 1)
        self.assertEqual(owners[0].user, self.owner)

    def test_unsaved_owner_is_rejected(self):
        unsaved_user = User(username="ghost")

        with self.assertRaises(ValueError):
            create_course(
                CourseCreateInput(
                    title="Ghost course",
                    owner=unsaved_user,
                )
            )
