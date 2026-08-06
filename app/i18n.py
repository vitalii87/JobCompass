"""Small standard-library runtime localization for the desktop interface."""

from __future__ import annotations

from tkinter import StringVar
from typing import Any


DEFAULT_LANGUAGE = "uk"
LANGUAGE_LABELS = {"uk": "Українська", "en": "English"}
_language = DEFAULT_LANGUAGE
_localized_variables: set[str] = set()


_UK_TO_EN = {
    # Main navigation and shared controls.
    "Українська": "Ukrainian",
    "Профіль": "Profile",
    "Пошук": "Search",
    "За розкладом (0)": "Scheduled (0)",
    "Результати": "Results",
    "Мої заявки": "My applications",
    "Налаштування": "Settings",
    "Готово": "Ready",
    "Активний профіль:": "Active profile:",
    "Новий профіль": "New profile",
    "Редагувати": "Edit",
    "Гостьовий режим": "Guest mode",
    "Гостьовий режим (без збереження)": "Guest mode (not saved)",
    "Локальний пошук, оцінювання та відстеження вакансій": (
        "Local job search, matching, and application tracking"
    ),
    "Скасувати": "Cancel",
    "Продовжити": "Continue",
    "Зберегти": "Save",
    "Оновити": "Update",
    "Видалити": "Delete",
    "Імпортувати": "Import",
    "Експортувати": "Export",
    "Дублювати": "Duplicate",
    "Перейменувати": "Rename",
    "Копіювати": "Copy",
    "Вставити": "Paste",
    "Вирізати": "Cut",
    "Виділити все": "Select all",
    "Так": "Yes",
    "Ні": "No",
    "Не вказано": "Not specified",
    "не вказано": "not specified",
    "—": "—",

    # Profile.
    "Профіль кандидата": "Candidate profile",
    "Дані з резюме — усі поля необов’язкові": (
        "Resume data — all fields are optional"
    ),
    "Ім’я": "Name",
    "Телефон": "Phone",
    "Бажані професії": "Target roles",
    "Бажані посади": "Target roles",
    "Навички": "Skills",
    "Мови": "Languages",
    "Роки досвіду": "Years of experience",
    "Бажані локації": "Preferred locations",
    "Короткий профіль": "Short profile",
    "Шукаю лише віддалену роботу": "I am looking for remote work only",
    "Зберегти профіль": "Save profile",
    "Зберегти як профіль": "Save as profile",
    "Завантажити резюме": "Load resume",
    "Резюме": "Resume",
    "Резюме ще не завантажено": "No resume loaded yet",
    "Текст резюме — лише для перевірки": "Resume text — preview only",
    "Підтримувані резюме": "Supported resumes",
    "Резюме готове до використання": "Resume is ready to use",
    "Резюме не знайдено": "Resume not found",
    "Оберіть резюме": "Select a resume",
    "Оберіть оригінальний файл резюме": "Select the original resume file",
    "Оберіть актуальний оригінальний файл резюме.": (
        "Select the current original resume file."
    ),
    "Роки досвіду повинні бути числом": "Years of experience must be a number",
    "JobCompass шукає актуальні вакансії у вибраних інтернет-джерелах, об’єднує дублікати та оцінює відповідність резюме.": (
        "JobCompass searches selected online sources for current jobs, merges "
        "duplicates, and evaluates resume fit."
    ),

    # Search and locations.
    "Пошук вакансій": "Job search",
    "Платформи / джерела": "Platforms / sources",
    "Фільтри": "Filters",
    "Додаткові вимоги (не міста)": "Additional requirements (not cities)",
    "Локації (міста) *": "Locations (cities) *",
    "Країна підказок": "Suggestion country",
    "Вибрані міста:": "Selected cities:",
    "Додати введене без перевірки": "Add entered city without verification",
    "Видалити вибране": "Remove selected",
    "Радіус": "Radius",
    "Без радіуса": "No radius",
    "без радіуса": "no radius",
    "Виключити слова": "Exclude words",
    "Виключити компанії": "Exclude companies",
    "Тільки remote (якщо вимкнено — remote, hybrid, office та невідомий формат)": (
        "Remote only (when off: remote, hybrid, office, and unknown)"
    ),
    "Мінімальна релевантність": "Minimum match",
    "Знайти вакансії в інтернеті": "Find jobs online",
    "Зберегти параметри": "Save settings",
    "Через кому.": "Comma-separated.",
    "Усі країни": "All countries",
    "Шукаю відповідні міста…": "Searching for matching cities…",
    "Знайдено варіантів: ": "Suggestions found: ",
    "Спочатку введіть назву міста.": "Enter a city name first.",
    "Місто вже вибрано: ": "City already selected: ",
    "Підказки міст тимчасово недоступні. Місто можна додати вручну.": (
        "City suggestions are temporarily unavailable. You can add the city manually."
    ),
    "Для інтернет-пошуку вкажіть хоча б одну бажану посаду": (
        "Enter at least one target role for online search"
    ),
    "Оберіть хоча б одне джерело вакансій": "Select at least one job source",
    "Пошук виконується": "Search in progress",
    "Пошук не виконано": "Search was not completed",
    "Триває новий пошук вакансій…": "A new job search is running…",
    "Джерела: пошук ще не запускався": "Sources: search has not run yet",
    "Джерела: виконується новий пошук; попередні результати очищено": (
        "Sources: running a new search; previous results were cleared"
    ),
    "Через кому; кожна повна назва — окрема альтернатива (АБО / OR). Пишіть «Administrative Assistant», а не «Administrative, Assistant».": (
        "Separate roles with commas; each complete title is an alternative "
        "(OR). Enter ‘Administrative Assistant’, not ‘Administrative, Assistant’."
    ),
    "Необов’язково. Напр.: SAP, Excel. Усі мають збігтися (І / AND).": (
        "Optional. Example: SAP, Excel. Every requirement must match (AND)."
    ),
    "Обов’язково. Введіть назву, оберіть точне місто з підказки; можна додати кілька міст, вони працюють як АБО / OR.": (
        "Required. Enter a name and select the exact city from the suggestions; "
        "you can add several cities, which are combined with OR."
    ),
    "Почніть вводити щонайменше 2–3 літери й оберіть місто зі списку.": (
        "Enter at least 2–3 letters and select a city from the list."
    ),
    "Один радіус застосовується окремо до кожного вибраного міста. Bundesagentur передає його серверу; джерела без геопошуку можуть фільтрувати лише за назвою.": (
        "The radius is applied separately to each selected city. Bundesagentur "
        "sends it to its server; sources without geosearch may filter by name only."
    ),
    "Ctrl+Enter — почати пошук; Enter/Space — натиснути вибрану кнопку": (
        "Ctrl+Enter — start search; Enter/Space — activate the focused button"
    ),

    # Results.
    "Релевантні вакансії": "Matching jobs",
    "Вакансій у списку: 0": "Jobs in list: 0",
    "Вакансій у списку: ": "Jobs in list: ",
    "Цікаво": "Interesting",
    "Підготувати / подати заявку": "Prepare / submit application",
    "Відкрити вакансію": "Open job",
    "Відкрити вибрану вакансію": "Open selected job",
    "Match": "Match",
    "Вакансія": "Job",
    "Компанія": "Company",
    "Локація": "Location",
    "Джерело": "Source",
    "Ключові збіги": "Key matches",
    "Статус": "Status",
    "Пояснення відповідності": "Match explanation",
    "Сортування:": "Sort:",
    "За релевантністю": "By relevance",
    "Найновіші спочатку": "Newest first",
    "Найстаріші спочатку": "Oldest first",
    "Немає вакансій, що відповідають вибраним фільтрам.": (
        "No jobs match the selected filters."
    ),
    "Виберіть вакансію зі списку.": "Select a job from the list.",
    "Для вакансії немає посилання.": "This job has no link.",
    "Формат роботи: ": "Work mode: ",
    "Опубліковано: ": "Published: ",
    "Посилання: ": "Link: ",
    "Збігаються: ": "Matched: ",
    "Бракує обов’язкових: ": "Missing required: ",
    "Ризики:": "Risks:",
    "Компоненти оцінювання:": "Scoring components:",
    "Повнота доказів для оцінювання: ": "Evidence coverage: ",

    # Scheduling.
    "Пошук за розкладом": "Scheduled search",
    "Щоденний автоматичний пошук": "Daily automatic search",
    "Увімкнути для активного профілю": "Enable for active profile",
    "Час:": "Time:",
    "Зберегти розклад": "Save schedule",
    "Розклад не налаштовано": "Schedule is not configured",
    "Нові та ще не переглянуті вакансії": "New and unseen jobs",
    "Позначити всі переглянутими": "Mark all as seen",
    "Запустити зараз": "Run now",
    "Опубліковано": "Published",
    "Останній запуск: ": "Last run: ",
    "Усі вакансії позначено переглянутими": "All jobs marked as seen",
    "Гостьовий режим: створіть профіль, щоб увімкнути розклад.": (
        "Guest mode: create a profile to enable scheduled search."
    ),
    "Пошук використовує збережені посади, міста, джерела та фільтри цього профілю. Якщо програма була закрита, прострочений пошук запуститься після наступного відкриття.": (
        "Scheduled search uses this profile’s saved roles, cities, sources, and "
        "filters. If the application was closed, an overdue search will run the "
        "next time it opens."
    ),

    # Applications and cover letters.
    "Історія заявок": "Application history",
    "Історія статусів": "Status history",
    "Новий статус": "New status",
    "Поточний статус: ": "Current status: ",
    "Підготовка заявки": "Application preparation",
    "Релевантність: ": "Match: ",
    "Оберіть, як підготувати заявку для цієї конкретної вакансії.": (
        "Choose how to prepare an application for this specific job."
    ),
    "Створити локальну чернетку супровідного листа": (
        "Create a local cover-letter draft"
    ),
    "Безкоштовний режим: створити промпт для AI": (
        "Free mode: create a prompt for AI"
    ),
    "Продовжити без супровідного листа": "Continue without a cover letter",
    "Використати збережений супровідний лист": "Use saved cover letter",
    "Лист формується з підтверджених даних профілю та вимог вакансії.": (
        "The letter is created from verified profile data and job requirements."
    ),
    "Промпт поєднає оброблені дані резюме, повний контекст вакансії, збіги та правила проти вигадування фактів.": (
        "The prompt combines processed resume data, the full job context, matches, "
        "and rules against inventing facts."
    ),
    "Відкрити сторінку вакансії без генерації листа або промпту.": (
        "Open the job page without generating a letter or prompt."
    ),
    "Перейти до перевірки матеріалів із раніше збереженим листом.": (
        "Review the application materials with the previously saved letter."
    ),
    "Локальна чернетка": "Local draft",
    "Безкоштовний AI-промпт": "Free AI prompt",
    "Використані дані й прогалини": "Used data and gaps",
    "Параметри майбутнього листа": "Future letter settings",
    "Мова": "Language",
    "Автоматично": "Automatic",
    "Тон": "Tone",
    "Професійний": "Professional",
    "Теплий і особистий": "Warm and personal",
    "Лаконічний": "Concise",
    "Довжина": "Length",
    "Короткий (140–180 слів)": "Short (140–180 words)",
    "Стандартний (180–250 слів)": "Standard (180–250 words)",
    "Розгорнутий (250–320 слів)": "Detailed (250–320 words)",
    "Оновити тексти": "Regenerate texts",
    "Скопіювати чернетку": "Copy draft",
    "Скопіювати AI-промпт": "Copy AI prompt",
    "Зберегти локально": "Save locally",
    "Позначити Draft": "Mark as Draft",
    "Перейти до відправлення": "Continue to submission",
    "Супровідний лист": "Cover letter",
    "Чернетка та промпт використовують лише підтверджені дані. Обов’язково перевірте текст перед відправленням.": (
        "The draft and prompt use verified data only. Always review the text "
        "before sending it."
    ),
    "Визначено: ": "Detected: ",
    "Особистий акцент або мотивація (необов’язково; вводьте лише правдиві факти)": (
        "Personal angle or motivation (optional; enter truthful facts only)"
    ),
    "Перевірка перед відправленням": "Pre-submission review",
    "Режим відправлення": "Submission mode",
    "З допомогою JobCompass — рекомендовано": "Assisted by JobCompass — recommended",
    "Ручне — лише відкрити сторінку вакансії": (
        "Manual — only open the job page"
    ),
    "Автоматичне — немає перевіреного конектора для цього джерела": (
        "Automatic — no verified connector for this source"
    ),
    "Матеріали заявки": "Application materials",
    "Контакт": "Contact",
    "Не заповнено — введіть дані на сайті": "Not provided — enter it on the site",
    "Обрати…": "Choose…",
    "Показати файл": "Show file",
    "Скопіювати лист": "Copy letter",
    "Почати відправлення": "Start submission",
    "Так, заявку успішно відправлено": "Yes, the application was submitted",
    "Можлива повторна подача": "Possible duplicate application",
    "Підтвердження відправлення": "Submission confirmation",
    "Автоматичний режим недоступний": "Automatic mode unavailable",
    "Немає посилання": "No link",
    "Оберіть резюме": "Select a resume",
    "Не вдалося підготувати заявку": "Could not prepare application",
    "Потрібен профіль": "Profile required",
    "Не вдалося зберегти відправлення": "Could not save submission",
    "Перевірте, що саме буде використано для заявки. JobCompass не позначить її відправленою без вашого окремого підтвердження.": (
        "Review exactly what will be used for the application. JobCompass will not "
        "mark it as submitted without your separate confirmation."
    ),
    "Лист копіюється, папка з резюме та сторінка вакансії відкриваються.": (
        "The letter is copied, and the resume folder and job page are opened."
    ),
    "До форми прикріплюється оригінальний файл. Розпарсений текст використовується лише локально й роботодавцю не надсилається.": (
        "Attach the original file to the form. Parsed text is used locally only and "
        "is not sent to the employer."
    ),
    "⚠ На цю вакансію вже подавали заявку. Повторне відправлення потребуватиме додаткового підтвердження.": (
        "⚠ An application was already submitted for this job. Sending it again "
        "requires additional confirmation."
    ),
    "На цю вакансію вже подавали заявку. Відкрити форму для повторного відправлення все одно?": (
        "An application was already submitted for this job. Open the form again anyway?"
    ),
    "Для режиму з допомогою JobCompass оберіть оригінальний PDF або DOCX.": (
        "Select the original PDF or DOCX for assisted mode."
    ),
    "Для цього джерела ще немає перевіреного конектора.": (
        "There is no verified connector for this source yet."
    ),
    "Вакансія не містить адреси сторінки для подачі заявки.": (
        "The job does not contain an application page URL."
    ),
    "Супровідний лист порожній.": "The cover letter is empty.",
    "Супровідний лист скопійовано в буфер обміну.": (
        "The cover letter was copied to the clipboard."
    ),
    "Підтверджуйте лише якщо сайт роботодавця показав, що заявку успішно прийнято. Записати її в історію?": (
        "Confirm only if the employer's site showed that the application was "
        "accepted successfully. Save it to history?"
    ),
    "Створити профіль, щоб зберегти заявку та її матеріали?": (
        "Create a profile to save the application and its materials?"
    ),
    "Сторінку вакансії відкрито. Заповніть і перевірте форму, прикріпіть оригінальне резюме та натисніть Submit на сайті. Після успіху поверніться сюди й підтвердьте відправлення.": (
        "The job page is open. Complete and review the form, attach the original "
        "resume, and click Submit on the site. After success, return here and "
        "confirm the submission."
    ),
    "Заявку підтверджено й записано: ": "Application confirmed and recorded: ",
    "Відправлені матеріали:": "Submitted materials:",
    "ручний режим": "manual mode",
    "з допомогою JobCompass": "assisted by JobCompass",
    "автоматичний режим": "automatic mode",
    "використано": "used",
    "не використано": "not used",

    # Settings, profiles, and updates.
    "Налаштування JobCompass": "JobCompass settings",
    "Мова інтерфейсу": "Interface language",
    "Застосовується одразу та зберігається для всіх профілів.": (
        "Applied immediately and saved for all profiles."
    ),
    "Мову інтерфейсу змінено": "Interface language changed",
    "Тут зберігатимуться загальні параметри програми, які не залежать від профілю кандидата.": (
        "Global application settings that do not depend on the candidate profile."
    ),
    "Гостьовий режим: резюме, обране, перегляди та заявки зберігаються лише до закриття програми.": (
        "Guest mode: the resume, favorites, views, and applications are kept only "
        "until the application is closed."
    ),
    "Профіль, вакансії та історія зберігаються тільки локально. JobCompass не надсилає резюме або дані до AI-сервісів.": (
        "Profiles, jobs, and history are stored locally only. JobCompass does not "
        "send resumes or data to AI services."
    ),
    "Вакансії: Bundesagentur, Arbeitnow і Remotive підключені; доступність залежить від зовнішніх сервісів.\nПідказки міст: Open-Meteo Geocoding / GeoNames, без ключа для некомерційного використання; вводиться лише текст міста.\nJSON-імпорт залишається допоміжним режимом для тестів і власних даних.\nРезюме: JSON, TXT, DOCX і текстовий PDF — доступно локально.\nСЛ, безкоштовний режим: локальна чернетка та покращений промпт — доступно.\nСЛ, AI/API режим: заплановано; токени ще не приймаються і зовнішні виклики відсутні.": (
        "Jobs: Bundesagentur, Arbeitnow, and Remotive are connected; availability "
        "depends on external services.\n"
        "City suggestions: Open-Meteo Geocoding / GeoNames, keyless for "
        "non-commercial use; only city text is submitted.\n"
        "JSON import remains an auxiliary mode for tests and custom data.\n"
        "Resumes: JSON, TXT, DOCX, and text-based PDF are processed locally.\n"
        "Cover letters, free mode: local draft and enhanced prompt are available.\n"
        "Cover letters, AI/API mode: planned; tokens are not accepted and no "
        "external AI calls are made."
    ),
    "Оновлення": "Updates",
    "Перевірити оновлення": "Check for updates",
    "Перевірити ще раз": "Check again",
    "Спробувати ще раз": "Try again",
    "Поточна версія: ": "Current version: ",
    "Перевірте, чи доступна нова версія JobCompass.": (
        "Check whether a new JobCompass version is available."
    ),
    "Перевіряємо наявність оновлень…": "Checking for updates…",
    "Завантажити й установити": "Download and install",
    "Завантажити portable-версію": "Download portable version",
    "Відкрити сторінку оновлення": "Open update page",
    "Установити оновлення": "Install update",
    "Оновлення завантажено": "Update downloaded",
    "Триває пошук": "Search in progress",
    "Локальні дані": "Local data",
    "Файл сховища": "Storage file",
    "Керування профілями": "Profile management",
    "Конектори та формати": "Connectors and formats",
    "Імпортувати вакансії з JSON": "Import jobs from JSON",
    "Імпортувати профіль": "Import profile",
    "Експортувати профіль": "Export profile",
    "Дублювати профіль": "Duplicate profile",
    "Перейменувати профіль": "Rename profile",
    "Видалити профіль": "Delete profile",
    "Незбережені зміни": "Unsaved changes",
    "Збережено": "Saved",
    "Оновлено": "Updated",
    "Не вдалося зберегти": "Could not save",
    "Не вдалося оновити статус": "Could not update status",
    "Не вдалося прочитати резюме": "Could not read resume",
    "Не вдалося створити профіль": "Could not create profile",
    "Не вдалося зберегти профіль": "Could not save profile",
    "Не вдалося зберегти розклад": "Could not save schedule",
    "Не вдалося відкрити папку": "Could not open folder",
    "Не вдалося запустити інсталятор": "Could not start installer",
    "Деякі джерела недоступні": "Some sources are unavailable",
    "Імпорт вакансій": "Job import",
    "Імпорт завершено": "Import complete",
    "Нову portable-версію збережено: ": "New portable version saved to: ",
    "Доступна нова версія ": "A new version is available: ",
    "Доступне оновлення JobCompass ": "JobCompass update available: ",
    "У вас актуальна версія JobCompass ": "You have the latest JobCompass version ",
    "Що змінило:\n": "What changed:\n",
}

