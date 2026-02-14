from django.contrib.auth import get_user_model
from django.test import TestCase

from runner.models import Contest, Course, CourseParticipant, Section, Notebook
from runner.services.section_service import SectionCreateInput, create_section

User = get_user_model()


class ContestVisibilityTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.co_teacher = User.objects.create_user(username="teacher2", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.outsider = User.objects.create_user(username="outsider", password="pass")

        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Teacher Section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
        self.course = Course.objects.create(
            title="Course A",
            owner=self.teacher,
            section=self.section,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseParticipant.Role.TEACHER,
            is_owner=True,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.co_teacher,
            role=CourseParticipant.Role.TEACHER,
            is_owner=False,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.student,
            role=CourseParticipant.Role.STUDENT,
        )

    def test_published_contest_visible_to_participants_only(self):
        contest = Contest.objects.create(
            course=self.course,
            title="Contest 1",
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )

        self.assertTrue(contest.is_visible_to(self.teacher))
        self.assertTrue(contest.is_visible_to(self.student))
        self.assertFalse(contest.is_visible_to(self.outsider))

    def test_draft_contest_visible_only_to_owner(self):
        contest = Contest.objects.create(
            course=self.course,
            title="Draft Contest",
            created_by=self.teacher,
            is_published=False,
        )

        self.assertTrue(contest.is_visible_to(self.teacher))
        self.assertTrue(contest.is_visible_to(self.co_teacher))
        self.assertFalse(contest.is_visible_to(self.student))
        self.assertFalse(contest.is_visible_to(self.outsider))

    def test_open_course_public_contest_visible_to_any_user(self):
        self.course.is_open = True
        self.course.save(update_fields=["is_open"])
        contest = Contest.objects.create(
            course=self.course,
            title="Open Contest",
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )

        self.assertTrue(contest.is_visible_to(self.outsider))

    def test_defaults_for_scoring_registration_rating(self):
        contest = Contest.objects.create(
            course=self.course,
            title="Defaults",
            created_by=self.teacher,
            is_published=True,
        )

        self.assertEqual(contest.scoring, Contest.Scoring.IOI)
        self.assertEqual(contest.registration_type, Contest.Registration.OPEN)
        self.assertFalse(contest.is_rated)

    def test_private_contest_visibility_requires_allow_list(self):
        contest = Contest.objects.create(
            course=self.course,
            title="Private",
            created_by=self.teacher,
            is_published=True,
            access_type=Contest.AccessType.PRIVATE,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )
        contest.allowed_participants.add(self.student)

        self.assertTrue(contest.is_visible_to(self.teacher))
        self.assertTrue(contest.is_visible_to(self.student))
        self.assertFalse(contest.is_visible_to(self.outsider))

    def test_link_contest_allows_course_participants(self):
        contest = Contest.objects.create(
            course=self.course,
            title="Link",
            created_by=self.teacher,
            is_published=True,
            access_type=Contest.AccessType.LINK,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )

        self.assertTrue(contest.is_visible_to(self.student))
        self.assertFalse(contest.is_visible_to(self.outsider))


class NotebookContestTests(TestCase):
    """Tests for notebook-based contest functionality"""
    
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
        self.course = Course.objects.create(
            title="Course A",
            owner=self.teacher,
            section=self.section,
        )
    
    def test_create_regular_contest(self):
        """Test creating a regular (problem-based) contest"""
        contest = Contest.objects.create(
            course=self.course,
            title="Regular Contest",
            contest_type=Contest.ContestType.REGULAR,
            created_by=self.teacher,
        )
        
        self.assertEqual(contest.contest_type, Contest.ContestType.REGULAR)
        self.assertIsNone(contest.template_notebook)
    
    def test_create_notebook_contest(self):
        """Test creating a notebook-based contest"""
        # Create template notebook
        template = Notebook.objects.create(
            title="Contest Template",
            owner=self.teacher
        )
        
        contest = Contest.objects.create(
            course=self.course,
            title="Notebook Contest",
            contest_type=Contest.ContestType.NOTEBOOK,
            template_notebook=template,
            created_by=self.teacher,
        )
        
        self.assertEqual(contest.contest_type, Contest.ContestType.NOTEBOOK)
        self.assertEqual(contest.template_notebook, template)
    
    def test_default_contest_type_is_regular(self):
        """Test that default contest type is regular"""
        contest = Contest.objects.create(
            course=self.course,
            title="Default Contest",
            created_by=self.teacher,
        )
        
        self.assertEqual(contest.contest_type, Contest.ContestType.REGULAR)
