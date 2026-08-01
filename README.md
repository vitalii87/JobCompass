# JobCompass

JobCompass — локальна GUI-програма для пошуку, пояснюваного оцінювання та
відстеження вакансій. Поточна версія є прототипом на Python 3.11+ і
використовує лише стандартну бібліотеку.

## Що вже працює

- єдині моделі профілю кандидата, вакансії та заявки;
- графічний інтерфейс на `Tkinter/ttk` для Windows;
- локальне завантаження профілю або резюме у форматі JSON, TXT чи DOCX;
- пояснюваний match score від 0 до 100%;
- консервативне визначення точних дублікатів;
- імпорт нормалізованих вакансій із локального JSON;
- атомарне локальне JSON-сховище;
- статуси `Found`, `Interesting`, `Draft`, `Applied`, `Rejected`, `Interview`,
  `Offer` та `Archived`;
- фільтри за джерелом, ключовими словами, локацією, remote та score;
- локальна чернетка супровідного листа й безпечний промпт для зовнішнього AI;
- повна історія статусів і попередження про можливу повторну подачу;
- додатковий CLI для імпорту, перегляду, оцінювання та зміни статусів.

## Запуск

З кореня репозиторію запустіть GUI:

```powershell
python -m app
```

Або явно:

```powershell
python -m app gui
python -m app gui --data C:\path\jobcompass.json
```

Якщо у Windows доступний лише Python Launcher:

```powershell
py -3.11 -m app
```

Також можна двічі натиснути `run_jobcompass.bat`. Для швидкої перевірки GUI:

1. На вкладці `Профіль` завантажте `examples/profile.example.json` і збережіть.
2. На вкладці `Пошук` імпортуйте `examples/jobs.example.json`.
3. Виберіть джерела, встановіть фільтри та запустіть пошук.

GUI має п'ять вкладок:

1. `Профіль` — завантаження резюме, перевірка й збереження даних.
2. `Пошук` — імпорт вакансій, вибір джерел і фільтрів.
3. `Результати` — match score, ключові збіги, ризики й дії.
4. `Мої заявки` — поточні статуси та повна історія змін.
5. `Налаштування` — шлях до локального сховища й стан інтеграцій.

Командний інтерфейс залишається доступним:

```powershell
python -m app --help
python -m app init
python -m app import-jobs path\to\jobs.json
python -m app list-jobs
python -m app match path\to\profile.json
python -m app set-status source:id Interesting
python -m app list-applications
```

За замовчуванням локальні дані зберігаються в `data/jobcompass.json` і не
потрапляють до Git. Інший шлях можна передати перед командою:

```powershell
python -m app --data C:\path\jobcompass.json list-jobs
```

## Завантаження резюме

- `JSON` завантажується як готовий структурований профіль.
- `TXT` обробляється локально за підписаними секціями на кшталт `Skills:` або
  `Навички:`.
- `DOCX` читається локально стандартними засобами Python.
- `PDF` поки не підтримується: для надійного читання потрібен окремий парсер.

Автоматично витягнуті поля завжди потрібно перевірити в GUI. Програма не
вигадує відсутні дані.

## Формат профілю JSON

```json
{
  "full_name": "Candidate Name",
  "email": "candidate@example.test",
  "phone": "+49 000 000000",
  "summary": "Backend developer focused on reliable local software.",
  "desired_roles": ["Python Developer"],
  "skills": ["Python", "SQL", "Git"],
  "languages": ["English", "Ukrainian"],
  "years_experience": 3,
  "preferred_locations": ["Berlin"],
  "remote_only": false
}
```

## Мінімальний формат вакансій

Файл може містити список вакансій або об'єкт із полем `jobs`. Поля `source`,
`external_id`, `title` і `company` є обов'язковими.

```json
{
  "jobs": [
    {
      "source": "example",
      "external_id": "123",
      "title": "Python Developer",
      "company": "Example GmbH",
      "location": "Berlin",
      "url": "https://example.test/jobs/123",
      "required_skills": ["Python", "SQL"],
      "preferred_skills": ["Docker"],
      "required_languages": ["English"],
      "minimum_years_experience": 2,
      "remote": true,
      "employment_type": "full-time",
      "published_at": "2026-08-01T09:00:00+00:00"
    }
  ]
}
```

## Перевірка

```powershell
python -m unittest discover -v
```

## Конфіденційність і межі прототипу

Профіль, вакансії та історія заявок залишаються у локальному файлі
`data/jobcompass.json`. JobCompass не викликає AI API: кнопка AI-промпту лише
готує текст, який користувач може перевірити та скопіювати.

У поточній версії немає онлайн-конекторів, PDF-парсера, REST API, embeddings,
Ollama, scraping job-платформ або автоматичної подачі заявок. Кнопка відкриття
вакансії передає керування браузеру, а успішну подачу підтверджує користувач.
Нові конектори можна додавати без зміни моделей, matcher і сховища.
