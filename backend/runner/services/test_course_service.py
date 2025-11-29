from django.contrib.auth import get_user_model
from django.test import TestCase

from runner.models import CourseParticipant
from runner.services.course_service import (
    CourseCreateInput,
    add_users_to_course,
    create_course,
)

User = get_user_model()


class CreateCourseTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.parent_course = create_course(
            CourseCreateInput(title="Parent", owner=self.owner)
        )

    def test_create_course_adds_owner_as_teacher(self):
        course = create_course(
            CourseCreateInput(
                title="Intro to ML",
                description="Basics",
                is_open=True,
                owner=self.owner,
                parent=self.parent_course,
            )
        )

        self.assertEqual(course.title, "Intro to ML")
        self.assertTrue(course.is_open)
        self.assertEqual(course.owner, self.owner)
        self.assertEqual(course.parent, self.parent_course)

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

    def test_add_users_to_course_adds_teacher_and_student(self):
        course = create_course(CourseCreateInput(title="Child", owner=self.owner))
        co_teacher = User.objects.create_user(username="teacher2", password="pass")
        student = User.objects.create_user(username="student1", password="pass")

        result = add_users_to_course(
            course, teachers=[co_teacher], students=[student]
        )

        self.assertEqual(CourseParticipant.objects.filter(course=course).count(), 3)
        roles = {
            p.user.username: (p.role, p.is_owner)
            for p in CourseParticipant.objects.filter(course=course)
        }
        self.assertEqual(roles["owner"], (CourseParticipant.Role.TEACHER, True))
        self.assertEqual(roles["teacher2"], (CourseParticipant.Role.TEACHER, False))
        self.assertEqual(roles["student1"], (CourseParticipant.Role.STUDENT, False))
        self.assertEqual(len(result["created"]), 2)  # co_teacher + student

    def test_add_users_updates_role_to_teacher(self):
        course = create_course(CourseCreateInput(title="Child2", owner=self.owner))
        user = User.objects.create_user(username="upgrade", password="pass")
        add_users_to_course(course, students=[user])

        result = add_users_to_course(course, teachers=[user])
        self.assertEqual(len(result["updated"]), 1)

        participant = CourseParticipant.objects.get(course=course, user=user)
        self.assertEqual(participant.role, CourseParticipant.Role.TEACHER)
        self.assertFalse(participant.is_owner)

    def test_owner_cannot_be_downgraded_to_student(self):
        course = create_course(CourseCreateInput(title="Child3", owner=self.owner))

        add_users_to_course(course, students=[self.owner])
        participant = CourseParticipant.objects.get(course=course, user=self.owner)
        self.assertEqual(participant.role, CourseParticipant.Role.TEACHER)
        self.assertTrue(participant.is_owner)
