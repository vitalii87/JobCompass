from __future__ import annotations

import unittest

from app.i18n import (
    get_language,
    language_from_label,
    language_label,
    normalize_language,
    set_language,
    translate,
)


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
        self.assertEqual(
            translate("Senior Job Search Specialist"),
            "Senior Job Search Specialist",
        )

    def test_result_details_and_view_state_have_english_labels(self) -> None:
        set_language("en")

        self.assertEqual(translate("Опис:"), "Description:")
        self.assertEqual(
            translate("Докази з тексту вакансії:"),
            "Evidence from the job description:",
        )
        self.assertEqual(translate("Переглянуто"), "Viewed")

    def test_static_and_dynamic_text_translates_to_german(self) -> None:
        set_language("de")

        self.assertEqual(translate("Пошук вакансій"), "Stellensuche")
        self.assertEqual(
            translate("Jobs in list: 12"),
            "Stellen in der Liste: 12",
        )
        self.assertEqual(translate("Опис:"), "Beschreibung:")
        self.assertEqual(translate("Viewed"), "Angesehen")
        self.assertEqual(
            translate("Скопіювати лист і відкрити вакансію"),
            "Anschreiben kopieren und Stelle öffnen",
        )

    def test_interface_can_switch_from_german_to_ukrainian(self) -> None:
        set_language("de")
        self.assertEqual(translate("Job search"), "Stellensuche")

        set_language("uk")
        self.assertEqual(translate("Stellensuche"), "Пошук вакансій")

    def test_language_labels_are_localized_and_resolved(self) -> None:
        set_language("de")

        self.assertEqual(language_label("uk"), "Ukrainisch")
        self.assertEqual(language_label("en"), "Englisch")
        self.assertEqual(language_label("de"), "Deutsch")
        self.assertEqual(language_from_label("Німецька"), "de")
        self.assertEqual(language_from_label("German"), "de")
        self.assertEqual(language_from_label("Deutsch"), "de")
        self.assertEqual(normalize_language("de"), "de")

    def test_german_translation_preserves_candidate_and_job_content(self) -> None:
        set_language("de")

        self.assertEqual(translate("Anna Zhyliayeva"), "Anna Zhyliayeva")
        self.assertEqual(translate("Köngen"), "Köngen")
        self.assertEqual(
            translate("Senior Job Search Specialist"),
            "Senior Job Search Specialist",
        )

    def test_copy_action_and_copy_noun_have_distinct_german_forms(self) -> None:
        set_language("de")

        self.assertEqual(translate("Копіювати"), "Kopieren")
        self.assertEqual(translate("Копія"), "Kopie")
        self.assertEqual(translate("Kopieren"), "Kopieren")

    def test_career_site_settings_are_translated(self) -> None:
        set_language("en")
        self.assertEqual(
            translate("Career-сайти компаній"), "Company career sites"
        )

        set_language("de")
        self.assertEqual(
            translate("Career-сайти компаній"),
            "Karriereseiten von Unternehmen",
        )
        self.assertEqual(
            translate("Personio career-сайти"), "Personio-Karriereseiten"
        )

    def test_simple_search_and_discovery_progress_are_translated(self) -> None:
        set_language("en")
        self.assertEqual(translate("Усі формати"), "All work modes")
        self.assertEqual(translate("Розширені → Джерела"), "Advanced → Sources")
        self.assertEqual(
            translate("Перевірено джерел: 4 · вакансій зібрано: 12"),
            "Sources checked: 4 · jobs collected: 12",
        )

        set_language("de")
        self.assertEqual(translate("Remote або hybrid"), "Remote oder Hybrid")
        self.assertEqual(
            translate("Відомих career-сайтів: 3"),
            "Bekannte Karriereseiten: 3",
        )

    def test_scheduled_retry_messages_are_translated(self) -> None:
        set_language("en")
        self.assertEqual(
            translate(
                "Автопошук не оновив результати; повтор через 30 хвилин. timeout"
            ),
            "Automatic search did not update results; retrying in 30 minutes. timeout",
        )

        set_language("de")
        self.assertEqual(
            translate("Запланований пошук ще не настав."),
            "Die geplante Suche ist noch nicht fällig.",
        )

    def test_update_download_fallback_is_translated(self) -> None:
        set_language("en")
        self.assertEqual(
            translate(
                "Не вдалося підключитися до GitHub після повторних спроб: closed"
            ),
            "Could not connect to GitHub after several attempts: closed",
        )

        set_language("de")
        self.assertEqual(
            translate(
                "\n\nАвтоматичне завантаження не вдалося. Відкрити сторінку релізу у браузері?"
            ),
            "\n\nDer automatische Download ist fehlgeschlagen. Release-Seite im Browser öffnen?",
        )


if __name__ == "__main__":
    unittest.main()
