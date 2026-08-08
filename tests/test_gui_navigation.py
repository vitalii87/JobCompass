from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from app.core.models import JobPosting, MatchLevel, MatchResult, SubmissionMode
from app.core.search import RankedJob
from app.i18n import set_language
from app.interfaces.gui import JobCompassApp, SubmissionReviewDialog


class _FakeButton:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.invocations = 0

    def instate(self, _states: tuple[str, ...]) -> bool:
        return self.enabled

    def invoke(self) -> None:
        self.invocations += 1


class _FakeCanvas:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def yview_moveto(self, fraction: float) -> None:
        self.calls.append(("move", fraction))

    def yview_scroll(self, amount: int, units: str) -> None:
        self.calls.append(("scroll", amount, units))


class _FakeVariable:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class _FakeWidget:
    def __init__(self) -> None:
        self.options: dict[str, object] = {}
        self.content = ""

    def configure(self, **kwargs: object) -> None:
        self.options.update(kwargs)

    def get_children(self) -> tuple[object, ...]:
        return ()

    def delete(self, *_args: object) -> None:
        self.content = ""

    def insert(self, _position: str, value: str) -> None:
        self.content = value


class _FakeNotebook:
    def __init__(self) -> None:
        self.text = ""

    def tab(self, _tab: object, *, text: str) -> None:
        self.text = text


class GuiNavigationTests(unittest.TestCase):
    def test_submission_action_explains_clipboard_and_browser_behavior(self) -> None:
        self.assertEqual(
            SubmissionReviewDialog._action_label(SubmissionMode.ASSISTED, True),
            "Скопіювати лист і відкрити вакансію",
        )
        self.assertEqual(
            SubmissionReviewDialog._action_label(SubmissionMode.MANUAL, True),
            "Відкрити вакансію",
        )
        self.assertEqual(
            SubmissionReviewDialog._action_label(SubmissionMode.ASSISTED, False),
            "Відкрити вакансію",
        )

    def tearDown(self) -> None:
        set_language("uk")

    def test_enter_invokes_enabled_focused_button(self) -> None:
        button = _FakeButton()

        result = JobCompassApp._invoke_focused_button(
            SimpleNamespace(widget=button)
        )

        self.assertEqual(result, "break")
        self.assertEqual(button.invocations, 1)

    def test_keyboard_scroll_supports_arrows_pages_and_edges(self) -> None:
        app = object.__new__(JobCompassApp)
        app.search_canvas = _FakeCanvas()

        for keysym in ("Down", "Prior", "End", "Home"):
            app._scroll_search_with_keyboard(SimpleNamespace(keysym=keysym))

        self.assertEqual(
            app.search_canvas.calls,
            [
                ("scroll", 1, "units"),
                ("scroll", -1, "pages"),
                ("move", 1.0),
                ("move", 0.0),
            ],
        )

    def test_freshness_sort_keeps_jobs_without_date_at_the_end(self) -> None:
        app = object.__new__(JobCompassApp)
        app.result_sort_var = _FakeVariable("Найновіші спочатку")

        def ranked(external_id: str, day: int | None) -> RankedJob:
            published_at = (
                datetime(2026, 8, day, tzinfo=timezone.utc)
                if day is not None
                else None
            )
            job = JobPosting(
                source="test",
                external_id=external_id,
                title=external_id,
                company="Company",
                published_at=published_at,
            )
            match = MatchResult(
                job_id=job.job_id,
                score=50,
                level=MatchLevel.PARTIAL,
            )
            return RankedJob(job=job, match=match)

        app.ranked_jobs = [ranked("unknown", None), ranked("old", 1), ranked("new", 5)]

        self.assertEqual(
            [item.job.external_id for item in app._ordered_results()],
            ["new", "old", "unknown"],
        )

    def test_view_label_keeps_date_for_opened_job(self) -> None:
        self.assertEqual(JobCompassApp._job_view_label(None), "Нова")
        expected = datetime.fromisoformat(
            "2026-08-06T20:15:00+00:00"
        ).astimezone().strftime("%d.%m.%Y %H:%M")
        self.assertEqual(
            JobCompassApp._job_view_label("2026-08-06T20:15:00+00:00"),
            f"Переглянуто · {expected}",
        )

    def test_guest_profile_label_refreshes_in_selected_language(self) -> None:
        set_language("en")
        app = object.__new__(JobCompassApp)
        app.store = SimpleNamespace(
            list_profiles=lambda: [],
            active_profile_id=None,
        )
        app.profile_selector = _FakeWidget()
        app.profile_selector_var = _FakeVariable("")

        app._refresh_profile_selector()

        self.assertEqual(
            app.profile_selector.options["values"],
            ("Guest mode (not saved)",),
        )
        self.assertEqual(app.profile_selector_var.get(), "Guest mode (not saved)")

    def test_scheduled_tab_counter_refreshes_in_selected_language(self) -> None:
        set_language("de")
        app = object.__new__(JobCompassApp)
        app.unseen_tree = _FakeWidget()
        app.store = SimpleNamespace(list_scheduled_jobs=lambda: [])
        app.notebook = _FakeNotebook()
        app.schedule_tab = object()

        app._refresh_unseen_jobs()

        self.assertEqual(app.notebook.text, "Zeitplan (0)")

    def test_empty_results_message_refreshes_in_selected_language(self) -> None:
        set_language("en")
        app = object.__new__(JobCompassApp)
        app.results_tree = _FakeWidget()
        app.results_count_var = _FakeVariable("")
        app.ranked_jobs = []
        app.store = SimpleNamespace(
            list_applications=lambda: [],
            list_discovered_jobs=lambda: [],
        )
        app.result_sort_var = _FakeVariable("By relevance")
        app.result_details = _FakeWidget()
        app.empty_results_message = (
            "Немає вакансій, що відповідають вибраним фільтрам."
        )

        app._render_results()

        self.assertEqual(
            app.result_details.content,
            "No jobs match the selected filters.",
        )


if __name__ == "__main__":
    unittest.main()
