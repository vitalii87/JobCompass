# JobCompass

[Українська](README.md) · **English**

JobCompass is a local Windows desktop application for finding, explainably
matching, and tracking job vacancies. The packaged Windows application does not
require Python to be installed. The source version supports Python 3.11+ and
uses the standard library plus the local PDF parser `pypdf`.

## Current features

- Windows desktop interface built with `Tkinter/ttk`;
- Ukrainian, English, and German interface selectable in Settings;
- local resume loading from JSON, TXT, DOCX, and text-based PDF files;
- explainable 0–100% matching with evidence-coverage information;
- online search through Bundesagentur für Arbeit, Arbeitnow, and Remotive;
- exact duplicate detection and optional normalized JSON import;
- isolated candidate profiles with individual resumes, filters, results,
  favorites, application history, and cover-letter materials;
- temporary guest mode;
- daily scheduled searches and new-job tracking;
- scheduled jobs remain in the list after opening and show a profile-specific
  `New` or dated `Viewed` status;
- statuses `Found`, `Interesting`, `Draft`, `Applied`, `Rejected`, `Interview`,
  `Offer`, and `Archived`;
- vacancy-specific local cover-letter drafts and grounded prompts for external AI;
- manual and assisted application workflows with a pre-submission review;
- duplicate-application warnings and an audit trail of submitted materials;
- automatic update checks through GitHub Releases;
- a supplementary command-line interface.

## Windows installation

