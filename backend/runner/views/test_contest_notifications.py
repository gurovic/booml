import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from runner.models import Contest, Course, CourseParticipant, Section
from runner.services.section_service import SectionCreateInput, create_section
from runner.views.contest_notifications import (
    answer_contest_question,
    ask_contest_question,
    contest_notifications,
    mark_contest_notifications_read,
    send_contest_notification,
)

User = get_user_model()


class ContestNotificationsViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.teacher = User.objects.create_user(username="teacher_notifications", password="pass")
        self.student_1 = User.objects.create_user(username="student_notifications_1", password="pass")
        self.student_2 = User.objects.create_user(username="student_notifications_2", password="pass")
        self.outsider = User.objects.create_user(username="outsider_notifications", password="pass")

        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Contest notifications section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
        self.course = Course.objects.create(
            title="Contest notifications course",
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
            user=self.student_1,
            role=CourseParticipant.Role.STUDENT,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.student_2,
            role=CourseParticipant.Role.STUDENT,
        )

        self.contest = Contest.objects.create(
            title="Contest notifications",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )

    def _post_json(self, view, user, payload, **kwargs):
        request = self.factory.post(
            "/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = user
        return view.__wrapped__(request, **kwargs)

    def _get(self, view, user, query_string="", **kwargs):
        request = self.factory.get(f"/{query_string}")
        request.user = user
        return view(request, **kwargs)

    def test_teacher_can_send_announcement_to_all_participants(self):
        with patch("runner.views.contest_notifications.broadcast_contest_notification") as mocked_broadcast:
            response = self._post_json(
                send_contest_notification,
                self.teacher,
                {"text": "Важное объявление", "audience": "all"},
                contest_id=self.contest.id,
            )

        self.assertEqual(response.status_code, 201)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["notification"]["kind"], "announcement")
        self.assertEqual(payload["notification"]["recipient_count"], 2)
        mocked_broadcast.assert_called_once()

        student_response = self._get(
            contest_notifications,
            self.student_1,
            contest_id=self.contest.id,
        )
        self.assertEqual(student_response.status_code, 200)
        student_payload = json.loads(student_response.content.decode())
        self.assertEqual(student_payload["unread_count"], 1)
        self.assertEqual(len(student_payload["items"]), 1)
        self.assertEqual(student_payload["items"][0]["text"], "Важное объявление")

    def test_teacher_can_send_announcement_to_selected_participants(self):
        self._post_json(
            send_contest_notification,
            self.teacher,
            {
                "text": "Сообщение только одному ученику",
                "audience": "selected",
                "recipient_ids": [self.student_1.id],
            },
            contest_id=self.contest.id,
        )

        payload_1 = json.loads(
            self._get(contest_notifications, self.student_1, contest_id=self.contest.id).content.decode()
        )
        payload_2 = json.loads(
            self._get(contest_notifications, self.student_2, contest_id=self.contest.id).content.decode()
        )
        self.assertEqual(payload_1["unread_count"], 1)
        self.assertEqual(len(payload_1["items"]), 1)
        self.assertEqual(payload_2["unread_count"], 0)
        self.assertEqual(len(payload_2["items"]), 0)

    def test_student_question_and_teacher_answer_flow(self):
        ask_response = self._post_json(
            ask_contest_question,
            self.student_1,
            {"text": "Подскажите, какой формат файла нужен?"},
            contest_id=self.contest.id,
        )
        self.assertEqual(ask_response.status_code, 201)
        ask_payload = json.loads(ask_response.content.decode())
        question_id = ask_payload["notification"]["id"]

        teacher_payload = json.loads(
            self._get(contest_notifications, self.teacher, contest_id=self.contest.id).content.decode()
        )
        self.assertEqual(teacher_payload["unread_count"], 1)
        self.assertEqual(teacher_payload["items"][0]["kind"], "question")
        self.assertEqual(teacher_payload["items"][0]["id"], question_id)

        answer_response = self._post_json(
            answer_contest_question,
            self.teacher,
            {"text": "Нужен CSV c колонками id,pred."},
            contest_id=self.contest.id,
            notification_id=question_id,
        )
        self.assertEqual(answer_response.status_code, 201)

        student_payload = json.loads(
            self._get(contest_notifications, self.student_1, contest_id=self.contest.id).content.decode()
        )
        kinds = [item["kind"] for item in student_payload["items"]]
        self.assertIn("question", kinds)
        self.assertIn("answer", kinds)
        self.assertEqual(student_payload["unread_count"], 1)

        read_response = self._post_json(
            mark_contest_notifications_read,
            self.student_1,
            {},
            contest_id=self.contest.id,
        )
        self.assertEqual(read_response.status_code, 200)
        read_payload = json.loads(read_response.content.decode())
        self.assertEqual(read_payload["unread_count"], 0)

    def test_student_cannot_send_teacher_announcement(self):
        response = self._post_json(
            send_contest_notification,
            self.student_1,
            {"text": "Я не должен это отправить", "audience": "all"},
            contest_id=self.contest.id,
        )
        self.assertEqual(response.status_code, 403)

    def test_outsider_cannot_read_contest_notifications(self):
        response = self._get(
            contest_notifications,
            self.outsider,
            contest_id=self.contest.id,
        )
        self.assertEqual(response.status_code, 403)

    def test_questions_are_hidden_and_blocked_when_disabled(self):
        ask_response = self._post_json(
            ask_contest_question,
            self.student_1,
            {"text": "Вопрос до отключения"},
            contest_id=self.contest.id,
        )
        self.assertEqual(ask_response.status_code, 201)

        self.contest.allow_student_questions = False
        self.contest.save(update_fields=["allow_student_questions"])

        blocked_ask = self._post_json(
            ask_contest_question,
            self.student_1,
            {"text": "Вопрос после отключения"},
            contest_id=self.contest.id,
        )
        self.assertEqual(blocked_ask.status_code, 403)

        question_id = json.loads(ask_response.content.decode())["notification"]["id"]
        blocked_answer = self._post_json(
            answer_contest_question,
            self.teacher,
            {"text": "Ответ после отключения"},
            contest_id=self.contest.id,
            notification_id=question_id,
        )
        self.assertEqual(blocked_answer.status_code, 403)

        self._post_json(
            send_contest_notification,
            self.teacher,
            {"text": "Только объявление", "audience": "all"},
            contest_id=self.contest.id,
        )

        teacher_payload = json.loads(
            self._get(contest_notifications, self.teacher, contest_id=self.contest.id).content.decode()
        )
        student_payload = json.loads(
            self._get(contest_notifications, self.student_1, contest_id=self.contest.id).content.decode()
        )

        self.assertFalse(teacher_payload["questions_enabled"])
        self.assertFalse(student_payload["questions_enabled"])
        self.assertTrue(teacher_payload["notifications_enabled"])
        self.assertTrue(student_payload["notifications_enabled"])
        self.assertEqual([item["kind"] for item in teacher_payload["items"]], ["announcement"])
        self.assertEqual([item["kind"] for item in student_payload["items"]], ["announcement"])

    def test_notifications_can_be_disabled_and_all_notification_actions_are_blocked(self):
        self._post_json(
            send_contest_notification,
            self.teacher,
            {"text": "Старое объявление", "audience": "all"},
            contest_id=self.contest.id,
        )

        self.contest.allow_notifications = False
        self.contest.allow_student_questions = True
        self.contest.save(update_fields=["allow_notifications", "allow_student_questions"])

        teacher_payload = json.loads(
            self._get(contest_notifications, self.teacher, contest_id=self.contest.id).content.decode()
        )
        student_payload = json.loads(
            self._get(contest_notifications, self.student_1, contest_id=self.contest.id).content.decode()
        )

        self.assertFalse(teacher_payload["notifications_enabled"])
        self.assertFalse(student_payload["notifications_enabled"])
        self.assertFalse(teacher_payload["questions_enabled"])
        self.assertFalse(student_payload["questions_enabled"])
        self.assertEqual(teacher_payload["items"], [])
        self.assertEqual(student_payload["items"], [])

        send_response = self._post_json(
            send_contest_notification,
            self.teacher,
            {"text": "Новое объявление", "audience": "all"},
            contest_id=self.contest.id,
        )
        self.assertEqual(send_response.status_code, 403)

        ask_response = self._post_json(
            ask_contest_question,
            self.student_1,
            {"text": "Можно вопрос?"},
            contest_id=self.contest.id,
        )
        self.assertEqual(ask_response.status_code, 403)
