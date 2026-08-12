"""Small standard-library runtime localization for the desktop interface."""

from __future__ import annotations

from tkinter import StringVar
from typing import Any

from app.i18n_de import EN_TO_DE, INLINE_EN_TO_DE


DEFAULT_LANGUAGE = "uk"
LANGUAGE_LABELS = {"uk": "Українська", "en": "English", "de": "Deutsch"}
_LANGUAGE_DISPLAY_NAMES = {
    "uk": {"uk": "Українська", "en": "Ukrainian", "de": "Ukrainisch"},
    "en": {"uk": "Англійська", "en": "English", "de": "Englisch"},
    "de": {"uk": "Німецька", "en": "German", "de": "Deutsch"},
}
_language = DEFAULT_LANGUAGE
_localized_variables: set[str] = set()
_UK_TO_DE_EXACT_OVERRIDES = {
    "Копіювати": "Kopieren",
    "Копія": "Kopie",
}


_UK_TO_EN = {
    # Main navigation and shared controls.
    "Українська": "Ukrainian",
    "Англійська": "English",
    "Німецька": "German",
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
    "Вкажіть професію, місто й формат роботи. JobCompass сам перевірить доступні джерела, знайде career-сайти, прибере дублікати та оцінить вакансії.": (
        "Enter a role, city, and work mode. JobCompass will check available sources, "
        "discover career sites, remove duplicates, and evaluate jobs automatically."
    ),
    "Пошук розпочато: JobCompass перевіряє доступні джерела…": (
        "Search started: JobCompass is checking available sources…"
    ),

    # Search and locations.
    "Пошук вакансій": "Job search",
    "Платформи / джерела": "Platforms / sources",
    "Фільтри": "Filters",
    "Формат роботи": "Work mode",
    "Усі формати": "All work modes",
    "Remote або hybrid": "Remote or hybrid",
    "Тільки remote": "Remote only",
    "Тільки hybrid": "Hybrid only",
    "Тільки office": "Office only",
    "Розширені фільтри": "Advanced filters",
    "Сховати розширені": "Hide advanced filters",
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
    "Знайти роботу": "Find jobs",
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
    "Перегляд": "View status",
    "Нова": "New",
    "Переглянуто": "Viewed",
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
    "Докази з тексту вакансії:": "Evidence from the job description:",
    "Опис:": "Description:",
    "Професія": "Role",
    "Досвід": "Experience",
    "не вказана": "not specified",
    "повна": "full",
    "часткова": "partial",
    "слабка": "weak",
    "обов’язкова": "required",
    "бажана": "preferred",
    "невідома": "unknown",
    "Повнота доказів для оцінювання: ": "Evidence coverage: ",

    # Scheduling.
    "Пошук за розкладом": "Scheduled search",
    "Щоденний автоматичний пошук": "Daily automatic search",
    "Увімкнути для активного профілю": "Enable for active profile",
    "Час:": "Time:",
    "Зберегти розклад": "Save schedule",
    "Розклад не налаштовано": "Schedule is not configured",
    "Нові та ще не переглянуті вакансії": "New and unseen jobs",
    "Вакансії за розкладом": "Scheduled jobs",
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
    "Зберегти лист як PDF…": "Save letter as PDF…",
    "Зберегти супровідний лист як PDF": "Save cover letter as PDF",
    "Не вдалося створити PDF": "Could not create PDF",
    "PDF супровідного листа збережено: ": "Cover letter PDF saved: ",
    "Почати відправлення": "Start submission",
    "Скопіювати лист і відкрити вакансію": "Copy letter and open job",
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
    "Супровідний лист копіюється в буфер, після чого відкривається сторінка вакансії.": (
        "The cover letter is copied to the clipboard, then the job page is opened."
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
    "Супровідний лист скопійовано, сторінку вакансії відкрито. Заповніть і перевірте форму, прикріпіть оригінальне резюме та натисніть Submit на сайті. Після успіху поверніться сюди й підтвердьте відправлення.": (
        "The cover letter was copied and the job page is open. Complete and review "
        "the form, attach the original resume, and click Submit on the site. After "
        "success, return here and confirm the submission."
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
    "Career-сайти компаній": "Company career sites",
    "Greenhouse career-сайти": "Greenhouse career sites",
    "Lever career-сайти": "Lever career sites",
    "Ashby career-сайти": "Ashby career sites",
    "Personio career-сайти": "Personio career sites",
    "Workday career-сайти": "Workday career sites",
    "Розширені → Джерела": "Advanced → Sources",
    "Канали пошуку": "Search channels",
    "Career URL — advanced/debug": "Career URL — advanced/debug",
    "Зберегти ручні джерела": "Save manual sources",
    "Автоматично знайдені джерела": "Automatically discovered sources",
    "Компанія": "Company",
    "Тип": "Type",
    "Статус": "Status",
    "Перевірено": "Checked",
    "Країна / регіон": "Country / region",
    "Останній успіх": "Last success",
    "Знайдено": "Discovered",
    "Активне": "Active",
    "Помилка": "Error",
    "Заблоковано": "Blocked",
    "Вимкнено": "Disabled",
    "JobCompass автоматично знаходить і запам’ятовує career-сайти. Поля нижче потрібні лише для діагностики або ручного додавання джерела.": (
        "JobCompass automatically discovers and remembers career sites. The fields "
        "below are only for diagnostics or manually adding a source."
    ),
    "Необов’язково. По одному URL у рядку; підтримуються Greenhouse, Lever, Ashby, Personio, Workday, JSON-LD і дозволені HTML/sitemap.": (
        "Optional. One URL per line; Greenhouse, Lever, Ashby, Personio, Workday, "
        "JSON-LD, and permitted HTML/sitemaps are supported."
    ),
    "По одному URL у рядку. JobCompass автоматично розпізнає Greenhouse, Lever, Ashby, Personio або прочитає дозволений schema.org/JobPosting.": (
        "One URL per line. JobCompass automatically recognizes Greenhouse, Lever, "
        "Ashby, and Personio, or reads permitted schema.org/JobPosting data."
    ),
    "Зберегти career-сайти": "Save career sites",
    "Не вдалося зберегти career-сайти": "Could not save career sites",
    "Оновлення": "Updates",
    "Перевірити оновлення": "Check for updates",
    "Перевірити ще раз": "Check again",
    "Спробувати ще раз": "Try again",
    "Поточна версія: ": "Current version: ",
    "Career-сайти збережено: ": "Career sites saved: ",
    "Ручні career-сайти збережено: ": "Manual career sites saved: ",
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
    "Career-сайти збережено: ": "Career sites saved: ",
    "Заявку підтверджено й записано: ": "Application confirmed and recorded: ",
    "Нову portable-версію збережено: ": "New portable version saved to: ",
    "Доступна нова версія ": "A new version is available: ",
    "Доступне оновлення JobCompass ": "JobCompass update available: ",
    "У вас актуальна версія JobCompass ": "You have the latest JobCompass version ",
    "Що змінило:\n": "What changed:\n",
    "Знайдено варіантів: ": "Suggestions found: ",
    "Місто вже вибрано: ": "City already selected: ",
    "Активний профіль: ": "Active profile: ",
    "Відомих career-сайтів: ": "Known career sites: ",
    "Перевірено джерел: ": "Sources checked: ",
    "нових career-сайтів: ": "new career sites: ",
    "вакансій зібрано: ": "jobs collected: ",
    "відповідають профілю: ": "matching the profile: ",
    "Ручні career-сайти збережено: ": "Manual career sites saved: ",
}

# Messages assembled at runtime are kept explicit so localization never performs
# broad word replacement inside resume or job-description content.
_UK_TO_EN.update(
    {
        "\nВідправлені матеріали:": "\nSubmitted materials:",
        "\nПодії:": "\nEvents:",
        "  Супровідний лист: ": "  Cover letter: ",
        " — зачекайте": " — please wait",
        "Інтернет-джерела не повернули вакансій для вибраних посад, локацій і радіуса.": "Online sources returned no jobs for the selected roles, locations, and radius.",
        "Інші джерела оброблено.\n\n": "Other sources were processed.\n\n",
        "Автоматичний пошук потребує профілю. Створити його зараз?": "Automatic search requires a profile. Create one now?",
        "Вакансію для заявки не знайдено.": "The job for this application was not found.",
        "Вакансії знайдено, але їх приховали фільтри": "Jobs were found but hidden by filters",
        "Введіть щонайменше 2–3 літери назви міста.": "Enter at least 2–3 letters of the city name.",
        "Введіть ім’я або назву профілю:": "Enter a name or profile title:",
        "Виберіть місто у списку, яке потрібно видалити.": "Select the city to remove from the list.",
        "Виберіть резюме": "Select a resume",
        "Дочекайтеся завершення пошуку перед оновленням.": "Wait for the search to finish before updating.",
        "Дочекайтеся завершення пошуку перед перемиканням профілю.": "Wait for the search to finish before switching profiles.",
        "Закрийте JobCompass і розпакуйте нову portable-версію. Папку data та файл portable.flag потрібно зберегти.": "Close JobCompass and extract the new portable version. Keep the data folder and portable.flag file.",
        "Закрити програму й перервати поточний пошук?": "Close the application and interrupt the current search?",
        "Запускаю прострочений щоденний пошук…": "Starting the overdue daily search…",
        "Запланований пошук ще не настав.": "The scheduled search is not due yet.",
        "Зберегти поточний профіль перед створенням нового?": "Save the current profile before creating a new one?",
        "Зберегти поточний профіль і налаштування перед перемиканням?": "Save the current profile and settings before switching?",
        "Зберегти поточний профіль і параметри перед виходом?": "Save the current profile and settings before exiting?",
        "Зберегти поточний профіль і параметри перед оновленням?": "Save the current profile and settings before updating?",
        "Зберегти поточні посади, міста та фільтри перед запуском?": "Save the current roles, cities, and filters before running?",
        "Копія": "Copy",
        "Місто додано без географічної перевірки; за можливості оберіть підказку.": "The city was added without geographic verification; select a suggestion when possible.",
        "Місто не знайдено. Перевірте написання або додайте введене вручну.": "City not found. Check the spelling or add the entered value manually.",
        "Назва копії (історія та заявки не копіюються):": "Copy name (history and applications are not copied):",
        "Не вдалося видалити профіль": "Could not delete profile",
        "Не вдалося дублювати профіль": "Could not duplicate profile",
        "Не вдалося експортувати профіль": "Could not export profile",
        "Не вдалося зберегти результати": "Could not save results",
        "Не вдалося перейменувати профіль": "Could not rename profile",
        "Не вдалося імпортувати вакансії": "Could not import jobs",
        "Не вдалося імпортувати профіль": "Could not import profile",
        "Немає активного профілю.": "There is no active profile.",
        "Нова назва профілю:": "New profile name:",
        "Оберіть хоча б одне місто з підказки або натисніть «Додати введене без перевірки».": "Select at least one suggested city or click ‘Add entered city without verification’.",
        "Обране та історія заявок у гостьовому режимі не зберігаються. Створити профіль зараз?": "Favorites and application history are not saved in guest mode. Create a profile now?",
        "Оновлення перевірено й готове до встановлення. JobCompass буде закрито. Запустити інсталятор зараз?": "The update has been verified and is ready to install. JobCompass will close. Start the installer now?",
        "Останній інтернет-пошук не повернув вакансій, тому зміна порога не може змінити список. Перевірте стан джерел над таблицею.": "The latest online search returned no jobs, so changing the threshold cannot change the list. Check the source status above the table.",
        "Перевірте: ": "Check: ",
        "Перенести гостьові дані?": "Transfer guest data?",
        "Перенести поточне резюме, фільтри, результати та обране до нового профілю?": "Transfer the current resume, filters, results, and favorites to the new profile?",
        "Посилання": "Link",
        "Пошук за розкладом зберігає нові вакансії окремо для кандидата. Створити профіль?": "Scheduled search stores new jobs separately for each candidate. Create a profile?",
        "Пошук…": "Searching…",
        "Профіль успішно експортовано.": "Profile exported successfully.",
        "Профіль і всі параметри пошуку збережено локально": "The profile and all search settings were saved locally",
        "Профіль, резюме, міста, посади, фільтри та розклад збережено.": "Profile, resume, cities, roles, filters, and schedule were saved.",
        "Резюме активне в поточному сеансі. Поля можна виправити перед збереженням.\n\n": "The resume is active in the current session. You can correct the fields before saving.\n\n",
        "Резюме завантажено — натисніть «Зберегти профіль», щоб залишити його після закриття": "Resume loaded — click ‘Save profile’ to keep it after closing",
        "Розклад і поточні параметри пошуку збережено.\n\n": "The schedule and current search settings were saved.\n\n",
        "Спочатку виберіть вакансію.": "Select a job first.",
        "Спочатку виберіть заявку.": "Select an application first.",
        "Спочатку створіть профіль.": "Create a profile first.",
        "Текст скопійовано в буфер обміну": "Text copied to the clipboard",
        "У GitHub Release немає потрібного інсталяційного файла.": "The required installer file is missing from the GitHub Release.",
        "Увімкнено гостьовий режим": "Guest mode enabled",
        "Усі файли": "All files",
        "Чернетку, промпт і вибрані параметри збережено локально.": "The draft, prompt, and selected settings were saved locally.",
        "Щоб зберігати заявки й супровідні листи, створіть профіль. Створити зараз?": "Create a profile to save applications and cover letters. Create one now?",
        "виключені компанії: ": "excluded companies: ",
        "виключені слова: ": "excluded words: ",
        "додаткові вимоги: ": "additional requirements: ",
        "онлайн-джерела не вибрано": "no online sources selected",
        "ще не запускався": "has not run yet",
        "Отримано після фільтрів джерел: ": "Received after source filters: ",
        "Пошук у мережі: ": "Online search: ",
        "Remote": "Remote",
        "Hybrid": "Hybrid",
        "Office": "Office",
        "Email": "Email",
        "JobCompass profile": "JobCompass profile",
        "Vacancy-specific cover letter draft created": "Vacancy-specific cover letter draft created",
    }
)

_INLINE_UK_TO_EN.update(
    {
        "\n\nПродовжити все одно?": "\n\nContinue anyway?",
        "\n\nФонове завдання Windows: ": "\n\nWindows background task: ",
        "\nДодано нових: ": "\nNewly added: ",
        "\nОстаннє оновлення: ": "\nLast updated: ",
        "  Адреса: ": "  Address: ",
        "  Резюме: ": "  Resume: ",
        " (встановлено ": " (installed ",
        " (часткові результати)": " (partial results)",
        " | отримано: ": " | received: ",
        " | при порозі ": " | at threshold ",
        " | після об’єднання та фільтрів JobCompass: ": " | after merging and JobCompass filters: ",
        " вакансій за посадами й локаціями, але їх прибрали додаткові фільтри.\n\n": " jobs for the roles and locations, but additional filters removed them.\n\n",
        " вакансій. Найвища доступна оцінка: ": " jobs. Highest available score: ",
        " вакансій. Найвищий score: ": " jobs. Highest score: ",
        " і перевіряємо SHA-256…": " and verifying SHA-256…",
        " — копія": " — copy",
        "% показано: ": "% displayed: ",
        "% приховано ": "% hidden ",
        "% — без повторного запиту до сайтів": "% — without querying the sites again",
        "%, встановлений поріг: ": "%, configured threshold: ",
        "%. Зменште мінімальну релевантність.": "%. Lower the minimum match.",
        ", додано нових вакансій: ": ", new jobs added: ",
        ". Відкрийте ⚙.": ". Open ⚙.",
        ". Оберіть точне місто зі списку.": ". Select the exact city from the list.",
        ". Усі персональні дані ізольовані від інших профілів.": ". All personal data is isolated from other profiles.",
        ": помилка": ": error",
        "» разом із його заявками, обраним і розкладом?": "’ together with its applications, favorites, and schedule?",
        "Автопошук завершено: нових вакансій — ": "Automatic search complete: new jobs — ",
        "Автопошук не оновив результати; повтор через 30 хвилин.": "Automatic search did not update results; retrying in 30 minutes.",
        "Автопошук не запущено: ": "Automatic search not started: ",
        "Активовано профіль: ": "Profile activated: ",
        "До порога релевантності дійшло ": "Jobs reaching the match threshold: ",
        "Додано: ": "Added: ",
        "Завантажуємо ": "Downloading ",
        "Знайдено ": "Found ",
        "Локальний поріг змінено на ": "Local threshold changed to ",
        "На цю вакансію вже подавали заявку або вона має післяподачний статус.\n\nСтатус: ": "An application was already submitted for this job or it has a post-submission status.\n\nStatus: ",
        "Назавжди видалити профіль «": "Permanently delete profile ‘",
        "Не вдалося завантажити оновлення: ": "Could not download update: ",
        "Не вдалося перевірити оновлення: ": "Could not check for updates: ",
        "Нотатка: ": "Note: ",
        "Отримано часткові результати; наступні сторінки недоступні: ": "Partial results received; subsequent pages are unavailable: ",
        "Показано релевантних вакансій: ": "Matching jobs displayed: ",
        "Помилка розкладу: ": "Schedule error: ",
        "Порогом ": "Threshold ",
        "Прочитано ": "Read ",
        "Прочитано: ": "Read: ",
        "Створено профіль: ": "Profile created: ",
        "Супровідні матеріали збережено: ": "Application materials saved: ",
    }
)


def normalize_language(value: str | None) -> str:
    return value if value in LANGUAGE_LABELS else DEFAULT_LANGUAGE


def set_language(value: str) -> str:
    global _language
    _language = normalize_language(value)
    return _language


def get_language() -> str:
    return _language


def language_label(code: str, interface_language: str | None = None) -> str:
    """Return a localized language name for a stable language code."""

    normalized_code = normalize_language(code)
    display_language = normalize_language(interface_language or _language)
    return _LANGUAGE_DISPLAY_NAMES[normalized_code][display_language]


def language_from_label(label: str) -> str:
    """Resolve a language selected in any supported interface language."""

    for code, names in _LANGUAGE_DISPLAY_NAMES.items():
        if label in names.values() or label == LANGUAGE_LABELS[code]:
            return code
    return DEFAULT_LANGUAGE


def _canonical_exact(value: str) -> str | None:
    if value in _UK_TO_EN:
        return value
    english_reverse = {translated: source for source, translated in _UK_TO_EN.items()}
    canonical = english_reverse.get(value)
    if canonical is not None:
        return canonical
    german_reverse = {
        EN_TO_DE.get(english, english): source
        for source, english in _UK_TO_EN.items()
    }
    german_reverse.update(
        {translated: source for source, translated in _UK_TO_DE_EXACT_OVERRIDES.items()}
    )
    return german_reverse.get(value)


def _target_exact(canonical: str) -> str:
    if _language == "uk":
        return canonical
    english = _UK_TO_EN.get(canonical, canonical)
    if _language == "de":
        return _UK_TO_DE_EXACT_OVERRIDES.get(
            canonical, EN_TO_DE.get(english, english)
        )
    return english


def _inline_catalog(language: str) -> dict[str, str]:
    if language == "uk":
        return {source: source for source in _INLINE_UK_TO_EN}
    if language == "de":
        return {
            source: INLINE_EN_TO_DE.get(english, EN_TO_DE.get(english, english))
            for source, english in _INLINE_UK_TO_EN.items()
        }
    return dict(_INLINE_UK_TO_EN)


def translate(value: Any) -> Any:
    """Translate UI text while leaving unknown user content untouched."""

    if not isinstance(value, str) or not value:
        return value
    canonical = _canonical_exact(value)
    if canonical is not None:
        return _target_exact(canonical)

    source_catalogs = (
        _inline_catalog("uk"),
        _inline_catalog("en"),
        _inline_catalog("de"),
    )
    target_catalog = _inline_catalog(_language)
    result = value
    replacements: list[tuple[str, str]] = []
    for canonical_fragment in _INLINE_UK_TO_EN:
        target = target_catalog[canonical_fragment]
        for catalog in source_catalogs:
            source = catalog[canonical_fragment]
            if source != target:
                replacements.append((source, target))
    for source, target in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
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
