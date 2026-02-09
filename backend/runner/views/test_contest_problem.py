import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from runner.models import Contest, Course, CourseParticipant, Problem, Section
from runner.services.section_service import SectionCreateInput, create_section
from runner.views.contest_draft import add_problem_to_contest, remove_problem_from_contest

User = get_user_model()


class AddProblemToContestViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Owner Section",
                owner=self.owner,
                parent=self.root_section,
            )
        )
        self.course = Course.objects.create(
            title="Course A",
            owner=self.owner,
            section=self.section,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseParticipant.Role.TEACHER,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.student,
            role=CourseParticipant.Role.STUDENT,
        )
        self.contest = Contest.objects.create(
            title="Contest 1",
            course=self.course,
            created_by=self.owner,
        )
        self.problem = Problem.objects.create(
            title="Simple Sum",
            statement="Solve A+B",
        )

    def test_owner_can_add_problem(self):
        request = self.factory.post(
            "/",
            data=json.dumps({"problem_id": self.problem.id}),
            content_type="application/json",
        )
        request.user = self.owner

        response = add_problem_to_contest.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 201)
        payload = json.loads(response.content.decode())
        self.assertTrue(payload["added"])
        self.assertEqual(payload["contest"], self.contest.id)
        self.assertEqual(payload["problem"]["id"], self.problem.id)
        self.assertEqual(payload["problems_count"], 1)
        self.assertTrue(self.contest.problems.filter(pk=self.problem.id).exists())

    def test_second_addition_returns_200(self):
        self.contest.problems.add(self.problem)
        request = self.factory.post(
            "/",
            data=json.dumps({"problem_id": self.problem.id}),
            content_type="application/json",
        )
        request.user = self.owner

        response = add_problem_to_contest.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertFalse(payload["added"])
        self.assertEqual(payload["problems_count"], 1)

    def test_student_cannot_add_problem(self):
        request = self.factory.post(
            "/",
            data=json.dumps({"problem_id": self.problem.id}),
            content_type="application/json",
        )
        request.user = self.student

        response = add_problem_to_contest.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.contest.problems.exists())

    def test_missing_problem_id_returns_bad_request(self):
        request = self.factory.post("/", data=json.dumps({}), content_type="application/json")
        request.user = self.owner

        response = add_problem_to_contest.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content.decode())
        self.assertIn("problem_id", payload["detail"])


class RemoveProblemFromContestViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(username="owner2", password="pass")
        self.teacher = User.objects.create_user(username="teacher2", password="pass")
        self.student = User.objects.create_user(username="student2", password="pass")
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Owner Section 2",
                owner=self.owner,
                parent=self.root_section,
            )
        )
        self.course = Course.objects.create(
            title="Course B",
            owner=self.owner,
            section=self.section,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseParticipant.Role.TEACHER,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.student,
            role=CourseParticipant.Role.STUDENT,
        )
        self.contest = Contest.objects.create(
            title="Contest 2",
            course=self.course,
            created_by=self.owner,
        )
        self.problem1 = Problem.objects.create(title="P1", statement="...")
        self.problem2 = Problem.objects.create(title="P2", statement="...")
        self.contest.problems.add(self.problem1, self.problem2)

    def test_teacher_can_remove_problem(self):
        request = self.factory.post(
            "/",
            data=json.dumps({"problem_id": self.problem1.id}),
            content_type="application/json",
        )
        request.user = self.teacher

        response = remove_problem_from_contest.__wrapped__(request, contest_id=self.contest.id)
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["contest"], self.contest.id)
        self.assertIn(self.problem1.id, payload["removed_ids"])
        self.assertEqual(payload["problems_count"], 1)
        self.assertFalse(self.contest.problems.filter(pk=self.problem1.id).exists())

    def test_student_cannot_remove_problem(self):
        request = self.factory.post(
            "/",
            data=json.dumps({"problem_id": self.problem1.id}),
            content_type="application/json",
        )
        request.user = self.student

        response = remove_problem_from_contest.__wrapped__(request, contest_id=self.contest.id)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.contest.problems.filter(pk=self.problem1.id).exists())
