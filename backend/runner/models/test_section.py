from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from runner.models import Course, Section

User = get_user_model()


class SectionModelTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", is_staff=True
        )
        self.course = Course.objects.create(title="Course A", owner=self.teacher)

    def test_section_creation(self):
        section = Section.objects.create(
            title="Section 1",
            description="Test description",
            owner=self.teacher,
        )
        self.assertEqual(section.title, "Section 1")
        self.assertEqual(section.owner, self.teacher)
        self.assertIsNone(section.parent)

    def test_section_with_parent(self):
        parent = Section.objects.create(title="Parent", owner=self.teacher)
        child = Section.objects.create(title="Child", parent=parent, owner=self.teacher)

        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())

    def test_section_cannot_be_own_parent(self):
        section = Section.objects.create(title="Section", owner=self.teacher)
        section.parent = section

        with self.assertRaises(ValidationError) as ctx:
            section.full_clean()

        self.assertIn("own parent", str(ctx.exception))

    def test_circular_hierarchy_prevented(self):
        s1 = Section.objects.create(title="S1", owner=self.teacher)
        s2 = Section.objects.create(title="S2", parent=s1, owner=self.teacher)
        s3 = Section.objects.create(title="S3", parent=s2, owner=self.teacher)

        # Try to make s1's parent be s3 (creates cycle: s1 -> s3 -> s2 -> s1)
        s1.parent = s3

        with self.assertRaises(ValidationError) as ctx:
            s1.full_clean()

        self.assertIn("hierarchy", str(ctx.exception).lower())

    def test_section_can_have_courses(self):
        section = Section.objects.create(title="Section", owner=self.teacher)
        section.courses.add(self.course)

        self.assertTrue(section.has_courses())
        self.assertFalse(section.has_child_sections())
        self.assertIn(self.course, section.courses.all())

    def test_section_can_have_child_sections(self):
        parent = Section.objects.create(title="Parent", owner=self.teacher)
        Section.objects.create(title="Child", parent=parent, owner=self.teacher)

        self.assertTrue(parent.has_child_sections())
        self.assertFalse(parent.has_courses())

    def test_can_add_course_true_when_no_children(self):
        section = Section.objects.create(title="Section", owner=self.teacher)
        self.assertTrue(section.can_add_course())

    def test_can_add_course_false_when_has_children(self):
        parent = Section.objects.create(title="Parent", owner=self.teacher)
        Section.objects.create(title="Child", parent=parent, owner=self.teacher)

        self.assertFalse(parent.can_add_course())

    def test_can_add_child_section_true_when_no_courses(self):
        section = Section.objects.create(title="Section", owner=self.teacher)
        self.assertTrue(section.can_add_child_section())

    def test_can_add_child_section_false_when_has_courses(self):
        section = Section.objects.create(title="Section", owner=self.teacher)
        section.courses.add(self.course)

        self.assertFalse(section.can_add_child_section())

    def test_add_course_raises_when_has_children(self):
        parent = Section.objects.create(title="Parent", owner=self.teacher)
        Section.objects.create(title="Child", parent=parent, owner=self.teacher)

        with self.assertRaises(ValidationError) as ctx:
            parent.add_course(self.course)

        self.assertIn("child sections", str(ctx.exception))

    def test_add_child_section_raises_when_has_courses(self):
        section = Section.objects.create(title="Section", owner=self.teacher)
        section.courses.add(self.course)

        child = Section(title="Child", owner=self.teacher)

        with self.assertRaises(ValidationError) as ctx:
            section.add_child_section(child)

        self.assertIn("courses", str(ctx.exception))

    def test_section_ordering(self):
        s1 = Section.objects.create(title="S1", owner=self.teacher, order=2)
        s2 = Section.objects.create(title="S2", owner=self.teacher, order=1)
        s3 = Section.objects.create(title="S3", owner=self.teacher, order=0)

        sections = list(Section.objects.all())
        self.assertEqual(sections[0], s3)
        self.assertEqual(sections[1], s2)
        self.assertEqual(sections[2], s1)
