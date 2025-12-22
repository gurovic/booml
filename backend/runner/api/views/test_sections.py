from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ...models import Course, Section

User = get_user_model()


class SectionCreateTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", is_staff=True
        )
        self.student = User.objects.create_user(
            username="student", password="pass", is_staff=False
        )
        self.url = reverse("section-create")

    def test_teacher_can_create_section(self):
        self.client.login(username="teacher", password="pass")
        resp = self.client.post(
            self.url,
            {"title": "New Section"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "New Section")

    def test_student_cannot_create_section(self):
        self.client.login(username="student", password="pass")
        resp = self.client.post(
            self.url,
            {"title": "New Section"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_create_section(self):
        resp = self.client.post(
            self.url,
            {"title": "New Section"},
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (401, 403))

    def test_create_section_with_parent(self):
        self.client.login(username="teacher", password="pass")
        parent = Section.objects.create(title="Parent", owner=self.teacher)

        resp = self.client.post(
            self.url,
            {"title": "Child", "parent_id": parent.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["parent"], parent.id)

    def test_create_section_invalid_parent(self):
        self.client.login(username="teacher", password="pass")
        resp = self.client.post(
            self.url,
            {"title": "Child", "parent_id": 999999},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_cannot_create_child_under_section_with_courses(self):
        self.client.login(username="teacher", password="pass")
        parent = Section.objects.create(title="Parent", owner=self.teacher)
        course = Course.objects.create(title="Course", owner=self.teacher)
        parent.courses.add(course)

        resp = self.client.post(
            self.url,
            {"title": "Child", "parent_id": parent.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class SectionListTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", is_staff=True
        )
        self.student = User.objects.create_user(
            username="student", password="pass", is_staff=False
        )
        self.url = reverse("section-list")

    def test_teacher_can_list_sections(self):
        Section.objects.create(title="S1", owner=self.teacher)
        Section.objects.create(title="S2", owner=self.teacher)

        self.client.login(username="teacher", password="pass")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_student_cannot_list_sections(self):
        self.client.login(username="student", password="pass")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_list_returns_only_root_sections(self):
        parent = Section.objects.create(title="Parent", owner=self.teacher)
        Section.objects.create(title="Child", parent=parent, owner=self.teacher)

        self.client.login(username="teacher", password="pass")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]["title"], "Parent")


class SectionDetailTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", is_staff=True
        )
        self.student = User.objects.create_user(
            username="student", password="pass", is_staff=False
        )
        self.section = Section.objects.create(title="Test", owner=self.teacher)
        self.url = reverse("section-detail", kwargs={"section_id": self.section.id})

    def test_teacher_can_view_section(self):
        self.client.login(username="teacher", password="pass")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Test")

    def test_student_cannot_view_section(self):
        self.client.login(username="student", password="pass")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_nonexistent_section_returns_404(self):
        self.client.login(username="teacher", password="pass")
        resp = self.client.get(reverse("section-detail", kwargs={"section_id": 999999}))
        self.assertEqual(resp.status_code, 404)


class SectionUpdateTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", is_staff=True
        )
        self.student = User.objects.create_user(
            username="student", password="pass", is_staff=False
        )
        self.section = Section.objects.create(title="Original", owner=self.teacher)
        self.url = reverse("section-update", kwargs={"section_id": self.section.id})

    def test_teacher_can_update_section(self):
        self.client.login(username="teacher", password="pass")
        resp = self.client.patch(
            self.url,
            {"title": "Updated"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Updated")

    def test_student_cannot_update_section(self):
        self.client.login(username="student", password="pass")
        resp = self.client.patch(
            self.url,
            {"title": "Updated"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_can_add_courses_to_section(self):
        self.client.login(username="teacher", password="pass")
        course = Course.objects.create(title="Course", owner=self.teacher)

        resp = self.client.patch(
            self.url,
            {"add_course_ids": [course.id]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(course.id, resp.json()["courses"])

    def test_cannot_add_courses_to_section_with_children(self):
        self.client.login(username="teacher", password="pass")
        Section.objects.create(title="Child", parent=self.section, owner=self.teacher)
        course = Course.objects.create(title="Course", owner=self.teacher)

        resp = self.client.patch(
            self.url,
            {"add_course_ids": [course.id]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class SectionDeleteTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", is_staff=True
        )
        self.student = User.objects.create_user(
            username="student", password="pass", is_staff=False
        )
        self.section = Section.objects.create(title="ToDelete", owner=self.teacher)
        self.url = reverse("section-delete", kwargs={"section_id": self.section.id})

    def test_teacher_can_delete_section(self):
        self.client.login(username="teacher", password="pass")
        resp = self.client.delete(self.url)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Section.objects.filter(id=self.section.id).exists())

    def test_student_cannot_delete_section(self):
        self.client.login(username="student", password="pass")
        resp = self.client.delete(self.url)
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Section.objects.filter(id=self.section.id).exists())


class CourseCreatePermissionTests(TestCase):
    """Tests to verify only teachers can create courses."""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", is_staff=True
        )
        self.student = User.objects.create_user(
            username="student", password="pass", is_staff=False
        )
        self.url = reverse("course-create")

    def test_teacher_can_create_course(self):
        self.client.login(username="teacher", password="pass")
        resp = self.client.post(
            self.url,
            {"title": "New Course"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_student_cannot_create_course(self):
        self.client.login(username="student", password="pass")
        resp = self.client.post(
            self.url,
            {"title": "New Course"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