# Only these application-owned fragments may be translated inside a longer
# string. Keeping this list explicit prevents names such as "JobCompass",
# vacancy titles, company names, profile names, paths, and resume text from
# being modified by a short dictionary entry such as "Job" or "Profile".
_INLINE_UK_TO_EN = {
    "За розкладом (": "Scheduled (",
    "Супровідний лист — ": "Cover letter — ",
    "Релевантність: ": "Match: ",
    "Оберіть, як підготувати заявку для цієї конкретної вакансії.": (
        "Choose how to prepare an application for this specific job."
    ),
    "Визначено: ": "Detected: ",
    "Вакансій у списку: ": "Jobs in list: ",
    "Формат роботи: ": "Work mode: ",
    "Опубліковано: ": "Published: ",
    "Посилання: ": "Link: ",
    "Збігаються: ": "Matched: ",
    "Бракує обов’язкових: ": "Missing required: ",
    "Повнота доказів для оцінювання: ": "Evidence coverage: ",
    "Останній запуск: ": "Last run: ",
    "Поточний статус: ": "Current status: ",
    "Поточна версія: ": "Current version: ",
    "Заявку підтверджено й записано: ": "Application confirmed and recorded: ",
    "Нову portable-версію збережено: ": "New portable version saved to: ",
    "Доступна нова версія ": "A new version is available: ",
    "Доступне оновлення JobCompass ": "JobCompass update available: ",
    "У вас актуальна версія JobCompass ": "You have the latest JobCompass version ",
    "Що змінило:\n": "What changed:\n",
    "Знайдено варіантів: ": "Suggestions found: ",
    "Місто вже вибрано: ": "City already selected: ",
    "Активний профіль: ": "Active profile: ",
}


