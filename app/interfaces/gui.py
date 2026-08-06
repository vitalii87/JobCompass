"""Tkinter desktop interface for the local JobCompass application."""

from __future__ import annotations

import webbrowser
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from tkinter import (
    BooleanVar,
    Canvas,
    DoubleVar,
    END,
    Listbox,
    Menu,
    StringVar,
    Text,
    Tk,
    Toplevel,
    filedialog,
    messagebox,
)
from tkinter import ttk

from app.core.deduplication import deduplicate_jobs
from app.core.models import (
    ApplicationStatus,
    CandidateProfile,
    CoverLetterPreparation,
    JobPosting,
)
from app.core.location import LocationSelection
from app.core.paths import default_data_path
from app.core.search import RankedJob, SearchFilters, search_jobs
from app.services import (
    build_ai_prompt,
    build_cover_letter_draft,
    build_evidence_summary,
    LocationGeocoder,
    load_resume,
    suggested_letter_language,
)
from app.sources import JsonFileSource, ONLINE_SOURCE_TYPES, SearchQuery
from app.storage import LocalJsonStore


DEFAULT_DATA_PATH = default_data_path()

_COMPONENT_LABELS = {
    "skills": "Навички",
    "role": "Професія",
    "experience": "Досвід",
    "languages": "Мови",
    "location": "Локація",
}

_WORK_MODE_LABELS = {
    "remote": "Remote",
    "hybrid": "Hybrid",
    "office": "Office",
    "unknown": "Не вказано",
}

_LETTER_TONES = {
    "Професійний": "professional",
    "Теплий і особистий": "warm",
    "Лаконічний": "concise",
}

_LETTER_LENGTHS = {
    "Короткий (140–180 слів)": "short",
    "Стандартний (180–250 слів)": "standard",
    "Розгорнутий (250–320 слів)": "detailed",
}

_LOCATION_COUNTRIES = {
    "Deutschland (DE)": "DE",
    "Österreich (AT)": "AT",
    "Schweiz (CH)": "CH",
    "Усі країни": "",
}

_RESULT_SORT_OPTIONS = {
    "За релевантністю": "relevance",
    "Найновіші спочатку": "newest",
    "Найстаріші спочатку": "oldest",
}


def _split_list(value: str) -> tuple[str, ...]:
    normalized = value.replace("\n", ",").replace(";", ",")
    return tuple(part.strip() for part in normalized.split(",") if part.strip())


