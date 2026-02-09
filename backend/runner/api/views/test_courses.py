from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ...models import CourseParticipant, Section
from ...services.course_service import CourseCreateInput, create_course
from ...services.section_service import SectionCreateInput, create_section

User = get_user_model()


class CourseSelfEnrollTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Teacher Section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
        self.course = create_course(
            CourseCreateInput(
                title="Open",
                owner=self.teacher,
                is_open=True,
                section=self.section,
            )
        )
        self.enroll_url = reverse("course-self-enroll", kwargs={"course_id": self.course.id})

    def test_self_enroll_open_course(self):
        User.objects.create_user(username="student", password="pass")
        self.client.login(username="student", password="pass")
        resp = self.client.post(self.enroll_url)
        self.assertEqual(resp.status_code, 403)
    def test_self_enroll_closed_course_forbidden(self):
        self.course.is_open = False
        self.course.save()
        User.objects.create_user(username="student2", password="pass")
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
        self.assertEqual(resp.status_code, 403)

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
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Creator Section",
                owner=self.user,
                parent=self.root_section,
            )
        )

    def test_course_create_success(self):
        resp = self.client.post(
            self.url,
            {"title": "Physics", "section_id": self.section.id},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "Physics")

    def test_course_create_invalid_section(self):
        resp = self.client.post(self.url, {"title": "Physics", "section_id": 999999})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("section_id", resp.json())

    def test_student_cannot_create_course_in_root_section(self):
        User.objects.create_user(username="student_root", password="pass", is_staff=False)
        self.client.login(username="student_root", password="pass")
        resp = self.client.post(
            self.url,
            {"title": "Root Course", "section_id": self.root_section.id},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("section_id", resp.json())


class SectionCreateTests(TestCase):
    def setUp(self):
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.url = reverse("section-create")

    def test_teacher_can_create_section_in_root(self):
        User.objects.create_user(username="teacher_root", password="pass", is_staff=True)
        self.client.login(username="teacher_root", password="pass")
        resp = self.client.post(self.url, {"title": "T-Section", "parent_id": self.root_section.id})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "T-Section")

    def test_student_cannot_create_section_in_root(self):
        User.objects.create_user(username="student_sec", password="pass", is_staff=False)
        self.client.login(username="student_sec", password="pass")
        resp = self.client.post(self.url, {"title": "S-Section", "parent_id": self.root_section.id})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("parent_id", resp.json())


class SectionDeleteTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="sec_owner", password="pass", is_staff=True)
        self.other_teacher = User.objects.create_user(username="sec_other", password="pass", is_staff=True)
        self.student = User.objects.create_user(username="sec_student", password="pass", is_staff=False)
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Deletable Section",
                owner=self.owner,
                parent=self.root_section,
            )
        )
        self.url = reverse("section-delete", kwargs={"section_id": self.section.id})

    def test_owner_can_delete_empty_section(self):
        self.client.login(username="sec_owner", password="pass")
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))
        self.assertFalse(Section.objects.filter(pk=self.section.id).exists())

    def test_owner_can_delete_section_with_courses_and_children(self):
        # Add a nested section and a course inside it, then delete the parent.
        nested = create_section(
            SectionCreateInput(
                title="Nested",
                owner=self.owner,
                parent=self.section,
            )
        )
        create_course(
            CourseCreateInput(
                title="Nested Course",
                owner=self.owner,
                is_open=True,
                section=nested,
            )
        )
        self.client.login(username="sec_owner", password="pass")
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))
        self.assertFalse(Section.objects.filter(pk=self.section.id).exists())
        self.assertFalse(Section.objects.filter(pk=nested.id).exists())

    def test_non_owner_teacher_forbidden(self):
        self.client.login(username="sec_other", password="pass")
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_student_forbidden(self):
        self.client.login(username="sec_student", password="pass")
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_root_cannot_be_deleted(self):
        url = reverse("section-delete", kwargs={"section_id": self.root_section.id})
        self.client.login(username="sec_owner", password="pass")
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 403)


class CourseParticipantsTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Teacher Section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
        self.course = create_course(
            CourseCreateInput(
                title="Open",
                owner=self.teacher,
                is_open=True,
                section=self.section,
            )
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


class CourseTreeTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Teacher Section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
        self.open_course = create_course(
            CourseCreateInput(
                title="Open Course",
                owner=self.teacher,
                is_open=True,
                section=self.section,
            )
        )
        self.closed_course = create_course(
            CourseCreateInput(
                title="Closed Course",
                owner=self.teacher,
                is_open=False,
                section=self.section,
            )
        )
        self.tree_url = reverse("course-tree")

    def test_unauthenticated_user_gets_empty_tree(self):
        """Unauthenticated users should get empty array, not 403"""
        self.client.logout()
        resp = self.client.get(self.tree_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_authenticated_user_sees_open_courses(self):
        """Authenticated users should see open courses but not closed ones"""
        self.client.login(username="student", password="pass")
        resp = self.client.get(self.tree_url)
        self.assertEqual(resp.status_code, 200)
        tree = resp.json()
        
        # Flatten the tree to get all course titles
        course_titles = []
        for section in tree:
            for child in section.get('children', []):
                if child.get('type') == 'course':
                    course_titles.append(child.get('title'))
                # Check nested sections
                for grandchild in child.get('children', []):
                    if grandchild.get('type') == 'course':
                        course_titles.append(grandchild.get('title'))
        
        # Student should see open course but not closed course
        self.assertIn("Open Course", course_titles)
        self.assertNotIn("Closed Course", course_titles)

    def test_course_owner_sees_own_courses(self):
        """Course owners should see their own courses including closed ones"""
        self.client.login(username="teacher", password="pass")
        resp = self.client.get(self.tree_url)
        self.assertEqual(resp.status_code, 200)
        tree = resp.json()
        
        # Flatten the tree to get all course titles
        course_titles = []
        for section in tree:
            for child in section.get('children', []):
                if child.get('type') == 'course':
                    course_titles.append(child.get('title'))
                # Check nested sections
                for grandchild in child.get('children', []):
                    if grandchild.get('type') == 'course':
                        course_titles.append(grandchild.get('title'))
        
        # Owner should see both open and closed courses
        self.assertIn("Open Course", course_titles)
        self.assertIn("Closed Course", course_titles)
