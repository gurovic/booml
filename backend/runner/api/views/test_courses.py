from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ...models import CourseParticipant, PinnedCourse, Section
from ...services.course_service import CourseCreateInput, create_course
from ...services.section_service import SectionCreateInput, create_section

User = get_user_model()


class CourseSelfEnrollTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.root_section = Section.objects.get(title="Авторское", parent__isnull=True)
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
        self.root_section = Section.objects.get(title="Авторское", parent__isnull=True)
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


class CourseParticipantsTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.root_section = Section.objects.get(title="Авторское", parent__isnull=True)
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
        self.root_section = Section.objects.get(title="Авторское", parent__isnull=True)
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


class MyCoursesTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.root_section = Section.objects.get(title="Авторское", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="My Section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
        self.course1 = create_course(
            CourseCreateInput(
                title="Course 1",
                owner=self.teacher,
                is_open=True,
                section=self.section,
                students=[self.student],
            )
        )
        self.course2 = create_course(
            CourseCreateInput(
                title="Course 2",
                owner=self.teacher,
                is_open=True,
                section=self.section,
                students=[self.student],
            )
        )
        self.my_courses_url = reverse("my-courses")

    def test_unauthenticated_user_forbidden(self):
        self.client.logout()
        resp = self.client.get(self.my_courses_url)
        self.assertIn(resp.status_code, (401, 403))

    def test_student_sees_courses(self):
        self.client.login(username="student", password="pass")
        resp = self.client.get(self.my_courses_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("pinned", data)
        self.assertIn("courses", data)
        self.assertEqual(data["courses"]["count"], 2)

    def test_teacher_sees_separate_lists(self):
        self.client.login(username="teacher", password="pass")
        resp = self.client.get(self.my_courses_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("pinned", data)
        self.assertIn("teaching", data)
        self.assertIn("studying", data)
        self.assertEqual(data["teaching"]["count"], 2)


class PinCourseTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.root_section = Section.objects.get(title="Авторское", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Pin Section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
        self.course = create_course(
            CourseCreateInput(
                title="Pin Course",
                owner=self.teacher,
                is_open=True,
                section=self.section,
                students=[self.student],
            )
        )
        self.pin_url = reverse("course-pin")
        self.unpin_url = reverse("course-unpin")

    def test_pin_course(self):
        self.client.login(username="student", password="pass")
        resp = self.client.post(
            self.pin_url,
            {"course_id": self.course.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(PinnedCourse.objects.filter(user=self.student).count(), 1)

    def test_pin_duplicate(self):
        self.client.login(username="student", password="pass")
        PinnedCourse.objects.create(user=self.student, course=self.course, position=0)
        resp = self.client.post(
            self.pin_url,
            {"course_id": self.course.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_unpin_course(self):
        self.client.login(username="student", password="pass")
        PinnedCourse.objects.create(user=self.student, course=self.course, position=0)
        resp = self.client.post(
            self.unpin_url,
            {"course_id": self.course.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PinnedCourse.objects.filter(user=self.student).count(), 0)

    def test_pin_non_participant(self):
        other = User.objects.create_user(username="other", password="pass")
        self.client.login(username="other", password="pass")
        resp = self.client.post(
            self.pin_url,
            {"course_id": self.course.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_pin_max_five(self):
        self.client.login(username="student", password="pass")
        for i in range(5):
            c = create_course(
                CourseCreateInput(
                    title=f"Extra {i}",
                    owner=self.teacher,
                    is_open=True,
                    section=self.section,
                    students=[self.student],
                )
            )
            PinnedCourse.objects.create(user=self.student, course=c, position=i)
        resp = self.client.post(
            self.pin_url,
            {"course_id": self.course.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
