from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
import json

from runner.models import FavoriteCourse, Section, SiteUpdate
from runner.services.course_service import CourseCreateInput, create_course
from runner.services.section_service import SectionCreateInput, create_section

User = get_user_model()


class HomeSidebarTests(TestCase):
    def setUp(self):
        self.url = reverse("home-sidebar")

    def test_unauthenticated_gets_empty_payload(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["favorites"], [])
        self.assertEqual(payload["recent_problems"], [])
        self.assertEqual(payload["updates"], [])

    def test_returns_published_updates(self):
        user = User.objects.create_user(username="u", password="pass")
        SiteUpdate.objects.create(title="A", body="1", is_published=True)
        SiteUpdate.objects.create(title="B", body="2", is_published=False)
        self.client.login(username="u", password="pass")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        titles = [x["title"] for x in payload["updates"]]
        self.assertIn("A", titles)
        self.assertNotIn("B", titles)


class FavoriteCoursesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass")
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(title="S", owner=self.owner, parent=self.root_section)
        )
        self.courses = [
            create_course(
                CourseCreateInput(
                    title=f"C{i}",
                    owner=self.owner,
                    is_open=True,
                    section=self.section,
                )
            )
            for i in range(1, 7)
        ]
        self.add_url = reverse("favorite-courses-add")
        self.remove_url = reverse("favorite-courses-remove")
        self.reorder_url = reverse("favorite-courses-reorder")

    def test_add_enforces_limit(self):
        self.client.login(username="u", password="pass")
        for course in self.courses[:5]:
            resp = self.client.post(self.add_url, data={"course_id": course.id})
            self.assertIn(resp.status_code, (200, 201))
        resp = self.client.post(self.add_url, data={"course_id": self.courses[5].id})
        self.assertEqual(resp.status_code, 400)

    def test_reorder_updates_positions(self):
        self.client.login(username="u", password="pass")
        for course in self.courses[:3]:
            self.client.post(self.add_url, data={"course_id": course.id})

        resp = self.client.post(
            self.reorder_url,
            data=json.dumps({"course_ids": [self.courses[2].id, self.courses[0].id]}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        favs = list(
            FavoriteCourse.objects.filter(user=self.user).order_by("position", "id")
        )
        self.assertEqual([f.course_id for f in favs], [self.courses[2].id, self.courses[0].id, self.courses[1].id])

    def test_remove_repacks_positions(self):
        self.client.login(username="u", password="pass")
        for course in self.courses[:3]:
            self.client.post(self.add_url, data={"course_id": course.id})

        resp = self.client.post(self.remove_url, data={"course_id": self.courses[1].id})
        self.assertEqual(resp.status_code, 200)
        favs = list(
            FavoriteCourse.objects.filter(user=self.user).order_by("position", "id")
        )
        self.assertEqual([f.position for f in favs], [0, 1])