class JobCompassApp:
    def __init__(self, root: Tk, data_path: str | Path = DEFAULT_DATA_PATH) -> None:
        self.root = root
        self.store = LocalJsonStore(data_path)
        self.store.initialize()
        self.profile = self.store.load_profile() or CandidateProfile()
        self.ranked_jobs: list[RankedJob] = []
        self.result_by_id: dict[str, RankedJob] = {}
        self.source_vars: dict[str, BooleanVar] = {}
        self.online_sources = {
            source_type.name: source_type() for source_type in ONLINE_SOURCE_TYPES
        }
        self.search_queue: Queue[object] = Queue()
        self.location_lookup_queue: Queue[object] = Queue()
        self.location_geocoder = LocationGeocoder()
        self.selected_locations: list[LocationSelection] = []
        self.location_suggestions: dict[str, LocationSelection] = {}
        self.location_lookup_after_id: str | None = None
        self.location_lookup_generation = 0
        self.location_lookup_polling = False
        self.search_running = False
        self.last_search_profile: CandidateProfile | None = None
        self.last_search_filters: SearchFilters | None = None
        self.last_search_jobs: list[JobPosting] = []
        self.last_location_prefiltered_job_ids: frozenset[str] = frozenset()
        self.source_diagnostics_prefix = "Джерела: пошук ще не запускався"
        self.empty_results_message = (
            "Немає вакансій, що відповідають вибраним фільтрам."
        )

        self.root.title("JobCompass")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(1180, max(760, screen_width - 80))
        window_height = min(760, max(500, screen_height - 120))
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(760, 500)
        self._configure_style()
        self._configure_clipboard_support()

        container = ttk.Frame(root, padding=12)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="JobCompass", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text="Локальний пошук, оцінювання та відстеження вакансій",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill="both", expand=True)
        self.profile_tab = ttk.Frame(self.notebook, padding=12)
        self.search_tab = ttk.Frame(self.notebook, padding=12)
        self.results_tab = ttk.Frame(self.notebook, padding=12)
        self.applications_tab = ttk.Frame(self.notebook, padding=12)
        self.settings_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.profile_tab, text="Профіль")
        self.notebook.add(self.search_tab, text="Пошук")
        self.notebook.add(self.results_tab, text="Результати")
        self.notebook.add(self.applications_tab, text="Мої заявки")
        self.notebook.add(self.settings_tab, text="Налаштування")

        self.status_var = StringVar(value="Готово")
        ttk.Label(container, textvariable=self.status_var, style="Status.TLabel").pack(
            fill="x", pady=(8, 0)
        )

        self._build_profile_tab()
        self._build_search_tab()
        self._build_results_tab()
        self._build_applications_tab()
        self._build_settings_tab()
        self._configure_keyboard_navigation()
        self._populate_profile(self.profile)
        self._refresh_sources()
        self._refresh_applications()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        available = style.theme_names()
        if "vista" in available:
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Heading.TLabel", font=("Segoe UI", 13, "bold"))
        style.configure("Status.TLabel", padding=6, relief="sunken")
        style.configure("Treeview", rowheight=26)
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))

    def _configure_clipboard_support(self) -> None:
        self.edit_menu = Menu(self.root, tearoff=False)
        self.edit_menu.add_command(
            label="Вирізати", command=lambda: self._clipboard_action("cut")
        )
        self.edit_menu.add_command(
            label="Копіювати", command=lambda: self._clipboard_action("copy")
        )
        self.edit_menu.add_command(
            label="Вставити", command=lambda: self._clipboard_action("paste")
        )
        self.edit_menu.add_separator()
        self.edit_menu.add_command(
            label="Виділити все", command=lambda: self._clipboard_action("select_all")
        )
        self.clipboard_widget: object | None = None
        self.root.bind_all("<Button-3>", self._show_edit_menu, add="+")
        self.root.bind_all(
            "<Control-KeyPress>", self._handle_layout_independent_shortcut, add="+"
        )

    @staticmethod
    def _is_text_widget(widget: object) -> bool:
        try:
            return widget.winfo_class() in {
                "Entry",
                "TEntry",
                "Text",
                "TCombobox",
                "Spinbox",
                "TSpinbox",
            }
        except AttributeError:
            return False

    @staticmethod
    def _widget_is_editable(widget: object) -> bool:
        try:
            return str(widget.cget("state")) not in {"disabled", "readonly"}
        except Exception:
            return True

    def _show_edit_menu(self, event: object) -> str | None:
        widget = getattr(event, "widget", None)
        if not self._is_text_widget(widget):
            return None
        self.clipboard_widget = widget
        try:
            widget.focus_set()
            editable = self._widget_is_editable(widget)
            self.edit_menu.entryconfigure("Вирізати", state="normal" if editable else "disabled")
            self.edit_menu.entryconfigure("Вставити", state="normal" if editable else "disabled")
            self.edit_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.edit_menu.grab_release()
        return "break"

    def _clipboard_action(self, action: str, widget: object | None = None) -> str:
        target = widget or self.clipboard_widget or self.root.focus_get()
        if not self._is_text_widget(target):
            return "break"
        if action in {"cut", "paste"} and not self._widget_is_editable(target):
            return "break"
        if action == "select_all":
            if target.winfo_class() == "Text":
                target.tag_add("sel", "1.0", "end-1c")
                target.mark_set("insert", "end-1c")
                target.see("insert")
            else:
                target.selection_range(0, END)
                target.icursor(END)
        else:
            target.event_generate(
                {"cut": "<<Cut>>", "copy": "<<Copy>>", "paste": "<<Paste>>"}[action]
            )
        return "break"

    def _handle_layout_independent_shortcut(self, event: object) -> str | None:
        widget = getattr(event, "widget", None)
        if not self._is_text_widget(widget):
            return None
        keysym = str(getattr(event, "keysym", "")).casefold()
        if keysym in {"a", "c", "v", "x"}:
            return None
        action = {
            65: "select_all",
            67: "copy",
            86: "paste",
            88: "cut",
        }.get(getattr(event, "keycode", None))
        return self._clipboard_action(action, widget) if action else None

    def _configure_keyboard_navigation(self) -> None:
        """Make the interface usable without a mouse."""
        self.notebook.enable_traversal()
        self.root.bind_class(
            "TButton", "<Return>", self._invoke_focused_button, add="+"
        )
        self.root.bind_class(
            "TButton", "<KP_Enter>", self._invoke_focused_button, add="+"
        )
        self.root.bind("<Control-Return>", self._run_search_from_keyboard, add="+")
        self.root.bind("<Control-KP_Enter>", self._run_search_from_keyboard, add="+")

    @staticmethod
    def _invoke_focused_button(event: object) -> str:
        button = getattr(event, "widget", None)
        try:
            if button.instate(("!disabled",)):
                button.invoke()
        except (AttributeError, RuntimeError):
            pass
        return "break"

    def _run_search_from_keyboard(self, _event: object) -> str:
        if self.notebook.select() == str(self.search_tab):
            self._run_search()
        return "break"

    def _update_search_scrollregion(self, _event: object | None = None) -> None:
        bounds = self.search_canvas.bbox("all")
        if bounds is not None:
            self.search_canvas.configure(scrollregion=bounds)

    def _resize_search_scroll_content(self, event: object) -> None:
        width = int(getattr(event, "width", self.search_canvas.winfo_width()))
        self.search_canvas.itemconfigure(self.search_canvas_window, width=width)
        self._update_search_scrollregion()

    def _pointer_is_over_search_form(self) -> bool:
        if self.notebook.select() != str(self.search_tab):
            return False
        pointer_x, pointer_y = self.root.winfo_pointerxy()
        left = self.search_canvas.winfo_rootx()
        top = self.search_canvas.winfo_rooty()
        return (
            left <= pointer_x < left + self.search_canvas.winfo_width()
            and top <= pointer_y < top + self.search_canvas.winfo_height()
        )

    def _scroll_search_with_mouse(self, event: object) -> str | None:
        if not self._pointer_is_over_search_form():
            return None
        delta = int(getattr(event, "delta", 0))
        if delta:
            steps = max(1, abs(delta) // 120)
            if delta > 0:
                steps = -steps
            self.search_canvas.yview_scroll(steps, "units")
            return "break"
        return None

    def _scroll_search_with_keyboard(self, event: object) -> str:
        keysym = str(getattr(event, "keysym", ""))
        if keysym == "Home":
            self.search_canvas.yview_moveto(0.0)
        elif keysym == "End":
            self.search_canvas.yview_moveto(1.0)
        elif keysym in {"Prior", "Next"}:
            self.search_canvas.yview_scroll(-1 if keysym == "Prior" else 1, "pages")
        else:
            self.search_canvas.yview_scroll(-1 if keysym == "Up" else 1, "units")
        return "break"

    def _bind_search_focus_scrolling(self, widget: object) -> None:
        """Keep controls reached with Tab inside the visible canvas area."""
        for child in widget.winfo_children():
            child.bind("<FocusIn>", self._show_focused_search_control, add="+")
            self._bind_search_focus_scrolling(child)

    def _show_focused_search_control(self, event: object) -> None:
        widget = getattr(event, "widget", None)
        bounds = self.search_canvas.bbox("all")
        if widget is None or bounds is None:
            return
        content_height = max(1, bounds[3] - bounds[1])
        viewport_height = self.search_canvas.winfo_height()
        visible_top = self.search_canvas.canvasy(0)
        visible_bottom = visible_top + viewport_height
        widget_top = widget.winfo_rooty() - self.search_content.winfo_rooty()
        widget_bottom = widget_top + widget.winfo_height()
        if widget_top < visible_top:
            self.search_canvas.yview_moveto(max(0.0, widget_top / content_height))
        elif widget_bottom > visible_bottom:
            destination = (widget_bottom - viewport_height) / content_height
            self.search_canvas.yview_moveto(min(1.0, max(0.0, destination)))

    def _build_profile_tab(self) -> None:
        self.profile_tab.columnconfigure(0, weight=1)
        self.profile_tab.columnconfigure(1, weight=1)
        self.profile_tab.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.profile_tab)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Label(toolbar, text="Профіль кандидата", style="Heading.TLabel").pack(
            side="left"
        )
        ttk.Button(
            toolbar,
            text="Завантажити резюме",
            command=self._load_resume,
            style="Primary.TButton",
        ).pack(side="right")
        ttk.Button(toolbar, text="Зберегти профіль", command=self._save_profile).pack(
            side="right", padx=(0, 8)
        )

        form = ttk.LabelFrame(
            self.profile_tab,
            text="Дані з резюме — усі поля необов’язкові",
            padding=12,
        )
        form.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        form.columnconfigure(1, weight=1)

        self.profile_vars = {
            "full_name": StringVar(),
            "email": StringVar(),
            "phone": StringVar(),
            "desired_roles": StringVar(),
            "skills": StringVar(),
            "languages": StringVar(),
            "years_experience": StringVar(),
            "preferred_locations": StringVar(),
        }
        labels = (
            ("full_name", "Ім’я"),
            ("email", "Email"),
            ("phone", "Телефон"),
            ("desired_roles", "Бажані професії"),
            ("skills", "Навички"),
            ("languages", "Мови"),
            ("years_experience", "Роки досвіду"),
            ("preferred_locations", "Бажані локації"),
        )
        for row, (field_name, label) in enumerate(labels):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(form, textvariable=self.profile_vars[field_name]).grid(
                row=row, column=1, sticky="ew", padx=(10, 0), pady=4
            )

        summary_row = len(labels)
        ttk.Label(form, text="Короткий профіль").grid(
            row=summary_row, column=0, sticky="nw", pady=4
        )
        self.summary_text = Text(form, height=6, wrap="word", font=("Segoe UI", 10))
        self.summary_text.grid(
            row=summary_row, column=1, sticky="nsew", padx=(10, 0), pady=4
        )
        form.rowconfigure(summary_row, weight=1)
        self.remote_only_var = BooleanVar(value=False)
        ttk.Checkbutton(
            form,
            text="Шукаю лише віддалену роботу",
            variable=self.remote_only_var,
        ).grid(row=summary_row + 1, column=1, sticky="w", padx=(10, 0), pady=4)

        preview = ttk.LabelFrame(
            self.profile_tab, text="Текст резюме — лише для перевірки", padding=12
        )
        preview.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(1, weight=1)
        self.resume_path_var = StringVar(value="Резюме ще не завантажено")
        ttk.Label(preview, textvariable=self.resume_path_var).grid(
            row=0, column=0, sticky="ew", pady=(0, 8)
        )
        self.resume_preview = Text(
            preview, wrap="word", font=("Consolas", 9), state="disabled"
        )
        preview_scroll = ttk.Scrollbar(
            preview, orient="vertical", command=self.resume_preview.yview
        )
        self.resume_preview.configure(yscrollcommand=preview_scroll.set)
        self.resume_preview.grid(row=1, column=0, sticky="nsew")
        preview_scroll.grid(row=1, column=1, sticky="ns")

    def _build_search_tab(self) -> None:
        self.search_tab.columnconfigure(0, weight=1)
        self.search_tab.rowconfigure(2, weight=1)

        header = ttk.Frame(self.search_tab)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(header, text="Пошук вакансій", style="Heading.TLabel").pack(
            side="left"
        )

        notice = ttk.Label(
            self.search_tab,
            text=(
                "JobCompass шукає актуальні вакансії у вибраних інтернет-джерелах, "
                "об’єднує дублікати та оцінює відповідність резюме."
            ),
            wraplength=900,
        )
        notice.grid(row=1, column=0, sticky="w", pady=(0, 10))

        scroll_host = ttk.Frame(self.search_tab)
        scroll_host.grid(row=2, column=0, sticky="nsew")
        scroll_host.columnconfigure(0, weight=1)
        scroll_host.rowconfigure(0, weight=1)

        self.search_canvas = Canvas(
            scroll_host,
            highlightthickness=0,
            borderwidth=0,
            takefocus=True,
        )
        self.search_canvas.grid(row=0, column=0, sticky="nsew")
        search_scrollbar = ttk.Scrollbar(
            scroll_host,
            orient="vertical",
            command=self.search_canvas.yview,
        )
        search_scrollbar.grid(row=0, column=1, sticky="ns")
        self.search_canvas.configure(yscrollcommand=search_scrollbar.set)

        content = ttk.Frame(self.search_canvas)
        self.search_content = content
        self.search_canvas_window = self.search_canvas.create_window(
            (0, 0), window=content, anchor="nw"
        )
        content.bind("<Configure>", self._update_search_scrollregion)
        self.search_canvas.bind("<Configure>", self._resize_search_scroll_content)
        content.columnconfigure(1, weight=1)

        self.sources_frame = ttk.LabelFrame(
            content, text="Платформи / джерела", padding=12
        )
        self.sources_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 8))

        filters = ttk.LabelFrame(content, text="Фільтри", padding=12)
        filters.grid(row=0, column=1, sticky="nsew")
        filters.columnconfigure(1, weight=1)
        self.role_var = StringVar()
        self.keyword_var = StringVar()
        self.location_var = StringVar()
        self.location_radius_var = DoubleVar(value=0)
        self.excluded_keyword_var = StringVar()
        self.excluded_company_var = StringVar()
        self.minimum_score_var = DoubleVar(value=0)
        self.filter_remote_var = BooleanVar(value=False)

        filter_rows = (
            (
                "Бажані посади",
                self.role_var,
                (
                    "Через кому; кожна повна назва — окрема альтернатива (АБО / OR). "
                    "Пишіть «Administrative Assistant», а не «Administrative, Assistant»."
                ),
            ),
            (
                "Додаткові вимоги (не міста)",
                self.keyword_var,
                "Необов’язково. Напр.: SAP, Excel. Усі мають збігтися (І / AND).",
            ),
            (
                "Локації (міста) *",
                self.location_var,
                (
                    "Обов’язково. Введіть назву, оберіть точне місто з підказки; "
                    "можна додати кілька міст, вони працюють як АБО / OR."
                ),
            ),
            ("Виключити слова", self.excluded_keyword_var, "Через кому."),
            ("Виключити компанії", self.excluded_company_var, "Через кому."),
        )
        for row, (label, variable, hint) in enumerate(filter_rows):
            ttk.Label(filters, text=label).grid(row=row, column=0, sticky="nw", pady=5)
            field = ttk.Frame(filters)
            field.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=5)
            field.columnconfigure(0, weight=1)
            if variable is self.location_var:
                self.location_entry = ttk.Combobox(
                    field,
                    textvariable=variable,
                    state="normal",
                )
                self.location_entry.grid(row=0, column=0, sticky="ew")
                self.location_entry.bind(
                    "<KeyRelease>", self._schedule_location_lookup
                )
                self.location_entry.bind(
                    "<<ComboboxSelected>>", self._select_location_suggestion
                )
            else:
                ttk.Entry(field, textvariable=variable).grid(
                    row=0, column=0, sticky="ew"
                )
            ttk.Label(field, text=hint, foreground="#555555", wraplength=680).grid(
                row=1, column=0, sticky="w", pady=(2, 0)
            )
            if variable is self.location_var:
                location_controls = ttk.Frame(field)
                location_controls.grid(row=2, column=0, sticky="ew", pady=(6, 0))
                location_controls.columnconfigure(4, weight=1)
                ttk.Label(location_controls, text="Країна підказок").grid(
                    row=0, column=0, sticky="w"
                )
                self.location_country_var = StringVar(value="Deutschland (DE)")
                country_box = ttk.Combobox(
                    location_controls,
                    textvariable=self.location_country_var,
                    values=tuple(_LOCATION_COUNTRIES),
                    state="readonly",
                    width=19,
                )
                country_box.grid(row=0, column=1, sticky="w", padx=(6, 12))
                country_box.bind(
                    "<<ComboboxSelected>>", self._schedule_location_lookup
                )
                ttk.Button(
                    location_controls,
                    text="Додати введене без перевірки",
                    command=self._add_manual_locations,
                ).grid(row=0, column=2, sticky="w")
                ttk.Button(
                    location_controls,
                    text="Видалити вибране",
                    command=self._remove_selected_location,
                ).grid(row=0, column=3, sticky="w", padx=(6, 0))

                ttk.Label(field, text="Вибрані міста:").grid(
                    row=3, column=0, sticky="w", pady=(6, 2)
                )
                self.selected_locations_list = Listbox(
                    field,
                    height=3,
                    exportselection=False,
                    font=("Segoe UI", 9),
                )
                self.selected_locations_list.grid(row=4, column=0, sticky="ew")
                self.location_lookup_status_var = StringVar(
                    value="Почніть вводити щонайменше 2–3 літери й оберіть місто зі списку."
                )
                ttk.Label(
                    field,
                    textvariable=self.location_lookup_status_var,
                    foreground="#555555",
                    wraplength=680,
                ).grid(row=5, column=0, sticky="w", pady=(2, 0))

                radius_frame = ttk.Frame(field)
                radius_frame.grid(row=6, column=0, sticky="ew", pady=(6, 0))
                radius_frame.columnconfigure(1, weight=1)
                ttk.Label(radius_frame, text="Радіус").grid(row=0, column=0, sticky="w")
                ttk.Scale(
                    radius_frame,
                    from_=0,
                    to=200,
                    variable=self.location_radius_var,
                    command=self._update_radius_label,
                ).grid(row=0, column=1, sticky="ew", padx=(10, 8))
                self.location_radius_label = ttk.Label(
                    radius_frame, text="Без радіуса", width=12
                )
                self.location_radius_label.grid(row=0, column=2, sticky="e")
                ttk.Label(
                    radius_frame,
                    text=(
                        "Один радіус застосовується окремо до кожного вибраного "
                        "міста. Bundesagentur передає його серверу; джерела без "
                        "геопошуку можуть фільтрувати лише за назвою."
                    ),
                    foreground="#555555",
                    wraplength=620,
                ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 0))
        ttk.Checkbutton(
            filters,
            text="Тільки remote (якщо вимкнено — remote, hybrid, office та невідомий формат)",
            variable=self.filter_remote_var,
        ).grid(row=5, column=1, sticky="w", padx=(12, 0), pady=5)
        ttk.Label(filters, text="Мінімальна релевантність").grid(
            row=6, column=0, sticky="w", pady=5
        )
        score_frame = ttk.Frame(filters)
        score_frame.grid(row=6, column=1, sticky="ew", padx=(12, 0), pady=5)
        score_frame.columnconfigure(0, weight=1)
        ttk.Scale(
            score_frame,
            from_=0,
            to=100,
            variable=self.minimum_score_var,
            command=self._update_minimum_score,
        ).grid(row=0, column=0, sticky="ew")
        self.minimum_score_label = ttk.Label(score_frame, text="0%", width=5)
        self.minimum_score_label.grid(row=0, column=1, padx=(8, 0))

        search_actions = ttk.Frame(self.search_tab)
        search_actions.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(
            search_actions,
            text="Ctrl+Enter — почати пошук; Enter/Space — натиснути вибрану кнопку",
            foreground="#555555",
        ).pack(side="left")
        self.search_button = ttk.Button(
            search_actions,
            text="Знайти вакансії в інтернеті",
            command=self._run_search,
            style="Primary.TButton",
        )
        self.search_button.pack(side="right")

        self.root.bind_all("<MouseWheel>", self._scroll_search_with_mouse, add="+")
        self.search_canvas.bind("<Up>", self._scroll_search_with_keyboard)
        self.search_canvas.bind("<Down>", self._scroll_search_with_keyboard)
        self.search_canvas.bind("<Prior>", self._scroll_search_with_keyboard)
        self.search_canvas.bind("<Next>", self._scroll_search_with_keyboard)
        self.search_canvas.bind("<Home>", self._scroll_search_with_keyboard)
        self.search_canvas.bind("<End>", self._scroll_search_with_keyboard)
        self._bind_search_focus_scrolling(content)

    def _build_results_tab(self) -> None:
        self.results_tab.columnconfigure(0, weight=1)
        self.results_tab.rowconfigure(2, weight=1)
        toolbar = ttk.Frame(self.results_tab)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(toolbar, text="Релевантні вакансії", style="Heading.TLabel").pack(
            side="left"
        )
        self.results_count_var = StringVar(value="Вакансій у списку: 0")
        ttk.Label(toolbar, textvariable=self.results_count_var).pack(
            side="left", padx=(16, 0)
        )
        ttk.Button(toolbar, text="Відкрити вакансію", command=self._open_job).pack(
            side="right"
        )
        ttk.Button(
            toolbar,
            text="Підготувати / подати заявку",
            command=self._prepare_application,
            style="Primary.TButton",
        ).pack(side="right", padx=(0, 6))
        ttk.Button(
            toolbar,
            text="Цікаво",
            command=lambda: self._mark_selected_result(ApplicationStatus.INTERESTING),
        ).pack(side="right", padx=(0, 6))

        results_info = ttk.Frame(self.results_tab)
        results_info.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        results_info.columnconfigure(0, weight=1)
        self.source_summary_var = StringVar(
            value="Джерела: пошук ще не запускався"
        )
        ttk.Label(
            results_info,
            textvariable=self.source_summary_var,
            foreground="#444444",
            wraplength=850,
        ).grid(row=0, column=0, sticky="ew")
        sort_frame = ttk.Frame(results_info)
        sort_frame.grid(row=0, column=1, sticky="e", padx=(12, 0))
        ttk.Label(sort_frame, text="Сортування:").pack(side="left", padx=(0, 6))
        self.result_sort_var = StringVar(value="За релевантністю")
        result_sort_box = ttk.Combobox(
            sort_frame,
            textvariable=self.result_sort_var,
            values=tuple(_RESULT_SORT_OPTIONS),
            state="readonly",
            width=23,
        )
        result_sort_box.pack(side="left")
        result_sort_box.bind("<<ComboboxSelected>>", self._change_result_sort)

        panes = ttk.Panedwindow(self.results_tab, orient="vertical")
        panes.grid(row=2, column=0, sticky="nsew")
        table_frame = ttk.Frame(panes)
        detail_frame = ttk.LabelFrame(panes, text="Пояснення відповідності", padding=8)
        panes.add(table_frame, weight=3)
        panes.add(detail_frame, weight=2)

        columns = (
            "score",
            "published",
            "title",
            "company",
            "location",
            "source",
            "skills",
            "status",
        )
        self.results_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )
        headings = {
            "score": "Match",
            "published": "Опубліковано",
            "title": "Вакансія",
            "company": "Компанія",
            "location": "Локація",
            "source": "Джерело",
            "skills": "Ключові збіги",
            "status": "Статус",
        }
        widths = {
            "score": 70,
            "published": 105,
            "title": 220,
            "company": 160,
            "location": 130,
            "source": 100,
            "skills": 220,
            "status": 90,
        }
        for column in columns:
            self.results_tree.heading(column, text=headings[column])
            self.results_tree.column(
                column,
                width=widths[column],
                minwidth=60,
                anchor="center" if column in {"score", "published", "status"} else "w",
            )
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        table_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.results_tree.yview
        )
        table_horizontal_scroll = ttk.Scrollbar(
            table_frame, orient="horizontal", command=self.results_tree.xview
        )
        self.results_tree.configure(
            yscrollcommand=table_scroll.set,
            xscrollcommand=table_horizontal_scroll.set,
        )
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        table_scroll.grid(row=0, column=1, sticky="ns")
        table_horizontal_scroll.grid(row=1, column=0, sticky="ew")
        self.results_tree.bind("<<TreeviewSelect>>", self._show_result_details)
        self.results_tree.bind("<Double-1>", lambda _event: self._open_job())
        self.results_tree.tag_configure("full", background="#e4f5e9")
        self.results_tree.tag_configure("partial", background="#fff5d6")
        self.results_tree.tag_configure("weak", background="#f8e3e3")

        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)
        self.result_details = Text(
            detail_frame, wrap="word", font=("Segoe UI", 10), state="disabled"
        )
        detail_scroll = ttk.Scrollbar(
            detail_frame, orient="vertical", command=self.result_details.yview
        )
        self.result_details.configure(yscrollcommand=detail_scroll.set)
        self.result_details.grid(row=0, column=0, sticky="nsew")
        detail_scroll.grid(row=0, column=1, sticky="ns")

    def _build_applications_tab(self) -> None:
        self.applications_tab.columnconfigure(0, weight=1)
        self.applications_tab.rowconfigure(1, weight=1)
        ttk.Label(
            self.applications_tab,
            text="Історія заявок",
            style="Heading.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        panes = ttk.Panedwindow(self.applications_tab, orient="vertical")
        panes.grid(row=1, column=0, sticky="nsew")
        table_frame = ttk.Frame(panes)
        history_frame = ttk.LabelFrame(panes, text="Історія статусів", padding=8)
        panes.add(table_frame, weight=3)
        panes.add(history_frame, weight=2)

        columns = ("title", "company", "status", "updated", "source")
        self.applications_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )
        for column, label, width in (
            ("title", "Вакансія", 260),
            ("company", "Компанія", 190),
            ("status", "Статус", 110),
            ("updated", "Оновлено", 160),
            ("source", "Джерело", 120),
        ):
            self.applications_tree.heading(column, text=label)
            self.applications_tree.column(column, width=width)
        app_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.applications_tree.yview
        )
        self.applications_tree.configure(yscrollcommand=app_scroll.set)
        self.applications_tree.pack(side="left", fill="both", expand=True)
        app_scroll.pack(side="right", fill="y")
        self.applications_tree.bind(
            "<<TreeviewSelect>>", self._show_application_history
        )

        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
        self.application_history = Text(
            history_frame, wrap="word", font=("Segoe UI", 10), state="disabled"
        )
        self.application_history.grid(row=0, column=0, columnspan=4, sticky="nsew")
        ttk.Label(history_frame, text="Новий статус").grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        self.application_status_var = StringVar(value=ApplicationStatus.INTERESTING.value)
        ttk.Combobox(
            history_frame,
            textvariable=self.application_status_var,
            values=[status.value for status in ApplicationStatus],
            state="readonly",
            width=16,
        ).grid(row=1, column=1, sticky="w", padx=(8, 16), pady=(8, 0))
        self.application_notes_var = StringVar()
        ttk.Entry(history_frame, textvariable=self.application_notes_var).grid(
            row=1, column=2, sticky="ew", pady=(8, 0)
        )
        history_frame.columnconfigure(2, weight=1)
        ttk.Button(
            history_frame, text="Оновити", command=self._update_application_status
        ).grid(row=1, column=3, padx=(8, 0), pady=(8, 0))

    def _build_settings_tab(self) -> None:
        self.settings_tab.columnconfigure(0, weight=1)
        ttk.Label(
            self.settings_tab, text="Налаштування", style="Heading.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))
        storage = ttk.LabelFrame(self.settings_tab, text="Локальні дані", padding=12)
        storage.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        storage.columnconfigure(1, weight=1)
        ttk.Label(storage, text="Файл сховища").grid(row=0, column=0, sticky="w")
        ttk.Label(storage, text=str(self.store.path.resolve())).grid(
            row=0, column=1, sticky="w", padx=(12, 0)
        )
        ttk.Label(
            storage,
            text=(
                "Профіль, вакансії та історія зберігаються тільки локально. "
                "JobCompass не надсилає резюме або дані до AI-сервісів."
            ),
            wraplength=850,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        connectors = ttk.LabelFrame(
            self.settings_tab, text="Конектори та формати", padding=12
        )
        connectors.grid(row=2, column=0, sticky="ew")
        ttk.Label(
            connectors,
            text=(
                "Вакансії: Bundesagentur, Arbeitnow і Remotive підключені; доступність "
                "залежить від зовнішніх сервісів.\n"
                "Підказки міст: Open-Meteo Geocoding / GeoNames, без ключа для "
                "некомерційного використання; вводиться лише текст міста.\n"
                "JSON-імпорт залишається допоміжним режимом для тестів і власних даних.\n"
                "Резюме: JSON, TXT, DOCX і текстовий PDF — доступно локально.\n"
                "СЛ, безкоштовний режим: локальна чернетка та покращений промпт — доступно.\n"
                "СЛ, AI/API режим: заплановано; токени ще не приймаються і зовнішні "
                "виклики відсутні."
            ),
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            connectors,
            text="Імпортувати вакансії з JSON",
            command=self._import_jobs,
        ).grid(row=1, column=0, sticky="w", pady=(12, 0))

    def _populate_profile(self, profile: CandidateProfile) -> None:
        values = {
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "desired_roles": ", ".join(profile.desired_roles),
            "skills": ", ".join(profile.skills),
            "languages": ", ".join(profile.languages),
            "years_experience": (
                f"{profile.years_experience:g}"
                if profile.years_experience is not None
                else ""
            ),
            "preferred_locations": ", ".join(profile.preferred_locations),
        }
        for field_name, value in values.items():
            self.profile_vars[field_name].set(value)
        self.summary_text.delete("1.0", END)
        self.summary_text.insert("1.0", profile.summary)
        self.remote_only_var.set(profile.remote_only)
        if not self.role_var.get().strip() and profile.desired_roles:
            self.role_var.set(", ".join(profile.desired_roles))

    def _profile_from_form(self) -> CandidateProfile:
        years_text = self.profile_vars["years_experience"].get().strip()
        try:
            years = float(years_text.replace(",", ".")) if years_text else None
        except ValueError as error:
            raise ValueError("Роки досвіду повинні бути числом") from error
        return CandidateProfile(
            full_name=self.profile_vars["full_name"].get(),
            email=self.profile_vars["email"].get(),
            phone=self.profile_vars["phone"].get(),
            summary=self.summary_text.get("1.0", "end-1c"),
            desired_roles=_split_list(self.profile_vars["desired_roles"].get()),
            skills=_split_list(self.profile_vars["skills"].get()),
            languages=_split_list(self.profile_vars["languages"].get()),
            years_experience=years,
            preferred_locations=_split_list(
                self.profile_vars["preferred_locations"].get()
            ),
            remote_only=self.remote_only_var.get(),
        )

    def _load_resume(self) -> None:
        path = filedialog.askopenfilename(
            title="Виберіть резюме",
            filetypes=(
                ("Підтримувані резюме", "*.json *.txt *.docx *.pdf"),
                ("JSON", "*.json"),
                ("Text", "*.txt"),
                ("Word", "*.docx"),
                ("PDF", "*.pdf"),
                ("Усі файли", "*.*"),
            ),
        )
        if not path:
            return
        try:
            result = load_resume(path)
            self.store.save_profile(result.profile)
        except (OSError, ValueError) as error:
            messagebox.showerror("Не вдалося прочитати резюме", str(error))
            return
        self.profile = result.profile
        self._populate_profile(result.profile)
        self.resume_path_var.set(str(Path(path).resolve()))
        self._set_text(self.resume_preview, result.raw_text)
        self.status_var.set(
            "Резюме завантажено й активовано — ручне заповнення полів необов’язкове"
        )
        if result.warnings:
            messagebox.showwarning(
                "Резюме готове до використання",
                "Профіль уже збережено локально. Поля можна не заповнювати.\n\n"
                + "\n\n".join(result.warnings),
            )

    def _save_profile(self) -> None:
        try:
            profile = self._profile_from_form()
            self.store.save_profile(profile)
        except (OSError, ValueError) as error:
            messagebox.showerror("Не вдалося зберегти профіль", str(error))
            return
        self.profile = profile
        self.status_var.set("Профіль збережено локально")
        messagebox.showinfo("JobCompass", "Профіль збережено.")

    def _import_jobs(self) -> None:
        path = filedialog.askopenfilename(
            title="Імпорт вакансій",
            filetypes=(("JSON", "*.json"), ("Усі файли", "*.*")),
        )
        if not path:
            return
        try:
            jobs = JsonFileSource(path).search(SearchQuery())
            added = self.store.save_jobs(jobs)
        except (OSError, ValueError) as error:
            messagebox.showerror("Не вдалося імпортувати вакансії", str(error))
            return
        self._refresh_sources()
        self.status_var.set(f"Прочитано {len(jobs)}, додано нових вакансій: {added}")
        messagebox.showinfo(
            "Імпорт завершено",
            f"Прочитано: {len(jobs)}\nДодано нових: {added}",
        )

    def _refresh_sources(self) -> None:
        previous = {name: variable.get() for name, variable in self.source_vars.items()}
        for child in self.sources_frame.winfo_children():
            child.destroy()
        stored_sources = {job.source for job in self.store.list_jobs()}
        sources = list(self.online_sources)
        sources.extend(
            sorted(stored_sources - set(self.online_sources), key=str.casefold)
        )
        self.source_vars = {}
        for source in sources:
            variable = BooleanVar(value=previous.get(source, True))
            self.source_vars[source] = variable
            ttk.Checkbutton(
                self.sources_frame, text=source, variable=variable
            ).pack(anchor="w", pady=2)

    def _run_search(self) -> None:
        if self.search_running:
            return
        try:
            profile = self._profile_from_form()
            selected_sources = tuple(
                source for source, variable in self.source_vars.items() if variable.get()
            )
            if not selected_sources:
                raise ValueError("Оберіть хоча б одне джерело вакансій")
            roles = _split_list(self.role_var.get()) or profile.desired_roles
            keywords = _split_list(self.keyword_var.get())
            location_selections = tuple(self.selected_locations)
            locations = tuple(item.name for item in location_selections)
            if not location_selections:
                raise ValueError(
                    "Оберіть хоча б одне місто з підказки або натисніть "
                    "«Додати введене без перевірки»."
                )
            if roles and profile.desired_roles != roles:
                profile = replace(profile, desired_roles=roles)
                self.store.save_profile(profile)
                self._populate_profile(profile)
            online_names = tuple(
                source for source in selected_sources if source in self.online_sources
            )
            if online_names and not roles and not keywords:
                raise ValueError(
                    "Для інтернет-пошуку вкажіть хоча б одну бажану посаду"
                )
            filters = SearchFilters(
                sources=selected_sources,
                roles=roles,
                keywords=keywords,
                locations=locations,
                location_selections=location_selections,
                location_radius_km=(
                    round(self.location_radius_var.get())
                    if self.location_radius_var.get() >= 1
                    else None
                ),
                excluded_keywords=_split_list(self.excluded_keyword_var.get()),
                excluded_companies=_split_list(self.excluded_company_var.get()),
                remote_only=self.filter_remote_var.get(),
                minimum_score=round(self.minimum_score_var.get()),
            )
        except (OSError, ValueError) as error:
            messagebox.showerror("Пошук не виконано", str(error))
            return

        query = SearchQuery(
            roles=filters.roles,
            locations=filters.locations,
            location_selections=filters.location_selections,
            location_radius_km=filters.location_radius_km,
            keywords=filters.keywords,
            remote_only=filters.remote_only,
        )
        if not online_names:
            self._complete_search(profile, filters, [], {}, {})
            return

        self.search_running = True
        self.ranked_jobs = []
        self.empty_results_message = "Триває новий пошук вакансій…"
        self._render_results()
        self.results_count_var.set("Пошук…")
        self.source_summary_var.set(
            "Джерела: виконується новий пошук; попередні результати очищено"
        )
        self.search_button.configure(state="disabled", text="Пошук…")
        self.status_var.set(
            "Пошук у мережі: " + ", ".join(online_names) + " — зачекайте"
        )
        worker = Thread(
            target=self._fetch_online_jobs,
            args=(online_names, query, profile, filters),
            daemon=True,
        )
        worker.start()
        self.root.after(100, self._poll_search_queue)

    def _fetch_online_jobs(
        self,
        source_names: tuple[str, ...],
        query: SearchQuery,
        profile: CandidateProfile,
        filters: SearchFilters,
    ) -> None:
        jobs: list[JobPosting] = []
        counts: dict[str, int] = {}
        errors: dict[str, str] = {}
        source_query = replace(query, keywords=())
        for name in source_names:
            try:
                found = self.online_sources[name].search(source_query)
            except Exception as error:
                errors[name] = str(error)
                continue
            jobs.extend(found)
            counts[name] = len(found)
            partial_error = getattr(
                self.online_sources[name], "last_partial_error", ""
            )
            if partial_error:
                errors[name] = (
                    f"Отримано часткові результати; наступні сторінки недоступні: "
                    f"{partial_error}"
                )
        self.search_queue.put((profile, filters, jobs, counts, errors))

    def _poll_search_queue(self) -> None:
        try:
            payload = self.search_queue.get_nowait()
        except Empty:
            if self.search_running:
                self.root.after(100, self._poll_search_queue)
            return
        profile, filters, jobs, counts, errors = payload
        self._complete_search(profile, filters, jobs, counts, errors)

    def _complete_search(
        self,
        profile: CandidateProfile,
        filters: SearchFilters,
        online_jobs: list[JobPosting],
        counts: dict[str, int],
        errors: dict[str, str],
    ) -> None:
        selected_online_sources = set(filters.sources) & set(self.online_sources)
        try:
            if online_jobs:
                self.store.save_jobs(online_jobs)
            stored_jobs = self.store.list_jobs()
            current_search_jobs = deduplicate_jobs(
                [
                    *online_jobs,
                    *(
                        job
                        for job in stored_jobs
                        if job.source not in selected_online_sources
                    ),
                ]
            )
            location_prefiltered_job_ids = frozenset(
                job.job_id for job in online_jobs
            )
            self.last_search_profile = profile
            self.last_search_filters = filters
            self.last_search_jobs = current_search_jobs
            self.last_location_prefiltered_job_ids = location_prefiltered_job_ids
            broadly_matching = search_jobs(
                profile,
                current_search_jobs,
                replace(
                    filters,
                    keywords=(),
                    excluded_keywords=(),
                    excluded_companies=(),
                    minimum_score=0,
                ),
                location_prefiltered_job_ids=location_prefiltered_job_ids,
            )
            matching_before_score = search_jobs(
                profile,
                current_search_jobs,
                replace(filters, minimum_score=0),
                location_prefiltered_job_ids=location_prefiltered_job_ids,
            )
            self.ranked_jobs = search_jobs(
                profile,
                current_search_jobs,
                filters,
                location_prefiltered_job_ids=location_prefiltered_job_ids,
            )
            if self.ranked_jobs:
                self.empty_results_message = ""
            elif broadly_matching and not matching_before_score:
                details: list[str] = []
                if filters.keywords:
                    details.append(
                        "додаткові вимоги: " + ", ".join(filters.keywords)
                    )
                if filters.excluded_keywords:
                    details.append(
                        "виключені слова: " + ", ".join(filters.excluded_keywords)
                    )
                if filters.excluded_companies:
                    details.append(
                        "виключені компанії: "
                        + ", ".join(filters.excluded_companies)
                    )
                self.empty_results_message = (
                    f"Знайдено {len(broadly_matching)} вакансій за посадами й "
                    "локаціями, але їх прибрали додаткові фільтри.\n\n"
                    + ("Перевірте: " + "; ".join(details) if details else "")
                )
            elif matching_before_score:
                maximum = max(item.match.score for item in matching_before_score)
                self.empty_results_message = (
                    f"До порога релевантності дійшло {len(matching_before_score)} "
                    f"вакансій. Найвищий score: {maximum}%, встановлений поріг: "
                    f"{filters.minimum_score}%. Зменште мінімальну релевантність."
                )
            else:
                self.empty_results_message = (
                    "Інтернет-джерела не повернули вакансій для вибраних посад, "
                    "локацій і радіуса."
                )
        except (OSError, ValueError) as error:
            messagebox.showerror("Не вдалося зберегти результати", str(error))
            self.ranked_jobs = []
        finally:
            self.search_running = False
            self.search_button.configure(
                state="normal", text="Знайти вакансії в інтернеті"
            )

        self.profile = profile
        self._refresh_sources()
        self._render_results()
        self.notebook.select(self.results_tab)
        source_summary = ", ".join(
            f"{name}: {count}" for name, count in counts.items()
        )
        diagnostic_parts: list[str] = []
        for name in self.online_sources:
            if name not in selected_online_sources:
                continue
            if name in errors:
                if counts.get(name, 0):
                    diagnostic_parts.append(
                        f"{name}: {counts[name]} (часткові результати)"
                    )
                else:
                    diagnostic_parts.append(f"{name}: помилка")
            else:
                diagnostic_parts.append(f"{name}: {counts.get(name, 0)}")
        self.source_diagnostics_prefix = (
            "Отримано після фільтрів джерел: "
            + (
                ", ".join(diagnostic_parts)
                if diagnostic_parts
                else "онлайн-джерела не вибрано"
            )
        )
        self.source_summary_var.set(
            self.source_diagnostics_prefix
            + f" | після об’єднання та фільтрів JobCompass: {len(self.ranked_jobs)}"
        )
        self.status_var.set(
            f"Показано релевантних вакансій: {len(self.ranked_jobs)}"
            + (f" | отримано: {source_summary}" if source_summary else "")
        )
        if errors:
            messagebox.showwarning(
                "Деякі джерела недоступні",
                "Інші джерела оброблено.\n\n"
                + "\n".join(f"{name}: {error}" for name, error in errors.items()),
            )
        elif online_jobs and not self.ranked_jobs:
            messagebox.showinfo(
                "Вакансії знайдено, але їх приховали фільтри",
                self.empty_results_message,
            )

    @staticmethod
    def _published_timestamp(value: datetime | None) -> float:
        if value is None:
            return 0.0
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()

    @staticmethod
    def _format_published_at(value: datetime | None) -> str:
        if value is None:
            return "Не вказано"
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone().strftime("%d.%m.%Y")

    def _ordered_results(self) -> list[RankedJob]:
        mode = _RESULT_SORT_OPTIONS.get(
            self.result_sort_var.get(), "relevance"
        )
        if mode == "relevance":
            return list(self.ranked_jobs)

        newest_first = mode == "newest"
        return sorted(
            self.ranked_jobs,
            key=lambda item: (
                item.job.published_at is None,
                (
                    -self._published_timestamp(item.job.published_at)
                    if newest_first
                    else self._published_timestamp(item.job.published_at)
                ),
                -item.match.score,
                item.job.title.casefold(),
            ),
        )

    def _change_result_sort(self, _event: object | None = None) -> None:
        selection = self.results_tree.selection()
        selected_job_id = selection[0] if selection else None
        self._render_results(selected_job_id)

    def _render_results(self, selected_job_id: str | None = None) -> None:
        self.results_tree.delete(*self.results_tree.get_children())
        self.results_count_var.set(
            f"Вакансій у списку: {len(self.ranked_jobs)}"
        )
        self.result_by_id = {item.job.job_id: item for item in self.ranked_jobs}
        applications = {
            item.job_id: item.status.value for item in self.store.list_applications()
        }
        displayed_jobs = self._ordered_results()
        for ranked in displayed_jobs:
            job = ranked.job
            result = ranked.match
            self.results_tree.insert(
                "",
                END,
                iid=job.job_id,
                values=(
                    f"{result.score}%",
                    self._format_published_at(job.published_at),
                    job.title,
                    job.company,
                    (
                        f"{_WORK_MODE_LABELS[job.work_mode.value]} · {job.location}"
                        if job.location
                        else _WORK_MODE_LABELS[job.work_mode.value]
                    ),
                    job.source,
                    ", ".join(result.matched_skills[:4]),
                    applications.get(job.job_id, ApplicationStatus.FOUND.value),
                ),
                tags=(result.level.value,),
            )
        if displayed_jobs:
            active_id = (
                selected_job_id
                if selected_job_id in self.result_by_id
                else displayed_jobs[0].job.job_id
            )
            self.results_tree.selection_set(active_id)
            self.results_tree.focus(active_id)
            self.results_tree.see(active_id)
            self._show_result_details()
        else:
            self._set_text(
                self.result_details,
                self.empty_results_message,
            )

    def _selected_result(self) -> RankedJob | None:
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("JobCompass", "Спочатку виберіть вакансію.")
            return None
        return self.result_by_id.get(selection[0])

    def _show_result_details(self, _event: object | None = None) -> None:
        selection = self.results_tree.selection()
        if not selection:
            return
        ranked = self.result_by_id.get(selection[0])
        if ranked is None:
            return
        job, result = ranked.job, ranked.match
        lines = [
            f"{job.title} — {job.company}",
            f"Релевантність: {result.score}% ({result.level.value})",
            f"Повнота доказів для оцінювання: {result.evidence_coverage}%",
            f"Джерело: {job.source}",
            f"Опубліковано: {self._format_published_at(job.published_at)}",
            f"Формат роботи: {_WORK_MODE_LABELS[job.work_mode.value]}",
            f"Локація: {job.location or 'не вказана'}",
        ]
        if job.url:
            lines.append(f"Посилання: {job.url}")
        lines.append("\nКомпоненти оцінювання:")
        for name, score in result.component_scores.items():
            lines.append(f"• {_COMPONENT_LABELS.get(name, name)}: {score}%")
        if result.matched_skills:
            lines.append("\nЗбігаються: " + ", ".join(result.matched_skills))
        if result.missing_required_skills:
            lines.append(
                "Бракує обов’язкових: "
                + ", ".join(result.missing_required_skills)
            )
        if result.risks:
            lines.append("\nРизики:")
            lines.extend(f"• {risk}" for risk in result.risks)
        if job.requirement_evidence:
            lines.append("\nДокази з тексту вакансії:")
            lines.extend(
                f"• [{item.classification}] {item.value}: “{item.excerpt}”"
                for item in job.requirement_evidence
            )
        if job.description:
            lines.append("\nОпис:\n" + job.description)
        self._set_text(self.result_details, "\n".join(lines))

    def _open_job(self) -> None:
        ranked = self._selected_result()
        if ranked is None:
            return
        self._open_job_for(ranked.job)

    def _open_job_for(self, job: JobPosting) -> bool:
        if not job.url:
            messagebox.showwarning("JobCompass", "Для вакансії немає посилання.")
            return False
        webbrowser.open(job.url)
        return True

    def _prepare_application(self) -> None:
        ranked = self._selected_result()
        if ranked is None:
            return
        ApplicationPreparationDialog(self, ranked)

    def _schedule_location_lookup(self, event: object | None = None) -> None:
        keysym = getattr(event, "keysym", "")
        if keysym in {
            "Up",
            "Down",
            "Left",
            "Right",
            "Return",
            "Escape",
            "Tab",
        }:
            return
        if self.location_lookup_after_id is not None:
            try:
                self.root.after_cancel(self.location_lookup_after_id)
            except Exception:
                pass
            self.location_lookup_after_id = None
        query = self.location_var.get().strip()
        if len(query) < 2:
            self.location_suggestions = {}
            self.location_entry.configure(values=())
            self.location_lookup_status_var.set(
                "Введіть щонайменше 2–3 літери назви міста."
            )
            return
        self.location_lookup_status_var.set("Шукаю відповідні міста…")
        self.location_lookup_after_id = self.root.after(
            350, lambda: self._start_location_lookup(query)
        )

    def _start_location_lookup(self, query: str) -> None:
        self.location_lookup_after_id = None
        self.location_lookup_generation += 1
        generation = self.location_lookup_generation
        country_code = _LOCATION_COUNTRIES.get(
            self.location_country_var.get(), "DE"
        )

        def worker() -> None:
            try:
                suggestions = self.location_geocoder.search(
                    query,
                    country_code=country_code,
                    language="de",
                    count=10,
                )
                error = ""
            except Exception as lookup_error:
                suggestions = []
                error = str(lookup_error)
            self.location_lookup_queue.put(
                (generation, query, suggestions, error)
            )

        Thread(target=worker, daemon=True).start()
        if not self.location_lookup_polling:
            self.location_lookup_polling = True
            self.root.after(75, self._poll_location_lookup)

    def _poll_location_lookup(self) -> None:
        latest: tuple[int, str, list[LocationSelection], str] | None = None
        try:
            while True:
                payload = self.location_lookup_queue.get_nowait()
                if (
                    isinstance(payload, tuple)
                    and len(payload) == 4
                    and payload[0] == self.location_lookup_generation
                ):
                    latest = payload
        except Empty:
            pass
        if latest is None:
            self.root.after(75, self._poll_location_lookup)
            return
        self.location_lookup_polling = False
        _, query, suggestions, error = latest
        if query.casefold() != self.location_var.get().strip().casefold():
            return
        if error:
            self.location_suggestions = {}
            self.location_entry.configure(values=())
            self.location_lookup_status_var.set(
                "Підказки міст тимчасово недоступні. Місто можна додати вручну."
            )
            return

        suggestion_map: dict[str, LocationSelection] = {}
        for suggestion in suggestions:
            label = suggestion.display_name
            if label in suggestion_map:
                assert suggestion.latitude is not None
                assert suggestion.longitude is not None
                label += f" ({suggestion.latitude:.4f}, {suggestion.longitude:.4f})"
            suggestion_map[label] = suggestion
        self.location_suggestions = suggestion_map
        labels = tuple(suggestion_map)
        self.location_entry.configure(values=labels)
        if labels:
            self.location_lookup_status_var.set(
                f"Знайдено варіантів: {len(labels)}. Оберіть точне місто зі списку."
            )
            if self.location_entry.focus_get() is self.location_entry:
                try:
                    self.location_entry.event_generate("<Down>")
                except Exception:
                    pass
        else:
            self.location_lookup_status_var.set(
                "Місто не знайдено. Перевірте написання або додайте введене вручну."
            )

    def _select_location_suggestion(self, _event: object | None = None) -> None:
        label = self.location_var.get().strip()
        suggestion = self.location_suggestions.get(label)
        if suggestion is None:
            return
        self._add_location_selection(suggestion)
        self.location_var.set("")
        self.location_suggestions = {}
        self.location_entry.configure(values=())

    @staticmethod
    def _location_selection_key(selection: LocationSelection) -> object:
        if selection.geonames_id is not None:
            return ("geonames", selection.geonames_id)
        return (
            selection.name.casefold(),
            selection.admin1.casefold(),
            selection.country_code.casefold(),
        )

    def _add_location_selection(self, selection: LocationSelection) -> None:
        key = self._location_selection_key(selection)
        if any(
            self._location_selection_key(existing) == key
            for existing in self.selected_locations
        ):
            self.location_lookup_status_var.set(
                f"Місто вже вибрано: {selection.display_name}"
            )
            return
        self.selected_locations.append(selection)
        self._refresh_selected_locations()
        self.location_lookup_status_var.set(
            f"Додано: {selection.display_name}"
        )

    def _add_manual_locations(self) -> None:
        names = _split_list(self.location_var.get())
        if not names:
            self.location_lookup_status_var.set("Спочатку введіть назву міста.")
            return
        for name in names:
            self._add_location_selection(LocationSelection(name=name))
        self.location_var.set("")
        self.location_suggestions = {}
        self.location_entry.configure(values=())
        self.location_lookup_status_var.set(
            "Місто додано без географічної перевірки; за можливості оберіть підказку."
        )

    def _remove_selected_location(self) -> None:
        selection = self.selected_locations_list.curselection()
        if not selection:
            self.location_lookup_status_var.set(
                "Виберіть місто у списку, яке потрібно видалити."
            )
            return
        del self.selected_locations[selection[0]]
        self._refresh_selected_locations()

    def _refresh_selected_locations(self) -> None:
        self.selected_locations_list.delete(0, END)
        radius = round(self.location_radius_var.get())
        radius_label = "без радіуса" if radius < 1 else f"+{radius} km"
        for selection in self.selected_locations:
            self.selected_locations_list.insert(
                END, f"{selection.display_name}  ·  {radius_label}"
            )

    def _update_radius_label(self, value: str) -> None:
        radius = round(float(value))
        self.location_radius_label.configure(
            text="Без радіуса" if radius < 1 else f"+{radius} km"
        )
        if hasattr(self, "selected_locations_list"):
            self._refresh_selected_locations()

    def _update_minimum_score(self, value: str) -> None:
        threshold = round(float(value))
        self.minimum_score_label.configure(text=f"{threshold}%")
        if (
            self.search_running
            or self.last_search_profile is None
            or self.last_search_filters is None
        ):
            return

        filters = replace(self.last_search_filters, minimum_score=threshold)
        matching_before_threshold = search_jobs(
            self.last_search_profile,
            self.last_search_jobs,
            replace(filters, minimum_score=0),
            location_prefiltered_job_ids=self.last_location_prefiltered_job_ids,
        )
        self.ranked_jobs = search_jobs(
            self.last_search_profile,
            self.last_search_jobs,
            filters,
            location_prefiltered_job_ids=self.last_location_prefiltered_job_ids,
        )
        self.last_search_filters = filters
        if self.ranked_jobs:
            self.empty_results_message = ""
        elif matching_before_threshold:
            maximum = max(item.match.score for item in matching_before_threshold)
            self.empty_results_message = (
                f"Порогом {threshold}% приховано {len(matching_before_threshold)} "
                f"вакансій. Найвища доступна оцінка: {maximum}%."
            )
        else:
            self.empty_results_message = (
                "Останній інтернет-пошук не повернув вакансій, тому зміна порога "
                "не може змінити список. Перевірте стан джерел над таблицею."
            )
        self._render_results()
        self.source_summary_var.set(
            self.source_diagnostics_prefix
            + f" | при порозі {threshold}% показано: {len(self.ranked_jobs)}"
        )
        self.status_var.set(
            f"Локальний поріг змінено на {threshold}% — без повторного запиту до сайтів"
        )

    def _mark_selected_result(self, status: ApplicationStatus) -> None:
        ranked = self._selected_result()
        if ranked is not None:
            self._set_status(ranked.job, status)

    def _set_status(
        self, job: JobPosting, status: ApplicationStatus, notes: str | None = None
    ) -> bool:
        existing = self.store.get_application(job.job_id)
        if status is ApplicationStatus.APPLIED and existing is not None:
            if existing.has_submission_history:
                date = existing.updated_at.astimezone().strftime("%d.%m.%Y %H:%M")
                proceed = messagebox.askyesno(
                    "Можлива повторна подача",
                    (
                        "На цю вакансію вже подавали заявку або вона має "
                        f"післяподачний статус.\n\nСтатус: {existing.status.value}\n"
                        f"Останнє оновлення: {date}\n\nПродовжити все одно?"
                    ),
                )
                if not proceed:
                    return False
        try:
            self.store.set_application_status(job.job_id, status, notes)
        except (OSError, ValueError) as error:
            messagebox.showerror("Не вдалося оновити статус", str(error))
            return False
        self._render_results()
        self._refresh_applications()
        self.status_var.set(f"{job.title}: {status.value}")
        return True

    def _refresh_applications(self) -> None:
        self.applications_tree.delete(*self.applications_tree.get_children())
        jobs = {job.job_id: job for job in self.store.list_jobs()}
        for application in sorted(
            self.store.list_applications(), key=lambda item: item.updated_at, reverse=True
        ):
            job = jobs.get(application.job_id)
            self.applications_tree.insert(
                "",
                END,
                iid=application.job_id,
                values=(
                    job.title if job else application.job_id,
                    job.company if job else "—",
                    application.status.value,
                    application.updated_at.astimezone().strftime("%d.%m.%Y %H:%M"),
                    job.source if job else "—",
                ),
            )

    def _show_application_history(self, _event: object | None = None) -> None:
        selection = self.applications_tree.selection()
        if not selection:
            return
        application = self.store.get_application(selection[0])
        if application is None:
            return
        lines = [f"Поточний статус: {application.status.value}"]
        if application.notes:
            lines.append(f"Нотатка: {application.notes}")
        lines.append("\nПодії:")
        for event in application.history:
            timestamp = event.occurred_at.astimezone().strftime("%d.%m.%Y %H:%M")
            note = f" — {event.notes}" if event.notes else ""
            lines.append(f"• {timestamp}: {event.status.value}{note}")
        self._set_text(self.application_history, "\n".join(lines))

    def _update_application_status(self) -> None:
        selection = self.applications_tree.selection()
        if not selection:
            messagebox.showwarning("JobCompass", "Спочатку виберіть заявку.")
            return
        job = self.store.get_job(selection[0])
        if job is None:
            messagebox.showerror("JobCompass", "Вакансію для заявки не знайдено.")
            return
        status = ApplicationStatus(self.application_status_var.get())
        notes = self.application_notes_var.get().strip() or None
        if self._set_status(job, status, notes):
            self.application_notes_var.set("")
            self.applications_tree.selection_set(job.job_id)
            self._show_application_history()

    @staticmethod
    def _set_text(widget: Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", END)
        widget.insert("1.0", value)
        widget.configure(state="disabled")


class ApplicationPreparationDialog:
    def __init__(self, app: JobCompassApp, ranked: RankedJob) -> None:
        self.app = app
        self.ranked = ranked
        self.window = Toplevel(app.root)
        self.window.title("Підготовка заявки")
        self.window.geometry("620x390")
        self.window.resizable(False, False)
        self.window.transient(app.root)
        self.window.grab_set()

        container = ttk.Frame(self.window, padding=18)
        container.pack(fill="both", expand=True)
        ttk.Label(
            container,
            text=f"{ranked.job.title} — {ranked.job.company}",
            style="Heading.TLabel",
            wraplength=570,
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            container,
            text=(
                f"Релевантність: {ranked.match.score}%. Оберіть, як підготувати "
                "заявку для цієї конкретної вакансії."
            ),
            wraplength=570,
        ).pack(anchor="w", pady=(0, 14))

        self.choice_var = StringVar(value="draft")
        options = (
            (
                "draft",
                "Створити локальну чернетку супровідного листа",
                "Лист формується з підтверджених даних профілю та вимог вакансії.",
            ),
            (
                "ai",
                "Безкоштовний режим: створити промпт для AI",
                (
                    "Промпт поєднає оброблені дані резюме, повний контекст "
                    "вакансії, збіги та правила проти вигадування фактів."
                ),
            ),
            (
                "none",
                "Продовжити без супровідного листа",
                "Відкрити сторінку вакансії без генерації листа або промпту.",
            ),
        )
        for value, title, description in options:
            option = ttk.Frame(container)
            option.pack(fill="x", pady=5)
            ttk.Radiobutton(
                option,
                text=title,
                variable=self.choice_var,
                value=value,
            ).pack(anchor="w")
            ttk.Label(
                option,
                text=description,
                foreground="#555555",
                wraplength=535,
            ).pack(anchor="w", padx=(24, 0))

        buttons = ttk.Frame(container)
        buttons.pack(fill="x", side="bottom", pady=(14, 0))
        ttk.Button(buttons, text="Скасувати", command=self.window.destroy).pack(
            side="right"
        )
        ttk.Button(
            buttons,
            text="Продовжити",
            command=self._continue,
            style="Primary.TButton",
        ).pack(side="right", padx=(0, 8))

    def _continue(self) -> None:
        choice = self.choice_var.get()
        self.window.grab_release()
        self.window.destroy()
        if choice in {"draft", "ai"}:
            CoverLetterDialog(self.app, self.ranked, initial_tab=choice)
            return
        if not self.app._open_job_for(self.ranked.job):
            return
        submitted = messagebox.askyesno(
            "Підтвердження відправлення",
            (
                "Сторінку вакансії відкрито у браузері.\n\n"
                "Натисніть «Так» лише після фактичного успішного відправлення "
                "заявки. Якщо ви ще не відправили її, натисніть «Ні»."
            ),
        )
        if submitted:
            self.app._set_status(
                self.ranked.job,
                ApplicationStatus.APPLIED,
                "Submitted without a cover letter",
            )


class CoverLetterDialog:
    def __init__(
        self, app: JobCompassApp, ranked: RankedJob, initial_tab: str = "draft"
    ) -> None:
        self.app = app
        self.ranked = ranked
        self.window = Toplevel(app.root)
        self.window.title(f"Супровідний лист — {ranked.job.title}")
        self.window.geometry("940x760")
        self.window.minsize(820, 650)
        self.window.transient(app.root)
        saved = app.store.get_cover_letter_preparation(ranked.job.job_id)

        container = ttk.Frame(self.window, padding=12)
        container.pack(fill="both", expand=True)
        ttk.Label(
            container,
            text=f"{ranked.job.title} — {ranked.job.company}",
            style="Heading.TLabel",
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            container,
            text=(
                "Чернетка та промпт використовують лише підтверджені дані. "
                "Обов’язково перевірте текст перед відправленням."
            ),
            wraplength=800,
        ).pack(anchor="w", pady=(0, 8))

        options_frame = ttk.LabelFrame(
            container, text="Параметри майбутнього листа", padding=8
        )
        options_frame.pack(fill="x", pady=(0, 8))
        options_frame.columnconfigure(5, weight=1)

        ttk.Label(options_frame, text="Мова").grid(row=0, column=0, sticky="w")
        language_label = {
            "auto": "Автоматично",
            "de": "Deutsch",
            "en": "English",
        }.get(saved.language if saved else "auto", "Автоматично")
        self.letter_language_var = StringVar(value=language_label)
        ttk.Combobox(
            options_frame,
            textvariable=self.letter_language_var,
            values=("Автоматично", "Deutsch", "English"),
            state="readonly",
            width=15,
        ).grid(row=0, column=1, sticky="w", padx=(6, 16))
        detected = (
            "Deutsch" if suggested_letter_language(ranked.job) == "de" else "English"
        )
        ttk.Label(
            options_frame,
            text=f"Визначено: {detected}",
            foreground="#555555",
        ).grid(row=0, column=2, sticky="w", padx=(0, 18))

        ttk.Label(options_frame, text="Тон").grid(row=0, column=3, sticky="w")
        tone_label = next(
            (
                label
                for label, value in _LETTER_TONES.items()
                if value == (saved.tone if saved else "professional")
            ),
            "Професійний",
        )
        self.letter_tone_var = StringVar(value=tone_label)
        ttk.Combobox(
            options_frame,
            textvariable=self.letter_tone_var,
            values=tuple(_LETTER_TONES),
            state="readonly",
            width=20,
        ).grid(row=0, column=4, sticky="w", padx=(6, 16))

        ttk.Label(options_frame, text="Довжина").grid(row=0, column=5, sticky="e")
        length_label = next(
            (
                label
                for label, value in _LETTER_LENGTHS.items()
                if value == (saved.length if saved else "standard")
            ),
            "Стандартний (180–250 слів)",
        )
        self.letter_length_var = StringVar(value=length_label)
        ttk.Combobox(
            options_frame,
            textvariable=self.letter_length_var,
            values=tuple(_LETTER_LENGTHS),
            state="readonly",
            width=26,
        ).grid(row=0, column=6, sticky="e", padx=(6, 0))

        ttk.Label(
            options_frame,
            text=(
                "Особистий акцент або мотивація (необов’язково; вводьте лише "
                "правдиві факти)"
            ),
        ).grid(row=1, column=0, columnspan=7, sticky="w", pady=(8, 3))
        self.letter_focus_text = Text(options_frame, height=3, wrap="word")
        self.letter_focus_text.grid(row=2, column=0, columnspan=7, sticky="ew")
        if saved and saved.focus:
            self.letter_focus_text.insert("1.0", saved.focus)
        ttk.Button(
            options_frame, text="Оновити тексти", command=self._regenerate
        ).grid(row=3, column=6, sticky="e", pady=(6, 0))

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)
        draft_frame = ttk.Frame(notebook, padding=8)
        prompt_frame = ttk.Frame(notebook, padding=8)
        evidence_frame = ttk.Frame(notebook, padding=8)
        notebook.add(draft_frame, text="Локальна чернетка")
        notebook.add(prompt_frame, text="Безкоштовний AI-промпт")
        notebook.add(evidence_frame, text="Використані дані й прогалини")
        if initial_tab == "ai":
            notebook.select(prompt_frame)
        draft_frame.rowconfigure(0, weight=1)
        draft_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(0, weight=1)
        prompt_frame.columnconfigure(0, weight=1)
        evidence_frame.rowconfigure(0, weight=1)
        evidence_frame.columnconfigure(0, weight=1)

        self.draft_text = Text(draft_frame, wrap="word", font=("Segoe UI", 10))
        self.draft_text.grid(row=0, column=0, sticky="nsew")
        self.prompt_text = Text(prompt_frame, wrap="word", font=("Consolas", 9))
        self.prompt_text.grid(row=0, column=0, sticky="nsew")
        self.evidence_text = Text(
            evidence_frame, wrap="word", font=("Segoe UI", 10), state="disabled"
        )
        self.evidence_text.grid(row=0, column=0, sticky="nsew")
        for frame, widget in (
            (draft_frame, self.draft_text),
            (prompt_frame, self.prompt_text),
            (evidence_frame, self.evidence_text),
        ):
            scrollbar = ttk.Scrollbar(
                frame, orient="vertical", command=widget.yview
            )
            widget.configure(yscrollcommand=scrollbar.set)
            scrollbar.grid(row=0, column=1, sticky="ns")
        if saved:
            self.draft_text.insert("1.0", saved.draft)
            self.prompt_text.insert("1.0", saved.prompt)
            self._set_evidence_text(saved.evidence_summary)
        else:
            self._regenerate()

        buttons = ttk.Frame(container)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(
            buttons,
            text="Скопіювати чернетку",
            command=lambda: self._copy(self.draft_text),
        ).pack(side="left")
        ttk.Button(
            buttons,
            text="Скопіювати AI-промпт",
            command=lambda: self._copy(self.prompt_text),
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            buttons,
            text="Зберегти локально",
            command=self._save_preparation,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            buttons, text="Позначити Draft", command=self._mark_draft
        ).pack(side="right")
        ttk.Button(
            buttons,
            text="Підтвердити відправлення",
            command=self._confirm_submitted,
            style="Primary.TButton",
        ).pack(side="right", padx=(0, 6))
        ttk.Button(
            buttons,
            text="Відкрити вакансію",
            command=lambda: self.app._open_job_for(self.ranked.job),
        ).pack(side="right", padx=(0, 6))

    def _copy(self, widget: Text) -> None:
        value = widget.get("1.0", "end-1c")
        self.window.clipboard_clear()
        self.window.clipboard_append(value)
        self.app.status_var.set("Текст скопійовано в буфер обміну")

    def _selected_language(self) -> str:
        return {
            "Автоматично": "auto",
            "Deutsch": "de",
            "English": "en",
        }[self.letter_language_var.get()]

    def _selected_tone(self) -> str:
        return _LETTER_TONES.get(
            self.letter_tone_var.get(), "professional"
        )

    def _selected_length(self) -> str:
        return _LETTER_LENGTHS.get(
            self.letter_length_var.get(), "standard"
        )

    def _focus(self) -> str:
        return self.letter_focus_text.get("1.0", "end-1c").strip()

    def _set_evidence_text(self, value: str) -> None:
        self.evidence_text.configure(state="normal")
        self.evidence_text.delete("1.0", END)
        self.evidence_text.insert("1.0", value)
        self.evidence_text.configure(state="disabled")

    def _regenerate(self) -> None:
        language = self._selected_language()
        focus = self._focus()
        self.draft_text.delete("1.0", END)
        self.draft_text.insert(
            "1.0",
            build_cover_letter_draft(
                self.app.profile, self.ranked.job, self.ranked.match, language
            ),
        )
        self.prompt_text.delete("1.0", END)
        self.prompt_text.insert(
            "1.0",
            build_ai_prompt(
                self.app.profile,
                self.ranked.job,
                self.ranked.match,
                language,
                tone=self._selected_tone(),
                length=self._selected_length(),
                focus=focus,
            ),
        )
        self._set_evidence_text(
            build_evidence_summary(
                self.app.profile,
                self.ranked.job,
                self.ranked.match,
                focus=focus,
            )
        )

    def _save_preparation(self, show_confirmation: bool = True) -> bool:
        preparation = CoverLetterPreparation(
            job_id=self.ranked.job.job_id,
            draft=self.draft_text.get("1.0", "end-1c"),
            prompt=self.prompt_text.get("1.0", "end-1c"),
            evidence_summary=self.evidence_text.get("1.0", "end-1c"),
            language=self._selected_language(),
            tone=self._selected_tone(),
            length=self._selected_length(),
            focus=self._focus(),
        )
        try:
            self.app.store.save_cover_letter_preparation(preparation)
        except (OSError, ValueError) as error:
            messagebox.showerror("Не вдалося зберегти", str(error))
            return False
        self.app.status_var.set(
            f"Супровідні матеріали збережено: {self.ranked.job.title}"
        )
        if show_confirmation:
            messagebox.showinfo(
                "Збережено",
                "Чернетку, промпт і вибрані параметри збережено локально.",
            )
        return True

    def _mark_draft(self) -> None:
        if not self._save_preparation(show_confirmation=False):
            return
        if self.app._set_status(
            self.ranked.job,
            ApplicationStatus.DRAFT,
            "Vacancy-specific cover letter draft created",
        ):
            self._copy(self.draft_text)
            self.window.destroy()

    def _confirm_submitted(self) -> None:
        confirmed = messagebox.askyesno(
            "Підтвердження відправлення",
            (
                "Підтверджуєте, що заявка на цю вакансію фактично й успішно "
                "відправлена?"
            ),
        )
        if confirmed and self._save_preparation(
            show_confirmation=False
        ) and self.app._set_status(
            self.ranked.job,
            ApplicationStatus.APPLIED,
            "Application submitted after cover-letter preparation",
        ):
            self.window.destroy()


def launch_gui(data_path: str | Path = DEFAULT_DATA_PATH) -> int:
    root = Tk()
    JobCompassApp(root, data_path)
    root.mainloop()
    return 0
