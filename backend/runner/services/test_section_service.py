from django.contrib.auth import get_user_model
from django.test import TestCase

from runner.models import Section
from runner.services.section_service import SectionCreateInput, create_section

User = get_user_model()


class SectionServiceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="root-owner", password="pass")
        self.root = Section.objects.filter(title="Авторское", parent__isnull=True).first()
        if self.root is None:
            self.root = create_section(
                SectionCreateInput(title="Авторское", owner=self.owner)
            )

    def test_other_owner_can_create_section_under_root(self):
        other_owner = User.objects.create_user(username="other-owner", password="pass")
        section = create_section(
            SectionCreateInput(title="Child", owner=other_owner, parent=self.root)
        )

        self.assertEqual(section.owner, other_owner)
        self.assertEqual(section.parent, self.root)

    def test_non_owner_cannot_create_under_foreign_section(self):
        child = create_section(
            SectionCreateInput(title="Owned", owner=self.owner, parent=self.root)
        )
        other_owner = User.objects.create_user(username="other-owner-2", password="pass")

        with self.assertRaises(ValueError):
            create_section(
                SectionCreateInput(title="Forbidden", owner=other_owner, parent=child)
            )
