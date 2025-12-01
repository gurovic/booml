from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ...services.course_service import CourseCreateInput, create_course
from ...models import CourseParticipant

User = get_user_model()


class CourseAPITests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.client.login(username="teacher", password="pass")
        self.create_url = reverse("course-create")

    def test_create_course_returns_json(self):
        resp = self.client.post(self.create_url, {"title": "Physics"})
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("id", data)
        self.assertEqual(data["title"], "Physics")
        self.assertEqual(data["owner"], self.teacher.id)
        self.assertIsNone(data["parent_id"])

    def test_create_course_with_parent_and_participants(self):
        parent = create_course(CourseCreateInput(title="Parent", owner=self.teacher))
        co_teacher = User.objects.create_user(username="teacher2", password="pass")

        resp = self.client.post(
            self.create_url,
            {
                "title": "Child",
                "parent_id": parent.id,
                "teacher_ids": [co_teacher.id],
                "student_ids": [self.student.id],
            },
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["parent_id"], parent.id)
        participants = CourseParticipant.objects.filter(course_id=data["id"])
        self.assertEqual(participants.count(), 3)

    def test_course_participants_update_requires_teacher(self):
        course = create_course(CourseCreateInput(title="Standalone", owner=self.teacher))
        other = User.objects.create_user(username="other", password="pass")
        self.client.logout()
        self.client.login(username="other", password="pass")
        url = reverse("course-participants-update", kwargs={"course_id": course.id})
        resp = self.client.post(url, {"teacher_ids": [other.id]})
        self.assertEqual(resp.status_code, 403)

    def test_course_participants_update_adds_members(self):
        course = create_course(CourseCreateInput(title="Standalone", owner=self.teacher))
        sibling = User.objects.create_user(username="sibling", password="pass")
        url = reverse("course-participants-update", kwargs={"course_id": course.id})
        resp = self.client.post(
            url,
            {"teacher_ids": [sibling.id], "student_ids": [self.student.id]},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["created"]), 2)
        self.assertEqual(len(data["updated"]), 0)
        snapshot_ids = {item["user_id"] for item in data["created"]}
        self.assertIn(sibling.id, snapshot_ids)
        self.assertIn(self.student.id, snapshot_ids)

    def test_course_participants_invalid_user_fails(self):
        course = create_course(CourseCreateInput(title="Standalone", owner=self.teacher))
        url = reverse("course-participants-update", kwargs={"course_id": course.id})
        resp = self.client.post(url, {"teacher_ids": [9999]})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("teacher_ids", resp.json())
