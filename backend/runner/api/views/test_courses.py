from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ...models import CourseParticipant, Section
from ...services.course_service import CourseCreateInput, create_course

User = get_user_model()


class CourseSelfEnrollTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.section = Section.objects.create(title="Авторское", owner=self.teacher)
        self.course = create_course(
            CourseCreateInput(title="Open", owner=self.teacher, section=self.section, is_open=True)
        )
        self.enroll_url = reverse("course-self-enroll", kwargs={"course_id": self.course.id})

    def test_self_enroll_open_course(self):
        student = User.objects.create_user(username="student", password="pass")
        self.client.login(username="student", password="pass")
        resp = self.client.post(self.enroll_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["course_id"], self.course.id)
        self.assertEqual(len(data["enrolled"]), 1)
        self.assertEqual(data["enrolled"][0]["user_id"], student.id)
        self.assertEqual(data["enrolled"][0]["role"], CourseParticipant.Role.STUDENT)

    def test_self_enroll_closed_course_forbidden(self):
        self.course.is_open = False
        self.course.save()
        student = User.objects.create_user(username="student2", password="pass")
        self.client.login(username="student2", password="pass")
        resp = self.client.post(self.enroll_url)
        self.assertEqual(resp.status_code, 403)

    def test_self_enroll_already_registered(self):
        student = User.objects.create_user(username="student3", password="pass")
        CourseParticipant.objects.create(
            course=self.course,
            user=student,
            role=CourseParticipant.Role.STUDENT,
            is_owner=False,
        )
        self.client.login(username="student3", password="pass")
        resp = self.client.post(self.enroll_url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("detail", resp.json())

    def test_self_enroll_requires_authentication(self):
        self.client.logout()
        resp = self.client.post(self.enroll_url)
        self.assertIn(resp.status_code, (401, 403))

    def test_self_enroll_nonexistent_course(self):
        student = User.objects.create_user(username="student4", password="pass")
        self.client.login(username="student4", password="pass")
        resp = self.client.post(reverse("course-self-enroll", kwargs={"course_id": 999999}))
        self.assertEqual(resp.status_code, 404)


class CourseCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="creator", password="pass")
        self.client.login(username="creator", password="pass")
        self.url = reverse("course-create")
        self.section = Section.objects.create(title="Авторское", owner=self.user)

    def test_course_create_success(self):
        resp = self.client.post(self.url, {"title": "Physics", "section_id": self.section.id})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "Physics")
        self.assertEqual(resp.json()["section_id"], self.section.id)

    def test_course_create_requires_section_ownership(self):
        foreign_owner = User.objects.create_user(username="other", password="pass")
        foreign_section = Section.objects.create(title="Олимпиады", owner=foreign_owner)

        resp = self.client.post(self.url, {"title": "Physics", "section_id": foreign_section.id})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("section_id", resp.json())


class CourseParticipantsTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.section = Section.objects.create(title="Авторское", owner=self.teacher)
        self.course = create_course(
            CourseCreateInput(title="Open", owner=self.teacher, section=self.section, is_open=True)
        )
        self.url = reverse("course-participants-update", kwargs={"course_id": self.course.id})

    def test_non_owner_forbidden(self):
        self.client.login(username="student", password="pass")
        resp = self.client.post(self.url, {"student_ids": [self.student.id]})
        self.assertEqual(resp.status_code, 403)

    def test_owner_can_add_student(self):
        self.client.login(username="teacher", password="pass")
        resp = self.client.post(self.url, {"student_ids": [self.student.id]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["created"]), 1)
