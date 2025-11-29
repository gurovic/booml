from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.exceptions import ValidationError

from runner.models import Course, CourseParticipant
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

        result = add_users_to_course(course, students=[self.owner])
        participant = CourseParticipant.objects.get(course=course, user=self.owner)
        self.assertEqual(participant.role, CourseParticipant.Role.TEACHER)
        self.assertTrue(participant.is_owner)
        self.assertEqual(len(result["created"]), 0)
        self.assertEqual(len(result["updated"]), 0)

    def test_add_users_respects_allow_role_update_false(self):
        course = create_course(CourseCreateInput(title="NoUpdate", owner=self.owner))
        user = User.objects.create_user(username="student-teacher", password="pass")
        add_users_to_course(course, students=[user])

        result = add_users_to_course(
            course, teachers=[user], allow_role_update=False
        )
        participant = CourseParticipant.objects.get(course=course, user=user)
        self.assertEqual(participant.role, CourseParticipant.Role.STUDENT)
        self.assertFalse(participant.is_owner)
        self.assertEqual(len(result["updated"]), 0)

    def test_add_users_fixes_owner_flag_even_when_updates_disabled(self):
        course = create_course(CourseCreateInput(title="FixOwner", owner=self.owner))
        CourseParticipant.objects.filter(course=course, user=self.owner).update(
            is_owner=False
        )

        result = add_users_to_course(
            course, teachers=[self.owner], allow_role_update=False
        )
        participant = CourseParticipant.objects.get(course=course, user=self.owner)
        self.assertTrue(participant.is_owner)
        self.assertEqual(participant.role, CourseParticipant.Role.TEACHER)
        self.assertEqual(len(result["updated"]), 1)

    def test_add_users_rejects_unsaved_course(self):
        unsaved_course = Course(title="tmp", owner=self.owner)
        with self.assertRaises(ValueError):
            add_users_to_course(unsaved_course, students=[self.owner])

    def test_add_users_rejects_unsaved_users(self):
        course = create_course(CourseCreateInput(title="Child4", owner=self.owner))
        unsaved_user = User(username="ghost2")
        with self.assertRaises(ValueError):
            add_users_to_course(course, students=[unsaved_user])

    def test_cycle_validation_on_course_clean(self):
        parent = create_course(CourseCreateInput(title="ParentCycle", owner=self.owner))
        parent.parent = parent
        with self.assertRaises(ValidationError):
            parent.full_clean()
