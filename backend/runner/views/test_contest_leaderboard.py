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
from runner.views.contest_leaderboard import (
    build_contest_overall_leaderboard,
    build_contest_problem_leaderboards,
    contest_problem_leaderboard,
)

User = get_user_model()


class ContestLeaderboardViewTests(TestCase):
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
                title="Leaderboard Section",
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
        self.contest = Contest.objects.create(
            title="Contest 1",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )
        self.problem_rmse = Problem.objects.create(title="RMSE Task", statement="desc", rating=1000)
        self.problem_accuracy = Problem.objects.create(title="Accuracy Task", statement="desc", rating=1000)
        self.contest.problems.add(self.problem_rmse, self.problem_accuracy)
        ProblemDescriptor.objects.create(problem=self.problem_rmse, metric="rmse")
        ProblemDescriptor.objects.create(problem=self.problem_accuracy, metric="accuracy")

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

    def test_leaderboard_orders_and_includes_participants(self):
        sub_alice_rmse = self._create_submission(self.alice, self.problem_rmse, "rmse", 0.4)
        sub_bob_rmse = self._create_submission(self.bob, self.problem_rmse, "rmse", 0.2)
        Submission.objects.filter(pk=sub_alice_rmse.pk).update(
            submitted_at=timezone.now() - timedelta(hours=2)
        )
        Submission.objects.filter(pk=sub_bob_rmse.pk).update(
            submitted_at=timezone.now() - timedelta(hours=1)
        )

        sub_alice_acc = self._create_submission(self.alice, self.problem_accuracy, "accuracy", 0.9)
        sub_bob_acc = self._create_submission(self.bob, self.problem_accuracy, "accuracy", 0.9)
        Submission.objects.filter(pk=sub_alice_acc.pk).update(
            submitted_at=timezone.now() - timedelta(minutes=10)
        )
        Submission.objects.filter(pk=sub_bob_acc.pk).update(
            submitted_at=timezone.now() - timedelta(minutes=20)
        )

        request = self.factory.get("/")
        request.user = self.teacher
        response = contest_problem_leaderboard.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        leaderboards = {lb["problem_id"]: lb for lb in payload["leaderboards"]}

        rmse_board = leaderboards[self.problem_rmse.id]
        self.assertTrue(rmse_board["lower_is_better"])
        rmse_entries = rmse_board["entries"]
        rmse_user_ids = {entry["user_id"] for entry in rmse_entries}
        self.assertEqual(
            rmse_user_ids,
            {self.teacher.id, self.alice.id, self.bob.id, self.charlie.id},
        )
        bob_entry = next(entry for entry in rmse_entries if entry["user_id"] == self.bob.id)
        alice_entry = next(entry for entry in rmse_entries if entry["user_id"] == self.alice.id)
        charlie_entry = next(entry for entry in rmse_entries if entry["user_id"] == self.charlie.id)
        self.assertEqual(bob_entry["rank"], 1)
        self.assertEqual(alice_entry["rank"], 2)
        self.assertIsNone(charlie_entry["best_metric"])
        self.assertIsNone(charlie_entry["rank"])

        acc_board = leaderboards[self.problem_accuracy.id]
        self.assertFalse(acc_board["lower_is_better"])
        acc_entries = acc_board["entries"]
        bob_index = next(i for i, entry in enumerate(acc_entries) if entry["user_id"] == self.bob.id)
        alice_index = next(i for i, entry in enumerate(acc_entries) if entry["user_id"] == self.alice.id)
        self.assertLess(bob_index, alice_index)
        self.assertEqual(acc_entries[bob_index]["rank"], 1)
        self.assertEqual(acc_entries[alice_index]["rank"], 1)

    def test_private_contest_includes_allowed_participants_only(self):
        private_contest = Contest.objects.create(
            title="Private Contest",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
            access_type=Contest.AccessType.PRIVATE,
        )
        private_contest.allowed_participants.add(self.bob)
        private_contest.problems.add(self.problem_rmse)

        leaderboards = build_contest_problem_leaderboards(private_contest)
        entries = leaderboards[0]["entries"]
        user_ids = {entry["user_id"] for entry in entries}
        self.assertEqual(user_ids, {self.bob.id})

    def test_overall_leaderboard_ioi_scores(self):
        self._create_submission(self.alice, self.problem_rmse, "rmse", 0.4)
        self._create_submission(self.bob, self.problem_rmse, "rmse", 0.2)
        self._create_submission(self.alice, self.problem_accuracy, "accuracy", 0.9)
        self._create_submission(self.bob, self.problem_accuracy, "accuracy", 0.9)

        overall = build_contest_overall_leaderboard(self.contest)
        entries = {entry["user_id"]: entry for entry in overall["entries"]}

        self.assertEqual(entries[self.bob.id]["rank"], 1)
        self.assertEqual(entries[self.alice.id]["rank"], 2)
        self.assertIsNone(entries[self.charlie.id]["rank"])
        self.assertAlmostEqual(entries[self.bob.id]["total_score"], 0.7, places=6)
        self.assertAlmostEqual(entries[self.alice.id]["total_score"], 0.5, places=6)

    def test_overall_leaderboard_icpc_penalty(self):
        start_time = timezone.now() - timedelta(hours=2)
        icpc_contest = Contest.objects.create(
            title="ICPC Contest",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
            scoring=Contest.Scoring.ICPC,
            start_time=start_time,
        )
        icpc_contest.problems.add(self.problem_rmse, self.problem_accuracy)

        alice_fail = self._create_submission(
            self.alice,
            self.problem_rmse,
            "rmse",
            1.0,
            status=Submission.STATUS_FAILED,
        )
        alice_ok = self._create_submission(
            self.alice,
            self.problem_rmse,
            "rmse",
            0.5,
        )
        alice_second = self._create_submission(
            self.alice,
            self.problem_accuracy,
            "accuracy",
            0.8,
        )
        bob_ok = self._create_submission(
            self.bob,
            self.problem_rmse,
            "rmse",
            0.3,
        )

        Submission.objects.filter(pk=alice_fail.pk).update(
            submitted_at=start_time + timedelta(minutes=10)
        )
        Submission.objects.filter(pk=alice_ok.pk).update(
            submitted_at=start_time + timedelta(minutes=30)
        )
        Submission.objects.filter(pk=alice_second.pk).update(
            submitted_at=start_time + timedelta(minutes=70)
        )
        Submission.objects.filter(pk=bob_ok.pk).update(
            submitted_at=start_time + timedelta(minutes=20)
        )

        overall = build_contest_overall_leaderboard(icpc_contest)
        entries = {entry["user_id"]: entry for entry in overall["entries"]}

        self.assertEqual(entries[self.alice.id]["solved_count"], 2)
        self.assertEqual(entries[self.bob.id]["solved_count"], 1)
        self.assertEqual(entries[self.alice.id]["penalty_minutes"], 120)
        self.assertEqual(entries[self.bob.id]["penalty_minutes"], 20)
        self.assertEqual(entries[self.alice.id]["rank"], 1)
        self.assertEqual(entries[self.bob.id]["rank"], 2)