Release packages are available on the
[GitHub Releases page](https://github.com/vitalii87/JobCompass/releases):

- `JobCompass-0.10.3-Setup.exe` — per-user installer for Windows 10/11 x64;
- `JobCompass-0.10.3-Portable.zip` — portable package;
- `SHA256SUMS.txt` — integrity checksums.

The installer does not require administrator rights. It creates Start Menu and
desktop shortcuts and installs a per-user uninstaller. Python and project
dependencies are bundled.

For portable use:

1. Extract the complete portable ZIP to a folder.
2. Run `JobCompass.exe` from that folder.
3. Keep `_internal` and `portable.flag`; copying only the EXE will not work.

Installed data is stored in:

```text
%LOCALAPPDATA%\JobCompass\data\jobcompass.json
```

Portable data is stored in a `data` directory beside `JobCompass.exe`. Back up
`jobcompass.json` periodically.

## Running from source

Requirements:

- Windows or another system with Tkinter;
- Python 3.11 or newer;
- `pypdf` for local PDF extraction.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app
```

Alternatively, on Windows run `run_jobcompass.bat`.

## Interface language

Open the gear button `⚙`, select **Ukrainian**, **English**, or **German**, and the interface
updates immediately. The choice is global, is shared by all candidate profiles,
and is restored the next time JobCompass starts. Resume text, candidate-entered
content, city names, and cover letters are never translated automatically.

## Candidate profiles and guest mode

JobCompass starts in guest mode when no persistent profile is active. Guest mode
supports resume loading, filter configuration, and searches, but personal state
is discarded when the application closes.

The selector at the top changes candidates without reloading their data. Saving
a profile stores the candidate data, resume reference and extracted text, source
selection, target roles, cities, radius, exclusions, match threshold, sorting,
and schedule. Each profile has isolated favorites, views, application history,
and cover-letter materials.

Profiles can be renamed, duplicated without history, exported, imported, and
deleted. The last persistent profile opens automatically on the next launch.

## Resume processing

All profile fields are optional. A user can work from an uploaded resume without
manually entering a name, email address, target role, or other fields. JobCompass
extracts information conservatively and does not invent candidate facts.

Supported formats:

- JSON profile;
- UTF-8 TXT;
- DOCX;
- text-based PDF.

Scanned image-only PDFs require OCR, which is not currently bundled. Parsed text
is used locally for matching and cover-letter preparation. It is never submitted
to an employer as a replacement for the original resume file.

## Online vacancy search

Target roles are comma-separated alternatives using OR logic. Additional
requirements use AND logic. Locations must be selected through the city
suggestions, which include country and administrative-region information to
disambiguate identical city names.

One radius is applied independently to every selected city. Bundesagentur passes
the radius to its server. Sources without geographic search may only filter by
the returned location name. When **Remote only** is disabled, remote, hybrid,
office, and unknown work modes are included.

The current connectors are:

- Bundesagentur für Arbeit;
- Arbeitnow;
- Remotive.

Source availability depends on external services and their rate limits. A failed
source does not invalidate partial results returned by other sources.

## German-market matching

JobCompass recognizes common German requirement sections such as `Ihr Profil`,
`Anforderungen`, `Das bringen Sie mit`, and `Wünschenswert`. It distinguishes
required, preferred, and explicitly non-required statements and normalizes common
German and English roles, skills, languages, and work arrangements.

The match score is evidence-based. Missing structured evidence does not become a
positive match. The result explains matched skills, missing requirements, risks,
component scores, and evidence coverage. The threshold slider filters the current
result set locally without repeating the internet request.

## Cover letters and applications

For a selected vacancy, JobCompass can:

1. create an editable local draft;
2. create a grounded prompt for an external AI service;
3. continue without a cover letter;
4. reuse a previously saved letter.

The prompt combines confirmed candidate evidence with the vacancy description,
matched requirements, and gaps. It instructs the AI not to invent experience,
skills, education, achievements, or company facts. Contact information is not
included in the AI prompt.

Before an application, JobCompass opens a pre-submission review. The user can:

- choose manual mode, which opens the job page;
- choose assisted mode, which copies the cover letter and opens the job page;
- edit or paste a final cover letter;
- export the reviewed cover letter locally as an A4 PDF when the employer form
  requires a file upload;
- choose the exact original PDF or DOCX intended for submission.

The user still reviews the employer form and clicks its final Submit button.
JobCompass records `Applied` only after explicit confirmation that the external
site accepted the application. It then stores a local audit record containing
the mode, destination URL, resume filename and SHA-256, cover-letter snapshot,
and contact-data snapshot. A repeated submission requires another confirmation.

Automatic submission remains disabled for sources without a verified connector.
JobCompass does not claim success when it cannot verify an external submission.

## Scheduled searches

Each persistent profile can configure one daily search time. The schedule uses
that profile's saved roles, cities, sources, and filters. Installed and portable
Windows builds register a profile-specific Windows Task Scheduler task. If a due
search could not run while the application was closed, it runs after the next
launch.

Portable scheduled tasks require the drive to remain available under the same
drive letter.

## Updates

The `⚙` dialog displays the current version and checks the latest stable GitHub
Release. JobCompass also performs a non-blocking check shortly after startup.

- Installed mode downloads the installer, verifies SHA-256, closes JobCompass,
  and launches the installer after confirmation.
- Portable mode downloads the verified ZIP to `Downloads` for manual extraction.
- Source mode opens the corresponding GitHub Release page.

Profiles and history are stored separately from installed program files.

## CLI

```powershell
python -m app --help
python -m app init
python -m app import-jobs path\to\jobs.json
python -m app list-jobs
python -m app match path\to\profile.json
python -m app set-status source:id Interesting
python -m app list-applications
python -m app scheduled-search --profile-id PROFILE_ID --force
```

Use another storage file with:

```powershell
python -m app --data C:\path\jobcompass.json list-jobs
```

## Tests and Windows builds

```powershell
python -m unittest discover -v
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

The build script creates a clean build environment, runs all tests, builds the
one-folder executable, portable ZIP, NSIS installer, and SHA-256 manifest.

## Privacy and current boundaries

Candidate profiles, resumes, cover letters, and application history remain in
the local JSON storage. The current free mode does not call an AI API and does
not store AI tokens.

JobCompass does not currently implement OCR, a REST API, embeddings, Ollama,
LinkedIn/Indeed/StepStone scraping, or automatic mass application submission.
External job pages remain under the user's control, and successful submission is
confirmed by the user.
