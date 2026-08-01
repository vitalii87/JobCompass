"""Tkinter desktop interface for the local JobCompass application."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from tkinter import (
    BooleanVar,
    DoubleVar,
    END,
    StringVar,
    Text,
    Tk,
    Toplevel,
    filedialog,
    messagebox,
)
from tkinter import ttk

from app.core.models import ApplicationStatus, CandidateProfile, JobPosting
from app.core.search import RankedJob, SearchFilters, search_jobs
from app.services import build_ai_prompt, build_cover_letter_draft, load_resume
from app.sources import JsonFileSource, SearchQuery
from app.storage import LocalJsonStore


DEFAULT_DATA_PATH = Path("data/jobcompass.json")

_COMPONENT_LABELS = {
    "skills": "Навички",
    "role": "Професія",
    "experience": "Досвід",
    "languages": "Мови",
    "location": "Локація",
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

        self.root.title("JobCompass")
        self.root.geometry("1180x760")
        self.root.minsize(960, 640)
        self._configure_style()

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

        form = ttk.LabelFrame(self.profile_tab, text="Підтверджені дані", padding=12)
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
        ttk.Button(
            header,
            text="Імпортувати вакансії JSON",
            command=self._import_jobs,
        ).pack(side="right")

        notice = ttk.Label(
            self.search_tab,
            text=(
                "Зараз пошук працює серед локально імпортованих вакансій. "
                "Онлайн-конектори з’являться окремими платформами."
            ),
            wraplength=900,
        )
        notice.grid(row=1, column=0, sticky="w", pady=(0, 10))

        content = ttk.Frame(self.search_tab)
        content.grid(row=2, column=0, sticky="nsew")
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        self.sources_frame = ttk.LabelFrame(
            content, text="Платформи / джерела", padding=12
        )
        self.sources_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 8))

        filters = ttk.LabelFrame(content, text="Фільтри", padding=12)
        filters.grid(row=0, column=1, sticky="nsew")
        filters.columnconfigure(1, weight=1)
        self.keyword_var = StringVar()
        self.location_var = StringVar()
        self.excluded_keyword_var = StringVar()
        self.excluded_company_var = StringVar()
        self.minimum_score_var = DoubleVar(value=0)
        self.filter_remote_var = BooleanVar(value=False)

        filter_rows = (
            ("Ключові слова", self.keyword_var),
            ("Локації", self.location_var),
            ("Виключити слова", self.excluded_keyword_var),
            ("Виключити компанії", self.excluded_company_var),
        )
        for row, (label, variable) in enumerate(filter_rows):
            ttk.Label(filters, text=label).grid(row=row, column=0, sticky="w", pady=5)
            ttk.Entry(filters, textvariable=variable).grid(
                row=row, column=1, sticky="ew", padx=(12, 0), pady=5
            )
        ttk.Checkbutton(
            filters, text="Тільки remote", variable=self.filter_remote_var
        ).grid(row=4, column=1, sticky="w", padx=(12, 0), pady=5)
        ttk.Label(filters, text="Мінімальна релевантність").grid(
            row=5, column=0, sticky="w", pady=5
        )
        score_frame = ttk.Frame(filters)
        score_frame.grid(row=5, column=1, sticky="ew", padx=(12, 0), pady=5)
        score_frame.columnconfigure(0, weight=1)
        ttk.Scale(
            score_frame,
            from_=0,
            to=100,
            variable=self.minimum_score_var,
            command=lambda value: self.minimum_score_label.configure(
                text=f"{round(float(value))}%"
            ),
        ).grid(row=0, column=0, sticky="ew")
        self.minimum_score_label = ttk.Label(score_frame, text="0%", width=5)
        self.minimum_score_label.grid(row=0, column=1, padx=(8, 0))

        ttk.Button(
            filters,
            text="Знайти й оцінити вакансії",
            command=self._run_search,
            style="Primary.TButton",
        ).grid(row=6, column=1, sticky="e", padx=(12, 0), pady=(20, 0))

    def _build_results_tab(self) -> None:
        self.results_tab.columnconfigure(0, weight=1)
        self.results_tab.rowconfigure(1, weight=1)
        toolbar = ttk.Frame(self.results_tab)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(toolbar, text="Релевантні вакансії", style="Heading.TLabel").pack(
            side="left"
        )
        ttk.Button(toolbar, text="Відкрити вакансію", command=self._open_job).pack(
            side="right"
        )
        ttk.Button(
            toolbar, text="Лист / AI-промпт", command=self._show_cover_letter
        ).pack(side="right", padx=(0, 6))
        ttk.Button(
            toolbar,
            text="Позначити Applied",
            command=lambda: self._mark_selected_result(ApplicationStatus.APPLIED),
        ).pack(side="right", padx=(0, 6))
        ttk.Button(
            toolbar,
            text="Цікаво",
            command=lambda: self._mark_selected_result(ApplicationStatus.INTERESTING),
        ).pack(side="right", padx=(0, 6))

        panes = ttk.Panedwindow(self.results_tab, orient="vertical")
        panes.grid(row=1, column=0, sticky="nsew")
        table_frame = ttk.Frame(panes)
        detail_frame = ttk.LabelFrame(panes, text="Пояснення відповідності", padding=8)
        panes.add(table_frame, weight=3)
        panes.add(detail_frame, weight=2)

        columns = ("score", "title", "company", "location", "source", "skills", "status")
        self.results_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )
        headings = {
            "score": "Match",
            "title": "Вакансія",
            "company": "Компанія",
            "location": "Локація",
            "source": "Джерело",
            "skills": "Ключові збіги",
            "status": "Статус",
        }
        widths = {
            "score": 70,
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
                anchor="center" if column in {"score", "status"} else "w",
            )
        table_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.results_tree.yview
        )
        self.results_tree.configure(yscrollcommand=table_scroll.set)
        self.results_tree.pack(side="left", fill="both", expand=True)
        table_scroll.pack(side="right", fill="y")
        self.results_tree.bind("<<TreeviewSelect>>", self._show_result_details)
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
                "Вакансії: локальний нормалізований JSON — доступно.\n"
                "Резюме: JSON, TXT, DOCX — доступно; PDF — заплановано.\n"
                "Онлайн-платформи — ще не підключені.\n"
                "AI: зовнішні виклики відсутні; можна лише скопіювати промпт."
            ),
            justify="left",
        ).grid(row=0, column=0, sticky="w")

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
                ("Підтримувані резюме", "*.json *.txt *.docx"),
                ("JSON", "*.json"),
                ("Text", "*.txt"),
                ("Word", "*.docx"),
                ("PDF — ще не підтримується", "*.pdf"),
                ("Усі файли", "*.*"),
            ),
        )
        if not path:
            return
        try:
            result = load_resume(path)
        except (OSError, ValueError) as error:
            messagebox.showerror("Не вдалося прочитати резюме", str(error))
            return
        self._populate_profile(result.profile)
        self.resume_path_var.set(str(Path(path).resolve()))
        self._set_text(self.resume_preview, result.raw_text)
        self.status_var.set("Резюме завантажено — перевірте та збережіть профіль")
        if result.warnings:
            messagebox.showwarning("Потрібна перевірка", "\n\n".join(result.warnings))

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
        sources = sorted({job.source for job in self.store.list_jobs()}, key=str.casefold)
        self.source_vars = {}
        if not sources:
            ttk.Label(
                self.sources_frame,
                text="Немає імпортованих\nджерел вакансій",
                justify="left",
            ).pack(anchor="w")
            return
        for source in sources:
            variable = BooleanVar(value=previous.get(source, True))
            self.source_vars[source] = variable
            ttk.Checkbutton(
                self.sources_frame, text=source, variable=variable
            ).pack(anchor="w", pady=2)

    def _run_search(self) -> None:
        try:
            profile = self._profile_from_form()
            selected_sources = tuple(
                source for source, variable in self.source_vars.items() if variable.get()
            )
            if self.source_vars and not selected_sources:
                raise ValueError("Оберіть хоча б одне джерело вакансій")
            filters = SearchFilters(
                sources=selected_sources,
                keywords=_split_list(self.keyword_var.get()),
                locations=_split_list(self.location_var.get()),
                excluded_keywords=_split_list(self.excluded_keyword_var.get()),
                excluded_companies=_split_list(self.excluded_company_var.get()),
                remote_only=self.filter_remote_var.get(),
                minimum_score=round(self.minimum_score_var.get()),
            )
            self.ranked_jobs = search_jobs(profile, self.store.list_jobs(), filters)
        except (OSError, ValueError) as error:
            messagebox.showerror("Пошук не виконано", str(error))
            return
        self.profile = profile
        self._render_results()
        self.notebook.select(self.results_tab)
        self.status_var.set(f"Знайдено вакансій: {len(self.ranked_jobs)}")

    def _render_results(self) -> None:
        self.results_tree.delete(*self.results_tree.get_children())
        self.result_by_id = {item.job.job_id: item for item in self.ranked_jobs}
        applications = {
            item.job_id: item.status.value for item in self.store.list_applications()
        }
        for ranked in self.ranked_jobs:
            job = ranked.job
            result = ranked.match
            self.results_tree.insert(
                "",
                END,
                iid=job.job_id,
                values=(
                    f"{result.score}%",
                    job.title,
                    job.company,
                    "Remote" if job.remote is True else job.location,
                    job.source,
                    ", ".join(result.matched_skills[:4]),
                    applications.get(job.job_id, ApplicationStatus.FOUND.value),
                ),
                tags=(result.level.value,),
            )
        if self.ranked_jobs:
            first_id = self.ranked_jobs[0].job.job_id
            self.results_tree.selection_set(first_id)
            self.results_tree.focus(first_id)
            self._show_result_details()
        else:
            self._set_text(
                self.result_details,
                "Немає вакансій, що відповідають вибраним фільтрам.",
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
            f"Джерело: {job.source}",
            f"Локація: {'Remote' if job.remote is True else job.location or 'не вказана'}",
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
        if job.description:
            lines.append("\nОпис:\n" + job.description)
        self._set_text(self.result_details, "\n".join(lines))

    def _open_job(self) -> None:
        ranked = self._selected_result()
        if ranked is None:
            return
        if not ranked.job.url:
            messagebox.showwarning("JobCompass", "Для вакансії немає посилання.")
            return
        webbrowser.open(ranked.job.url)

    def _show_cover_letter(self) -> None:
        ranked = self._selected_result()
        if ranked is None:
            return
        CoverLetterDialog(self, ranked)

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


class CoverLetterDialog:
    def __init__(self, app: JobCompassApp, ranked: RankedJob) -> None:
        self.app = app
        self.ranked = ranked
        self.window = Toplevel(app.root)
        self.window.title(f"Супровідний лист — {ranked.job.title}")
        self.window.geometry("850x650")
        self.window.transient(app.root)

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

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)
        draft_frame = ttk.Frame(notebook, padding=8)
        prompt_frame = ttk.Frame(notebook, padding=8)
        notebook.add(draft_frame, text="Локальна чернетка")
        notebook.add(prompt_frame, text="AI-промпт")
        draft_frame.rowconfigure(0, weight=1)
        draft_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(0, weight=1)
        prompt_frame.columnconfigure(0, weight=1)

        self.draft_text = Text(draft_frame, wrap="word", font=("Segoe UI", 10))
        self.draft_text.grid(row=0, column=0, sticky="nsew")
        self.draft_text.insert(
            "1.0", build_cover_letter_draft(app.profile, ranked.job, ranked.match)
        )
        self.prompt_text = Text(prompt_frame, wrap="word", font=("Consolas", 9))
        self.prompt_text.grid(row=0, column=0, sticky="nsew")
        self.prompt_text.insert(
            "1.0", build_ai_prompt(app.profile, ranked.job, ranked.match)
        )

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
            buttons, text="Позначити Draft", command=self._mark_draft
        ).pack(side="right")

    def _copy(self, widget: Text) -> None:
        value = widget.get("1.0", "end-1c")
        self.window.clipboard_clear()
        self.window.clipboard_append(value)
        self.app.status_var.set("Текст скопійовано в буфер обміну")

    def _mark_draft(self) -> None:
        text = self.draft_text.get("1.0", "end-1c").strip()
        if self.app._set_status(
            self.ranked.job, ApplicationStatus.DRAFT, "Cover letter draft created"
        ):
            self._copy(self.draft_text)
            self.window.destroy()


def launch_gui(data_path: str | Path = DEFAULT_DATA_PATH) -> int:
    root = Tk()
    JobCompassApp(root, data_path)
    root.mainloop()
    return 0