def normalize_language(value: str | None) -> str:
    return value if value in LANGUAGE_LABELS else DEFAULT_LANGUAGE


def set_language(value: str) -> str:
    global _language
    _language = normalize_language(value)
    return _language


def get_language() -> str:
    return _language


def translate(value: Any) -> Any:
    """Translate UI text while leaving unknown user content untouched."""

    if not isinstance(value, str) or not value:
        return value
    if _language == "en":
        exact = _UK_TO_EN.get(value)
        if exact is not None:
            return exact
        result = value
        for source, target in sorted(
            _INLINE_UK_TO_EN.items(), key=lambda item: len(item[0]), reverse=True
        ):
            if source in result:
                result = result.replace(source, target)
        return result

    reverse = {english: ukrainian for ukrainian, english in _UK_TO_EN.items()}
    exact = reverse.get(value)
    if exact is not None:
        return exact
    inline_reverse = {
        english: ukrainian for ukrainian, english in _INLINE_UK_TO_EN.items()
    }
    result = value
    for source, target in sorted(
        inline_reverse.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if source in result:
            result = result.replace(source, target)
    return result


class LocalizedStringVar(StringVar):
    """StringVar for application-owned labels and statuses, never form input."""

    def __init__(self, *args: Any, value: str = "", **kwargs: Any) -> None:
        super().__init__(*args, value=translate(value), **kwargs)
        _localized_variables.add(str(self))

    def set(self, value: str) -> None:
        super().set(translate(value))


def is_localized_variable(name: str) -> bool:
    return name in _localized_variables


class LocalizedDialogProxy:
    """Translate titles/messages while preserving arbitrary dialog values and paths."""

    def __init__(self, module: Any) -> None:
        self._module = module

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._module, name)
        if not callable(target):
            return target

        def localized(*args: Any, **kwargs: Any) -> Any:
            translated_args = list(args)
            for index in range(min(2, len(translated_args))):
                translated_args[index] = translate(translated_args[index])
            for key in ("title", "message", "prompt"):
                if key in kwargs:
                    kwargs[key] = translate(kwargs[key])
            if "filetypes" in kwargs:
                kwargs["filetypes"] = tuple(
                    (translate(label), pattern)
                    for label, pattern in kwargs["filetypes"]
                )
            return target(*translated_args, **kwargs)

        return localized
