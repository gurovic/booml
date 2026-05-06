import json
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from runner.models import Contest, Course, CourseParticipant, Problem, ProblemDescriptor, Section, Submission
from runner.services.section_service import SectionCreateInput, create_section
from runner.views.contest_leaderboard import build_course_leaderboard, course_leaderboard

User = get_user_model()


class CourseLeaderboardTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self._media_root = tempfile.mkdtemp()
        self._override_media = override_settings(MEDIA_ROOT=self._media_root)
        self._override_media.enable()

        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.alice = User.objects.create_user(username="alice", password="pass")
        self.bob = User.objects.create_user(username="bob", password="pass")
        self.charlie = User.objects.create_user(username="charlie", password="pass")

        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Leaderboard Test Section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
        self.course = Course.objects.create(
            title="Test Course",
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
            user=self.alice,
            role=CourseParticipant.Role.STUDENT,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.bob,
            role=CourseParticipant.Role.STUDENT,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.charlie,
            role=CourseParticipant.Role.STUDENT,
        )

        self.problem1 = Problem.objects.create(title="Problem A", statement="desc", rating=1000)
        self.problem2 = Problem.objects.create(title="Problem B", statement="desc", rating=1000)
        ProblemDescriptor.objects.create(problem=self.problem1, metric="rmse")
        ProblemDescriptor.objects.create(problem=self.problem2, metric="accuracy")

    def tearDown(self):
        self._override_media.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)
        super().tearDown()

    def _create_submission(self, user, problem, metric_key, metric_value, status=Submission.STATUS_ACCEPTED):
        content = b"id,pred\n1,0.1\n"
        uploaded = SimpleUploadedFile("preds.csv", content, content_type="text/csv")
        return Submission.objects.create(
            user=user,
            problem=problem,
            file=uploaded,
            status=status,
            metrics={metric_key: metric_value},
        )

    def test_build_course_leaderboard_empty(self):
        leaderboard = build_course_leaderboard(self.course)
        self.assertEqual(leaderboard["course_id"], self.course.id)
        self.assertEqual(leaderboard["course_title"], "Test Course")
        self.assertEqual(len(leaderboard["contests"]), 0)
        self.assertEqual(len(leaderboard["entries"]), 3)
        entries = {entry["username"]: entry for entry in leaderboard["entries"]}
        self.assertIn("alice", entries)
        self.assertIn("bob", entries)
        self.assertIn("charlie", entries)
        for entry in leaderboard["entries"]:
            self.assertEqual(entry["total_score"], 0.0)
            self.assertEqual(entry["contests_completed"], 0)
            self.assertEqual(entry["problems_solved"], 0)

    def test_build_course_leaderboard_with_contest_no_submissions(self):
        contest = Contest.objects.create(
            title="Contest 1",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )
        contest.problems.add(self.problem1)

        leaderboard = build_course_leaderboard(self.course)
        self.assertEqual(len(leaderboard["contests"]), 1)
        self.assertEqual(leaderboard["contests"][0]["title"], "Contest 1")
        self.assertEqual(len(leaderboard["entries"]), 3)
        for entry in leaderboard["entries"]:
            self.assertEqual(entry["total_score"], 0.0)
            self.assertEqual(entry["contests_completed"], 0)
            self.assertEqual(entry["problems_solved"], 0)

    def test_build_course_leaderboard_with_submissions(self):
        contest = Contest.objects.create(
            title="Contest 1",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )
        contest.problems.add(self.problem1, self.problem2)

        sub_alice_p1 = self._create_submission(self.alice, self.problem1, "rmse", 0.4)
        sub_bob_p1 = self._create_submission(self.bob, self.problem1, "rmse", 0.2)
        sub_alice_p2 = self._create_submission(self.alice, self.problem2, "accuracy", 0.9)
        sub_bob_p2 = self._create_submission(self.bob, self.problem2, "accuracy", 0.8)

        leaderboard = build_course_leaderboard(self.course)
        entries = {entry["username"]: entry for entry in leaderboard["entries"]}

        self.assertEqual(len(entries), 3)

        self.assertEqual(entries["alice"]["problems_solved"], 2)
        self.assertEqual(entries["bob"]["problems_solved"], 2)
        self.assertEqual(entries["charlie"]["problems_solved"], 0)

        self.assertEqual(entries["alice"]["contests_completed"], 1)
        self.assertEqual(entries["bob"]["contests_completed"], 1)
        self.assertEqual(entries["charlie"]["contests_completed"], 0)

        self.assertGreater(entries["alice"]["total_score"], 0)
        self.assertGreater(entries["bob"]["total_score"], 0)
        self.assertEqual(entries["charlie"]["total_score"], 0)

        self.assertIsNotNone(entries["alice"]["rank"])
        self.assertIsNotNone(entries["bob"]["rank"])
        self.assertIsNotNone(entries["charlie"]["rank"])

    def test_build_course_leaderboard_multiple_contests(self):
        contest1 = Contest.objects.create(
            title="Contest 1",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )
        contest1.problems.add(self.problem1)

        contest2 = Contest.objects.create(
            title="Contest 2",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )
        contest2.problems.add(self.problem2)

        self._create_submission(self.alice, self.problem1, "rmse", 0.3)
        self._create_submission(self.bob, self.problem1, "rmse", 0.4)
        self._create_submission(self.bob, self.problem2, "accuracy", 0.9)

        leaderboard = build_course_leaderboard(self.course)

        self.assertEqual(len(leaderboard["contests"]), 2)
        contests_titles = [c["title"] for c in leaderboard["contests"]]
        self.assertIn("Contest 1", contests_titles)
        self.assertIn("Contest 2", contests_titles)

        entries = {entry["username"]: entry for entry in leaderboard["entries"]}

        self.assertEqual(entries["alice"]["contests_completed"], 1)
        self.assertEqual(entries["bob"]["contests_completed"], 2)
        self.assertEqual(entries["charlie"]["contests_completed"], 0)

        self.assertGreaterEqual(entries["bob"]["rank"], 1)
        self.assertGreaterEqual(entries["alice"]["rank"], 2)

    def test_build_course_leaderboard_excludes_unpublished_contests(self):
        contest_published = Contest.objects.create(
            title="Published Contest",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )
        contest_published.problems.add(self.problem1)

        Contest.objects.create(
            title="Draft Contest",
            course=self.course,
            created_by=self.teacher,
            is_published=False,
            approval_status=Contest.ApprovalStatus.PENDING,
        )

        leaderboard = build_course_leaderboard(self.course)
        self.assertEqual(len(leaderboard["contests"]), 1)
        self.assertEqual(leaderboard["contests"][0]["title"], "Published Contest")

    def test_build_course_leaderboard_only_students(self):
        contest = Contest.objects.create(
            title="Contest 1",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )
        contest.problems.add(self.problem1)

        self._create_submission(self.teacher, self.problem1, "rmse", 0.1)
        self._create_submission(self.alice, self.problem1, "rmse", 0.3)

        leaderboard = build_course_leaderboard(self.course)
        entries = {entry["username"]: entry for entry in leaderboard["entries"]}

        self.assertIn("alice", entries)
        self.assertIn("bob", entries)
        self.assertIn("charlie", entries)
        self.assertNotIn("teacher", entries)


class CourseLeaderboardViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self._media_root = tempfile.mkdtemp()
        self._override_media = override_settings(MEDIA_ROOT=self._media_root)
        self._override_media.enable()

        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")

        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="View Test Section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
        self.course = Course.objects.create(
            title="View Test Course",
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
            user=self.student,
            role=CourseParticipant.Role.STUDENT,
        )

        self.problem = Problem.objects.create(title="Problem X", statement="desc", rating=1000)
        ProblemDescriptor.objects.create(problem=self.problem, metric="mse")

    def tearDown(self):
        self._override_media.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)
        super().tearDown()

    def test_teacher_can_access_leaderboard(self):
        request = self.factory.get(f"/course/{self.course.id}/leaderboard/")
        request.user = self.teacher
        response = course_leaderboard(request, course_id=self.course.id)
        self.assertEqual(response.status_code, 200)

    def test_course_owner_can_access_leaderboard(self):
        request = self.factory.get(f"/course/{self.course.id}/leaderboard/")
        request.user = self.teacher
        response = course_leaderboard(request, course_id=self.course.id)
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access_leaderboard(self):
        request = self.factory.get(f"/course/{self.course.id}/leaderboard/")
        request.user = self.student
        response = course_leaderboard(request, course_id=self.course.id)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_access_leaderboard(self):
        request = self.factory.get(f"/course/{self.course.id}/leaderboard/")
        request.user = self.other_user
        response = course_leaderboard(request, course_id=self.course.id)
        self.assertEqual(response.status_code, 403)

    def test_non_participant_cannot_access_leaderboard(self):
        request = self.factory.get(f"/course/{self.course.id}/leaderboard/")
        request.user = self.other_user
        response = course_leaderboard(request, course_id=self.course.id)
        self.assertEqual(response.status_code, 403)

    def test_invalid_method_returns_405(self):
        request = self.factory.post(f"/course/{self.course.id}/leaderboard/")
        request.user = self.teacher
        response = course_leaderboard(request, course_id=self.course.id)
        self.assertEqual(response.status_code, 405)

    def test_nonexistent_course_returns_404(self):
        from django.http import Http404
        request = self.factory.get("/course/99999/leaderboard/")
        request.user = self.teacher
        with self.assertRaises(Http404):
            course_leaderboard(request, course_id=99999)

    def test_open_course_visible_to_any_authenticated(self):
        self.course.is_open = True
        self.course.save()

        request = self.factory.get(f"/course/{self.course.id}/leaderboard/")
        request.user = self.other_user
        response = course_leaderboard(request, course_id=self.course.id)
        self.assertEqual(response.status_code, 200)

    def test_response_contains_correct_structure(self):
        contest = Contest.objects.create(
            title="Test Contest",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )
        contest.problems.add(self.problem)

        request = self.factory.get(f"/course/{self.course.id}/leaderboard/")
        request.user = self.teacher
        response = course_leaderboard(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())

        self.assertIn("course_id", data)
        self.assertIn("course_title", data)
        self.assertIn("contests", data)
        self.assertIn("entries", data)

        self.assertEqual(data["course_id"], self.course.id)
        self.assertEqual(data["course_title"], "View Test Course")
        self.assertIsInstance(data["contests"], list)
        self.assertIsInstance(data["entries"], list)
