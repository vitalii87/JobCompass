from __future__ import annotations

import unittest

from app.i18n import get_language, set_language, translate


class I18nTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_language("uk")

    def test_static_and_dynamic_ukrainian_text_translates_to_english(self) -> None:
        set_language("en")

        self.assertEqual(translate("Пошук вакансій"), "Job search")
        self.assertEqual(translate("Вакансій у списку: 12"), "Jobs in list: 12")

    def test_interface_can_switch_back_to_ukrainian(self) -> None:
        set_language("uk")

        self.assertEqual(translate("Job search"), "Пошук вакансій")
        self.assertEqual(get_language(), "uk")

    def test_unknown_candidate_content_is_not_modified(self) -> None:
        set_language("en")

        self.assertEqual(translate("Anna Zhyliayeva"), "Anna Zhyliayeva")
        self.assertEqual(translate("Köngen"), "Köngen")

    def test_brand_and_free_form_text_are_not_changed_by_partial_words(self) -> None:
        set_language("uk")

        self.assertEqual(translate("JobCompass"), "JobCompass")
        self.assertEqual(translate("Senior Job Search Specialist"), "Senior Job Search Specialist")


if __name__ == "__main__":
    unittest.main()
