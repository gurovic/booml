from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from ...models import Contest, ContestProblem, CourseParticipant, Problem, Section, SectionTeacher, Submission
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
        self.admin = User.objects.create_user(
            username="admin",
            password="pass",
            is_staff=True,
            is_superuser=True,
        )
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
        self.assertTrue(resp.json()["is_published"])

    def test_course_create_accepts_draft(self):
        resp = self.client.post(
            self.url,
            {"title": "Draft Physics", "section_id": self.section.id, "is_published": False},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(resp.json()["is_published"])

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

    def test_admin_can_create_course_in_foreign_nested_section(self):
        foreign_owner = User.objects.create_user(username="foreign_owner", password="pass")
        foreign_section = create_section(
            SectionCreateInput(
                title="Foreign Section",
                owner=foreign_owner,
                parent=self.root_section,
            )
        )
        self.client.login(username="admin", password="pass")
        resp = self.client.post(
            self.url,
            {"title": "Admin Course", "section_id": foreign_section.id},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "Admin Course")


class SectionCreateTests(TestCase):
    def setUp(self):
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.url = reverse("section-create")
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.admin = User.objects.create_user(
            username="admin",
            password="pass",
            is_staff=True,
            is_superuser=True,
        )
        self.nested = create_section(
            SectionCreateInput(
                title="Owned Section",
                owner=self.owner,
                parent=self.root_section,
            )
        )

    def test_teacher_can_create_section_in_root(self):
        User.objects.create_user(username="teacher_root", password="pass", is_staff=True)
        self.client.login(username="teacher_root", password="pass")
        resp = self.client.post(self.url, {"title": "T-Section", "parent_id": self.root_section.id})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "T-Section")
        self.assertTrue(resp.json()["is_published"])

    def test_teacher_can_create_draft_section_in_root(self):
        User.objects.create_user(username="teacher_root_draft", password="pass", is_staff=True)
        self.client.login(username="teacher_root_draft", password="pass")
        resp = self.client.post(
            self.url,
            {"title": "T-Draft", "parent_id": self.root_section.id, "is_published": False},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(resp.json()["is_published"])

    def test_student_cannot_create_section_in_root(self):
        User.objects.create_user(username="student_sec", password="pass", is_staff=False)
        self.client.login(username="student_sec", password="pass")
        resp = self.client.post(self.url, {"title": "S-Section", "parent_id": self.root_section.id})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("parent_id", resp.json())

    def test_admin_can_create_nested_section_anywhere(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.post(
            self.url,
            {"title": "Admin Nested", "parent_id": self.nested.id},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["title"], "Admin Nested")

    def test_assigned_teacher_cannot_create_nested_section_in_foreign_section(self):
        assigned_teacher = User.objects.create_user(
            username="assigned_teacher",
            password="pass",
            is_staff=True,
        )
        SectionTeacher.objects.create(section=self.nested, user=assigned_teacher)

        self.client.login(username="assigned_teacher", password="pass")
        resp = self.client.post(
            self.url,
            {"title": "Forbidden Nested", "parent_id": self.nested.id},
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json().get("parent_id"),
            ["Only section owner can create nested sections"],
        )


class SectionDeleteTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="sec_owner", password="pass", is_staff=True)
        self.other_teacher = User.objects.create_user(username="sec_other", password="pass", is_staff=True)
        self.student = User.objects.create_user(username="sec_student", password="pass", is_staff=False)
        self.admin = User.objects.create_user(
            username="admin",
            password="pass",
            is_staff=True,
            is_superuser=True,
        )
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

    def test_admin_can_delete_foreign_section(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("success"))
        self.assertFalse(Section.objects.filter(pk=self.section.id).exists())


class CourseParticipantsTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.admin = User.objects.create_user(
            username="admin",
            password="pass",
            is_staff=True,
            is_superuser=True,
        )
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

    def test_admin_can_add_student(self):
        self.client.login(username="admin", password="pass")
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
        self.empty_open_course = create_course(
            CourseCreateInput(
                title="Empty Open Course",
                owner=self.teacher,
                is_open=True,
                section=self.section,
            )
        )
        self.unpublished_course = create_course(
            CourseCreateInput(
                title="Draft Course",
                owner=self.teacher,
                is_open=True,
                is_published=False,
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
        self.problem = Problem.objects.create(title="Visible Problem", statement="", author=self.teacher, is_published=True)
        self.open_contest = Contest.objects.create(
            course=self.open_course,
            title="Visible Contest",
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
            access_type=Contest.AccessType.PUBLIC,
        )
        ContestProblem.objects.create(contest=self.open_contest, problem=self.problem, position=0)
        self.draft_contest = Contest.objects.create(
            course=self.unpublished_course,
            title="Draft Course Contest",
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
            access_type=Contest.AccessType.PUBLIC,
        )
        ContestProblem.objects.create(contest=self.draft_contest, problem=self.problem, position=0)
        self.tree_url = reverse("course-tree")

    def test_unauthenticated_user_sees_public_open_courses(self):
        """Unauthenticated users should see only open courses in public tree."""
        self.client.logout()
        resp = self.client.get(self.tree_url)
        self.assertEqual(resp.status_code, 200)
        tree = resp.json()

        course_titles = []
        for section in tree:
            for child in section.get("children", []):
                if child.get("type") == "course":
                    course_titles.append(child.get("title"))
                for grandchild in child.get("children", []):
                    if grandchild.get("type") == "course":
                        course_titles.append(grandchild.get("title"))

        self.assertIn("Open Course", course_titles)
        self.assertNotIn("Empty Open Course", course_titles)
        self.assertNotIn("Draft Course", course_titles)
        self.assertNotIn("Closed Course", course_titles)

    def test_authenticated_user_sees_open_courses(self):
        """Authenticated users should see open courses but not closed ones"""
        self.client.login(username="student", password="pass")
        resp = self.client.get(self.tree_url)
        self.assertEqual(resp.status_code, 200)
        tree = resp.json()

        # Flatten the tree to get all course titles
        course_titles = []
        for section in tree:
            for child in section.get("children", []):
                if child.get("type") == "course":
                    course_titles.append(child.get("title"))
                # Check nested sections
                for grandchild in child.get("children", []):
                    if grandchild.get("type") == "course":
                        course_titles.append(grandchild.get("title"))

        # Student should see open course but not closed course
        self.assertIn("Open Course", course_titles)
        self.assertNotIn("Empty Open Course", course_titles)
        self.assertNotIn("Draft Course", course_titles)
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
            for child in section.get("children", []):
                if child.get("type") == "course":
                    course_titles.append(child.get("title"))
                # Check nested sections
                for grandchild in child.get("children", []):
                    if grandchild.get("type") == "course":
                        course_titles.append(grandchild.get("title"))

        # Owner should see both open and closed courses
        self.assertIn("Open Course", course_titles)
        self.assertIn("Empty Open Course", course_titles)
        self.assertIn("Draft Course", course_titles)
        self.assertIn("Closed Course", course_titles)

    def test_assigned_teacher_sees_split_create_permissions_for_nested_section(self):
        assigned_teacher = User.objects.create_user(
            username="assigned_teacher_tree",
            password="pass",
            is_staff=True,
        )
        SectionTeacher.objects.create(section=self.section, user=assigned_teacher)

        self.client.login(username="assigned_teacher_tree", password="pass")
        resp = self.client.get(self.tree_url)
        self.assertEqual(resp.status_code, 200)

        def find_section(items, section_id):
            for item in items:
                if item.get("type") == "section" and item.get("id") == section_id:
                    return item
                children = item.get("children") or []
                found = find_section(children, section_id)
                if found is not None:
                    return found
            return None

        payload = find_section(resp.json(), self.section.id)
        self.assertIsNotNone(payload)
        self.assertTrue(payload["can_manage"])
        self.assertTrue(payload["can_create_course"])
        self.assertFalse(payload["can_create_subsection"])


class CourseBrowseTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher_browse", password="pass")
        self.student = User.objects.create_user(username="student_browse", password="pass")
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(title="S", owner=self.teacher, parent=self.root_section)
        )

        self.open_course = create_course(
            CourseCreateInput(title="Open C", owner=self.teacher, is_open=True, section=self.section)
        )
        self.open_course_no_activity = create_course(
            CourseCreateInput(title="Open No", owner=self.teacher, is_open=True, section=self.section)
        )
        self.private_course_invited = create_course(
            CourseCreateInput(title="Private Inv", owner=self.teacher, is_open=False, section=self.section)
        )
        CourseParticipant.objects.create(
            course=self.private_course_invited,
            user=self.student,
            role=CourseParticipant.Role.STUDENT,
            is_owner=False,
        )

        self.problem = Problem.objects.create(title="P", statement="", author=self.teacher, is_published=True)
        self.contest = Contest.objects.create(
            course=self.open_course,
            title="Contest",
            description="",
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
            access_type=Contest.AccessType.PUBLIC,
        )
        ContestProblem.objects.create(contest=self.contest, problem=self.problem, position=0)
        self.private_contest = Contest.objects.create(
            course=self.private_course_invited,
            title="Private Contest",
            description="",
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
            access_type=Contest.AccessType.PUBLIC,
        )
        ContestProblem.objects.create(contest=self.private_contest, problem=self.problem, position=0)
        Submission.objects.create(
            user=self.student,
            problem=self.problem,
            file=SimpleUploadedFile("a.csv", b"1,2,3\n", content_type="text/csv"),
            status=Submission.STATUS_ACCEPTED,
            metrics={"score": 0.5},
        )

        self.url = reverse("course-browse")

    def test_guest_sees_only_open_courses(self):
        self.client.logout()
        resp = self.client.get(self.url, {"tab": "mine"})
        self.assertEqual(resp.status_code, 200)
        items = resp.json().get("items") or []
        titles = {x["title"] for x in items}
        self.assertIn(self.open_course.title, titles)
        self.assertNotIn(self.open_course_no_activity.title, titles)
        self.assertNotIn(self.private_course_invited.title, titles)

    def test_student_mine_includes_open_with_submissions_and_private_invites(self):
        self.client.login(username="student_browse", password="pass")
        resp = self.client.get(self.url, {"tab": "mine"})
        self.assertEqual(resp.status_code, 200)
        items = resp.json().get("items") or []
        titles = {x["title"] for x in items}
        self.assertIn(self.open_course.title, titles)
        self.assertIn(self.private_course_invited.title, titles)
        self.assertNotIn(self.open_course_no_activity.title, titles)

    def test_teacher_admin_tab_includes_owned_courses(self):
        self.client.login(username="teacher_browse", password="pass")
        resp = self.client.get(self.url, {"tab": "admin"})
        self.assertEqual(resp.status_code, 200)
        items = resp.json().get("items") or []
        titles = {x["title"] for x in items}
        self.assertIn(self.open_course.title, titles)
        self.assertIn(self.private_course_invited.title, titles)
