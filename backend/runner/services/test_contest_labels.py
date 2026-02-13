from django.test import SimpleTestCase

from runner.services.contest_labels import contest_problem_label


class ContestProblemLabelTests(SimpleTestCase):
    def test_examples(self):
        self.assertEqual(contest_problem_label(0), "A")
        self.assertEqual(contest_problem_label(1), "B")
        self.assertEqual(contest_problem_label(25), "Z")
        self.assertEqual(contest_problem_label(26), "AA")
        self.assertEqual(contest_problem_label(27), "AB")

    def test_wraps_beyond_double_letters(self):
        self.assertEqual(contest_problem_label(51), "AZ")
        self.assertEqual(contest_problem_label(52), "BA")
        self.assertEqual(contest_problem_label(701), "ZZ")
        self.assertEqual(contest_problem_label(702), "AAA")

    def test_rejects_negative_index(self):
        with self.assertRaises(ValueError):
            contest_problem_label(-1)

    def test_rejects_non_integer_values(self):
        with self.assertRaises(TypeError):
            contest_problem_label(1.5)
        with self.assertRaises(TypeError):
            contest_problem_label(True)
