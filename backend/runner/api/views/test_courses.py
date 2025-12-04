from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ...models import CourseParticipant
from ...services.course_service import CourseCreateInput, create_course

User = get_user_model()


class CourseSelfEnrollTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.course = create_course(CourseCreateInput(title="Open", owner=self.teacher, is_open=True))
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
