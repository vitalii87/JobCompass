"""German translations for the JobCompass desktop interface."""

from __future__ import annotations


# Keys are the English values of the canonical Ukrainian catalogue. Keeping this
# table separate makes the runtime localization code small and easy to audit.
EN_TO_DE = {
    "Ukrainian": "Ukrainisch",
    "English": "Englisch",
    "German": "Deutsch",
    "Profile": "Profil",
    "Search": "Suche",
    "Scheduled (0)": "Zeitplan (0)",
    "Results": "Ergebnisse",
    "My applications": "Meine Bewerbungen",
    "Settings": "Einstellungen",
    "Ready": "Bereit",
    "Active profile:": "Aktives Profil:",
    "New profile": "Neues Profil",
    "Edit": "Bearbeiten",
    "Guest mode": "Gastmodus",
    "Guest mode (not saved)": "Gastmodus (wird nicht gespeichert)",
    "Local job search, matching, and application tracking": (
        "Lokale Stellensuche, Matching und Bewerbungsverfolgung"
    ),
    "Cancel": "Abbrechen",
    "Continue": "Weiter",
    "Save": "Speichern",
    "Update": "Aktualisieren",
    "Delete": "Löschen",
    "Import": "Importieren",
    "Export": "Exportieren",
    "Duplicate": "Duplizieren",
    "Rename": "Umbenennen",
    "Copy": "Kopieren",
    "Paste": "Einfügen",
    "Cut": "Ausschneiden",
    "Select all": "Alles auswählen",
    "Yes": "Ja",
    "No": "Nein",
    "Not specified": "Nicht angegeben",
    "not specified": "nicht angegeben",
    "—": "—",
    "Candidate profile": "Kandidatenprofil",
    "Resume data — all fields are optional": "Lebenslaufdaten — alle Felder sind optional",
    "Name": "Name",
    "Phone": "Telefon",
    "Target roles": "Wunschpositionen",
    "Skills": "Kenntnisse",
    "Languages": "Sprachen",
    "Years of experience": "Berufserfahrung in Jahren",
    "Preferred locations": "Bevorzugte Orte",
    "Short profile": "Kurzprofil",
    "I am looking for remote work only": "Ich suche ausschließlich Remote-Arbeit",
    "Save profile": "Profil speichern",
    "Save as profile": "Als Profil speichern",
    "Load resume": "Lebenslauf laden",
    "Resume": "Lebenslauf",
    "No resume loaded yet": "Noch kein Lebenslauf geladen",
    "Resume text — preview only": "Lebenslauftext — nur Vorschau",
    "Supported resumes": "Unterstützte Lebensläufe",
    "Resume is ready to use": "Der Lebenslauf kann verwendet werden",
    "Resume not found": "Lebenslauf nicht gefunden",
    "Select a resume": "Lebenslauf auswählen",
    "Select the original resume file": "Originaldatei des Lebenslaufs auswählen",
    "Select the current original resume file.": "Wählen Sie die aktuelle Originaldatei des Lebenslaufs aus.",
    "Years of experience must be a number": "Die Berufserfahrung muss als Zahl angegeben werden",
    "JobCompass searches selected online sources for current jobs, merges duplicates, and evaluates resume fit.": (
        "JobCompass durchsucht ausgewählte Online-Quellen nach aktuellen Stellen, "
        "führt Duplikate zusammen und bewertet die Übereinstimmung mit dem Lebenslauf."
    ),
    "Job search": "Stellensuche",
    "Platforms / sources": "Plattformen / Quellen",
    "Filters": "Filter",
    "Additional requirements (not cities)": "Zusätzliche Anforderungen (keine Orte)",
    "Locations (cities) *": "Orte (Städte) *",
    "Suggestion country": "Land für Ortsvorschläge",
    "Selected cities:": "Ausgewählte Städte:",
    "Add entered city without verification": "Eingegebenen Ort ungeprüft hinzufügen",
    "Remove selected": "Auswahl entfernen",
    "Radius": "Umkreis",
    "No radius": "Kein Umkreis",
    "no radius": "kein Umkreis",
    "Exclude words": "Wörter ausschließen",
    "Exclude companies": "Unternehmen ausschließen",
    "Remote only (when off: remote, hybrid, office, and unknown)": (
        "Nur Remote (wenn deaktiviert: Remote, Hybrid, vor Ort und unbekannt)"
    ),
    "Minimum match": "Mindestübereinstimmung",
    "Find jobs online": "Stellen online suchen",
    "Save settings": "Einstellungen speichern",
    "Comma-separated.": "Durch Kommas getrennt.",
    "All countries": "Alle Länder",
    "Searching for matching cities…": "Passende Städte werden gesucht…",
    "Suggestions found: ": "Gefundene Vorschläge: ",
    "Enter a city name first.": "Geben Sie zuerst einen Ortsnamen ein.",
    "City already selected: ": "Ort bereits ausgewählt: ",
    "City suggestions are temporarily unavailable. You can add the city manually.": (
        "Ortsvorschläge sind vorübergehend nicht verfügbar. Sie können den Ort manuell hinzufügen."
    ),
    "Enter at least one target role for online search": "Geben Sie mindestens eine Wunschposition für die Onlinesuche ein",
    "Select at least one job source": "Wählen Sie mindestens eine Stellenquelle aus",
    "Search in progress": "Suche läuft",
    "Search was not completed": "Die Suche wurde nicht abgeschlossen",
    "A new job search is running…": "Eine neue Stellensuche läuft…",
    "Sources: search has not run yet": "Quellen: Die Suche wurde noch nicht gestartet",
    "Sources: running a new search; previous results were cleared": (
        "Quellen: Neue Suche läuft; vorherige Ergebnisse wurden gelöscht"
    ),
    "Separate roles with commas; each complete title is an alternative (OR). Enter ‘Administrative Assistant’, not ‘Administrative, Assistant’.": (
        "Trennen Sie Positionen durch Kommas; jede vollständige Bezeichnung ist eine Alternative (ODER). "
        "Geben Sie „Administrative Assistant“ statt „Administrative, Assistant“ ein."
    ),
    "Optional. Example: SAP, Excel. Every requirement must match (AND).": (
        "Optional. Beispiel: SAP, Excel. Jede Anforderung muss erfüllt sein (UND)."
    ),
    "Required. Enter a name and select the exact city from the suggestions; you can add several cities, which are combined with OR.": (
        "Erforderlich. Geben Sie einen Namen ein und wählen Sie den genauen Ort aus den Vorschlägen; "
        "mehrere Orte werden mit ODER verknüpft."
    ),
    "Enter at least 2–3 letters and select a city from the list.": (
        "Geben Sie mindestens 2–3 Buchstaben ein und wählen Sie einen Ort aus der Liste."
    ),
    "The radius is applied separately to each selected city. Bundesagentur sends it to its server; sources without geosearch may filter by name only.": (
        "Der Umkreis wird auf jeden ausgewählten Ort separat angewendet. Die Bundesagentur übermittelt ihn "
        "an ihren Server; Quellen ohne Geosuche filtern möglicherweise nur nach dem Ortsnamen."
    ),
    "Ctrl+Enter — start search; Enter/Space — activate the focused button": (
        "Strg+Eingabe — Suche starten; Eingabe/Leertaste — fokussierte Schaltfläche auslösen"
    ),
    "Matching jobs": "Passende Stellen",
    "Jobs in list: 0": "Stellen in der Liste: 0",
    "Jobs in list: ": "Stellen in der Liste: ",
    "Interesting": "Interessant",
    "Prepare / submit application": "Bewerbung vorbereiten / absenden",
    "Open job": "Stelle öffnen",
    "Open selected job": "Ausgewählte Stelle öffnen",
    "Match": "Übereinstimmung",
    "Job": "Stelle",
    "Company": "Unternehmen",
    "Location": "Ort",
    "Source": "Quelle",
    "Key matches": "Wichtige Übereinstimmungen",
    "View status": "Angesehen",
    "New": "Neu",
    "Viewed": "Angesehen",
    "Status": "Status",
    "Match explanation": "Erklärung der Übereinstimmung",
    "Sort:": "Sortierung:",
    "By relevance": "Nach Relevanz",
    "Newest first": "Neueste zuerst",
    "Oldest first": "Älteste zuerst",
    "No jobs match the selected filters.": "Keine Stellen entsprechen den ausgewählten Filtern.",
    "Select a job from the list.": "Wählen Sie eine Stelle aus der Liste aus.",
    "This job has no link.": "Für diese Stelle ist kein Link vorhanden.",
    "Work mode: ": "Arbeitsmodell: ",
    "Published: ": "Veröffentlicht: ",
    "Link: ": "Link: ",
    "Matched: ": "Übereinstimmungen: ",
    "Missing required: ": "Fehlende Pflichtanforderungen: ",
    "Risks:": "Risiken:",
    "Scoring components:": "Bewertungskomponenten:",
    "Evidence from the job description:": "Belege aus der Stellenbeschreibung:",
    "Description:": "Beschreibung:",
    "Role": "Berufsbild",
    "Experience": "Erfahrung",
    "full": "vollständig",
    "partial": "teilweise",
    "weak": "gering",
    "required": "erforderlich",
    "preferred": "erwünscht",
    "unknown": "unbekannt",
    "Evidence coverage: ": "Belegabdeckung: ",
    "Scheduled search": "Geplante Suche",
    "Daily automatic search": "Tägliche automatische Suche",
    "Enable for active profile": "Für das aktive Profil aktivieren",
    "Time:": "Uhrzeit:",
    "Save schedule": "Zeitplan speichern",
    "Schedule is not configured": "Kein Zeitplan eingerichtet",
    "New and unseen jobs": "Neue und noch nicht angesehene Stellen",
    "Scheduled jobs": "Stellen aus der geplanten Suche",
    "Mark all as seen": "Alle als angesehen markieren",
    "Run now": "Jetzt ausführen",
    "Published": "Veröffentlicht",
    "Last run: ": "Letzte Ausführung: ",
    "All jobs marked as seen": "Alle Stellen wurden als angesehen markiert",
    "Guest mode: create a profile to enable scheduled search.": (
        "Gastmodus: Erstellen Sie ein Profil, um die geplante Suche zu aktivieren."
    ),
    "Scheduled search uses this profile’s saved roles, cities, sources, and filters. If the application was closed, an overdue search will run the next time it opens.": (
        "Die geplante Suche verwendet die gespeicherten Positionen, Orte, Quellen und Filter dieses Profils. "
        "War die Anwendung geschlossen, wird eine überfällige Suche beim nächsten Start ausgeführt."
    ),
    "Application history": "Bewerbungsverlauf",
    "Status history": "Statusverlauf",
    "New status": "Neuer Status",
    "Current status: ": "Aktueller Status: ",
    "Application preparation": "Bewerbung vorbereiten",
    "Match: ": "Übereinstimmung: ",
    "Choose how to prepare an application for this specific job.": (
        "Wählen Sie, wie die Bewerbung für diese Stelle vorbereitet werden soll."
    ),
    "Create a local cover-letter draft": "Lokalen Anschreibenentwurf erstellen",
    "Free mode: create a prompt for AI": "Kostenloser Modus: Prompt für KI erstellen",
    "Continue without a cover letter": "Ohne Anschreiben fortfahren",
    "Use saved cover letter": "Gespeichertes Anschreiben verwenden",
    "The letter is created from verified profile data and job requirements.": (
        "Das Anschreiben wird aus bestätigten Profildaten und Stellenanforderungen erstellt."
    ),
    "The prompt combines processed resume data, the full job context, matches, and rules against inventing facts.": (
        "Der Prompt kombiniert aufbereitete Lebenslaufdaten, den vollständigen Stellenkontext, "
        "Übereinstimmungen und Regeln gegen das Erfinden von Fakten."
    ),
    "Open the job page without generating a letter or prompt.": (
        "Stellenseite öffnen, ohne Anschreiben oder Prompt zu erstellen."
    ),
    "Review the application materials with the previously saved letter.": (
        "Bewerbungsunterlagen mit dem zuvor gespeicherten Anschreiben prüfen."
    ),
    "Local draft": "Lokaler Entwurf",
    "Free AI prompt": "Kostenloser KI-Prompt",
    "Used data and gaps": "Verwendete Daten und Lücken",
    "Future letter settings": "Einstellungen für das Anschreiben",
    "Language": "Sprache",
    "Automatic": "Automatisch",
    "Tone": "Ton",
    "Professional": "Professionell",
    "Warm and personal": "Warm und persönlich",
    "Concise": "Prägnant",
    "Length": "Länge",
    "Short (140–180 words)": "Kurz (140–180 Wörter)",
    "Standard (180–250 words)": "Standard (180–250 Wörter)",
    "Detailed (250–320 words)": "Ausführlich (250–320 Wörter)",
    "Regenerate texts": "Texte neu erstellen",
    "Copy draft": "Entwurf kopieren",
    "Copy AI prompt": "KI-Prompt kopieren",
    "Save locally": "Lokal speichern",
    "Mark as Draft": "Als Entwurf markieren",
    "Continue to submission": "Weiter zum Absenden",
    "Cover letter": "Anschreiben",
    "The draft and prompt use verified data only. Always review the text before sending it.": (
        "Entwurf und Prompt verwenden nur bestätigte Daten. Prüfen Sie den Text immer vor dem Absenden."
    ),
    "Detected: ": "Erkannt: ",
    "Personal angle or motivation (optional; enter truthful facts only)": (
        "Persönlicher Bezug oder Motivation (optional; nur wahrheitsgemäße Angaben)"
    ),
    "Pre-submission review": "Prüfung vor dem Absenden",
    "Submission mode": "Versandmodus",
    "Assisted by JobCompass — recommended": "Mit JobCompass-Unterstützung — empfohlen",
    "Manual — only open the job page": "Manuell — nur die Stellenseite öffnen",
    "Automatic — no verified connector for this source": (
        "Automatisch — kein geprüfter Konnektor für diese Quelle"
    ),
    "Application materials": "Bewerbungsunterlagen",
    "Contact": "Kontakt",
    "Not provided — enter it on the site": "Nicht angegeben — auf der Website eingeben",
    "Choose…": "Auswählen…",
    "Show file": "Datei anzeigen",
    "Copy letter": "Anschreiben kopieren",
    "Save letter as PDF…": "Anschreiben als PDF speichern…",
    "Save cover letter as PDF": "Anschreiben als PDF speichern",
    "Could not create PDF": "PDF konnte nicht erstellt werden",
    "Cover letter PDF saved: ": "PDF des Anschreibens gespeichert: ",
    "Start submission": "Bewerbung starten",
    "Copy letter and open job": "Anschreiben kopieren und Stelle öffnen",
    "Yes, the application was submitted": "Ja, die Bewerbung wurde abgesendet",
    "Possible duplicate application": "Mögliche doppelte Bewerbung",
    "Submission confirmation": "Versandbestätigung",
    "Automatic mode unavailable": "Automatischer Modus nicht verfügbar",
    "No link": "Kein Link",
    "Could not prepare application": "Bewerbung konnte nicht vorbereitet werden",
    "Profile required": "Profil erforderlich",
    "Could not save submission": "Versand konnte nicht gespeichert werden",
    "Review exactly what will be used for the application. JobCompass will not mark it as submitted without your separate confirmation.": (
        "Prüfen Sie genau, was für die Bewerbung verwendet wird. JobCompass markiert sie erst nach Ihrer "
        "separaten Bestätigung als abgesendet."
    ),
    "The cover letter is copied to the clipboard, then the job page is opened.": (
        "Das Anschreiben wird in die Zwischenablage kopiert, danach wird die Stellenseite geöffnet."
    ),
    "Attach the original file to the form. Parsed text is used locally only and is not sent to the employer.": (
        "Fügen Sie die Originaldatei dem Formular bei. Der extrahierte Text wird nur lokal verwendet und "
        "nicht an den Arbeitgeber gesendet."
    ),
    "⚠ An application was already submitted for this job. Sending it again requires additional confirmation.": (
        "⚠ Für diese Stelle wurde bereits eine Bewerbung versendet. Ein erneuter Versand erfordert eine zusätzliche Bestätigung."
    ),
    "An application was already submitted for this job. Open the form again anyway?": (
        "Für diese Stelle wurde bereits eine Bewerbung versendet. Das Formular trotzdem erneut öffnen?"
    ),
    "Select the original PDF or DOCX for assisted mode.": (
        "Wählen Sie für den unterstützten Modus die originale PDF- oder DOCX-Datei aus."
    ),
    "There is no verified connector for this source yet.": "Für diese Quelle gibt es noch keinen geprüften Konnektor.",
    "The job does not contain an application page URL.": "Die Stelle enthält keine URL zur Bewerbungsseite.",
    "The cover letter is empty.": "Das Anschreiben ist leer.",
    "The cover letter was copied to the clipboard.": "Das Anschreiben wurde in die Zwischenablage kopiert.",
    "Confirm only if the employer's site showed that the application was accepted successfully. Save it to history?": (
        "Bestätigen Sie nur, wenn die Arbeitgeberseite die erfolgreiche Annahme der Bewerbung angezeigt hat. "
        "Im Verlauf speichern?"
    ),
    "Create a profile to save the application and its materials?": (
        "Profil erstellen, um die Bewerbung und ihre Unterlagen zu speichern?"
    ),
    "The job page is open. Complete and review the form, attach the original resume, and click Submit on the site. After success, return here and confirm the submission.": (
        "Die Stellenseite ist geöffnet. Füllen Sie das Formular aus, prüfen Sie es, fügen Sie den originalen "
        "Lebenslauf bei und senden Sie es auf der Website ab. Kehren Sie anschließend hierher zurück und bestätigen Sie den Versand."
    ),
    "The cover letter was copied and the job page is open. Complete and review the form, attach the original resume, and click Submit on the site. After success, return here and confirm the submission.": (
        "Das Anschreiben wurde kopiert und die Stellenseite ist geöffnet. Füllen Sie das Formular aus, prüfen "
        "Sie es, fügen Sie den originalen Lebenslauf bei und senden Sie es auf der Website ab. Kehren Sie "
        "anschließend hierher zurück und bestätigen Sie den Versand."
    ),
    "Application confirmed and recorded: ": "Bewerbung bestätigt und gespeichert: ",
    "Submitted materials:": "Versendete Unterlagen:",
    "manual mode": "manueller Modus",
    "assisted by JobCompass": "mit JobCompass-Unterstützung",
    "automatic mode": "automatischer Modus",
    "used": "verwendet",
    "not used": "nicht verwendet",
    "JobCompass settings": "JobCompass-Einstellungen",
    "Interface language": "Oberflächensprache",
    "Applied immediately and saved for all profiles.": "Wird sofort angewendet und für alle Profile gespeichert.",
    "Interface language changed": "Oberflächensprache geändert",
    "Global application settings that do not depend on the candidate profile.": (
        "Allgemeine Anwendungseinstellungen, die nicht vom Kandidatenprofil abhängen."
    ),
    "Guest mode: the resume, favorites, views, and applications are kept only until the application is closed.": (
        "Gastmodus: Lebenslauf, Favoriten, Ansichten und Bewerbungen bleiben nur bis zum Schließen der Anwendung erhalten."
    ),
    "Profiles, jobs, and history are stored locally only. JobCompass does not send resumes or data to AI services.": (
        "Profile, Stellen und Verlauf werden ausschließlich lokal gespeichert. JobCompass sendet keine Lebensläufe oder Daten an KI-Dienste."
    ),
    "Jobs: Bundesagentur, Arbeitnow, and Remotive are connected; availability depends on external services.\nCity suggestions: Open-Meteo Geocoding / GeoNames, keyless for non-commercial use; only city text is submitted.\nJSON import remains an auxiliary mode for tests and custom data.\nResumes: JSON, TXT, DOCX, and text-based PDF are processed locally.\nCover letters, free mode: local draft and enhanced prompt are available.\nCover letters, AI/API mode: planned; tokens are not accepted and no external AI calls are made.": (
        "Stellen: Bundesagentur, Arbeitnow und Remotive sind angebunden; die Verfügbarkeit hängt von externen Diensten ab.\n"
        "Ortsvorschläge: Open-Meteo Geocoding / GeoNames, ohne Schlüssel für nichtkommerzielle Nutzung; übertragen wird nur der Ortstext.\n"
        "Der JSON-Import bleibt ein Hilfsmodus für Tests und eigene Daten.\n"
        "Lebensläufe: JSON, TXT, DOCX und textbasierte PDF werden lokal verarbeitet.\n"
        "Anschreiben, kostenloser Modus: Lokaler Entwurf und verbesserter Prompt sind verfügbar.\n"
        "Anschreiben, KI/API-Modus: geplant; Tokens werden noch nicht angenommen und es erfolgen keine externen KI-Aufrufe."
    ),
    "Updates": "Aktualisierungen",
    "Check for updates": "Nach Aktualisierungen suchen",
    "Check again": "Erneut prüfen",
    "Try again": "Erneut versuchen",
    "Current version: ": "Aktuelle Version: ",
    "Check whether a new JobCompass version is available.": "Prüfen Sie, ob eine neue JobCompass-Version verfügbar ist.",
    "Checking for updates…": "Aktualisierungen werden geprüft…",
    "Download and install": "Herunterladen und installieren",
    "Download portable version": "Portable-Version herunterladen",
    "Open update page": "Aktualisierungsseite öffnen",
    "Install update": "Aktualisierung installieren",
    "Update downloaded": "Aktualisierung heruntergeladen",
    "Local data": "Lokale Daten",
    "Storage file": "Speicherdatei",
    "Profile management": "Profilverwaltung",
    "Connectors and formats": "Konnektoren und Formate",
    "Import jobs from JSON": "Stellen aus JSON importieren",
    "Import profile": "Profil importieren",
    "Export profile": "Profil exportieren",
    "Duplicate profile": "Profil duplizieren",
    "Rename profile": "Profil umbenennen",
    "Delete profile": "Profil löschen",
    "Unsaved changes": "Ungespeicherte Änderungen",
    "Saved": "Gespeichert",
    "Updated": "Aktualisiert",
    "Could not save": "Speichern fehlgeschlagen",
    "Could not update status": "Status konnte nicht aktualisiert werden",
    "Could not read resume": "Lebenslauf konnte nicht gelesen werden",
    "Could not create profile": "Profil konnte nicht erstellt werden",
    "Could not save profile": "Profil konnte nicht gespeichert werden",
    "Could not save schedule": "Zeitplan konnte nicht gespeichert werden",
    "Could not open folder": "Ordner konnte nicht geöffnet werden",
    "Could not start installer": "Installationsprogramm konnte nicht gestartet werden",
    "Some sources are unavailable": "Einige Quellen sind nicht verfügbar",
    "Job import": "Stellenimport",
    "Import complete": "Import abgeschlossen",
    "New portable version saved to: ": "Neue Portable-Version gespeichert unter: ",
    "A new version is available: ": "Eine neue Version ist verfügbar: ",
    "JobCompass update available: ": "JobCompass-Aktualisierung verfügbar: ",
    "You have the latest JobCompass version ": "Sie verwenden die aktuelle JobCompass-Version ",
    "What changed:\n": "Änderungen:\n",
}


INLINE_EN_TO_DE = {
    "Scheduled (": "Zeitplan (",
    "Cover letter — ": "Anschreiben — ",
    "Match: ": "Übereinstimmung: ",
    "Choose how to prepare an application for this specific job.": (
        "Wählen Sie, wie die Bewerbung für diese Stelle vorbereitet werden soll."
    ),
    "Detected: ": "Erkannt: ",
    "Jobs in list: ": "Stellen in der Liste: ",
    "Work mode: ": "Arbeitsmodell: ",
    "Published: ": "Veröffentlicht: ",
    "Link: ": "Link: ",
    "Matched: ": "Übereinstimmungen: ",
    "Missing required: ": "Fehlende Pflichtanforderungen: ",
    "Evidence coverage: ": "Belegabdeckung: ",
    "Last run: ": "Letzte Ausführung: ",
    "Current status: ": "Aktueller Status: ",
    "Current version: ": "Aktuelle Version: ",
    "Application confirmed and recorded: ": "Bewerbung bestätigt und gespeichert: ",
    "New portable version saved to: ": "Neue Portable-Version gespeichert unter: ",
    "A new version is available: ": "Eine neue Version ist verfügbar: ",
    "JobCompass update available: ": "JobCompass-Aktualisierung verfügbar: ",
    "You have the latest JobCompass version ": "Sie verwenden die aktuelle JobCompass-Version ",
    "What changed:\n": "Änderungen:\n",
    "Suggestions found: ": "Gefundene Vorschläge: ",
    "City already selected: ": "Ort bereits ausgewählt: ",
    "Active profile: ": "Aktives Profil: ",
}

EN_TO_DE.update(
    {
        "\nSubmitted materials:": "\nVersendete Unterlagen:",
        "\nEvents:": "\nEreignisse:",
        "  Cover letter: ": "  Anschreiben: ",
        " — please wait": " — bitte warten",
        "Online sources returned no jobs for the selected roles, locations, and radius.": "Die Online-Quellen haben für die ausgewählten Positionen, Orte und den Umkreis keine Stellen geliefert.",
        "Other sources were processed.\n\n": "Andere Quellen wurden verarbeitet.\n\n",
        "Automatic search requires a profile. Create one now?": "Die automatische Suche benötigt ein Profil. Jetzt eines erstellen?",
        "The job for this application was not found.": "Die Stelle zu dieser Bewerbung wurde nicht gefunden.",
        "Jobs were found but hidden by filters": "Stellen wurden gefunden, aber durch Filter ausgeblendet",
        "Enter at least 2–3 letters of the city name.": "Geben Sie mindestens 2–3 Buchstaben des Ortsnamens ein.",
        "Enter a name or profile title:": "Geben Sie einen Namen oder eine Profilbezeichnung ein:",
        "Select the city to remove from the list.": "Wählen Sie den zu entfernenden Ort aus der Liste aus.",
        "Select a resume": "Lebenslauf auswählen",
        "Wait for the search to finish before updating.": "Warten Sie vor der Aktualisierung, bis die Suche abgeschlossen ist.",
        "Wait for the search to finish before switching profiles.": "Warten Sie vor dem Profilwechsel, bis die Suche abgeschlossen ist.",
        "Close JobCompass and extract the new portable version. Keep the data folder and portable.flag file.": "Schließen Sie JobCompass und entpacken Sie die neue Portable-Version. Behalten Sie den Ordner data und die Datei portable.flag bei.",
        "Close the application and interrupt the current search?": "Anwendung schließen und die laufende Suche abbrechen?",
        "Starting the overdue daily search…": "Die überfällige tägliche Suche wird gestartet…",
        "Save the current profile before creating a new one?": "Aktuelles Profil vor dem Erstellen eines neuen Profils speichern?",
        "Save the current profile and settings before switching?": "Aktuelles Profil und Einstellungen vor dem Wechsel speichern?",
        "Save the current profile and settings before exiting?": "Aktuelles Profil und Einstellungen vor dem Beenden speichern?",
        "Save the current profile and settings before updating?": "Aktuelles Profil und Einstellungen vor der Aktualisierung speichern?",
        "Save the current roles, cities, and filters before running?": "Aktuelle Positionen, Orte und Filter vor dem Start speichern?",
        "Copy": "Kopie",
        "The city was added without geographic verification; select a suggestion when possible.": "Der Ort wurde ohne geografische Prüfung hinzugefügt; wählen Sie nach Möglichkeit einen Vorschlag aus.",
        "City not found. Check the spelling or add the entered value manually.": "Ort nicht gefunden. Prüfen Sie die Schreibweise oder fügen Sie die Eingabe manuell hinzu.",
        "Copy name (history and applications are not copied):": "Name der Kopie (Verlauf und Bewerbungen werden nicht kopiert):",
        "Could not delete profile": "Profil konnte nicht gelöscht werden",
        "Could not duplicate profile": "Profil konnte nicht dupliziert werden",
        "Could not export profile": "Profil konnte nicht exportiert werden",
        "Could not save results": "Ergebnisse konnten nicht gespeichert werden",
        "Could not rename profile": "Profil konnte nicht umbenannt werden",
        "Could not import jobs": "Stellen konnten nicht importiert werden",
        "Could not import profile": "Profil konnte nicht importiert werden",
        "There is no active profile.": "Es ist kein Profil aktiv.",
        "New profile name:": "Neuer Profilname:",
        "Select at least one suggested city or click ‘Add entered city without verification’.": "Wählen Sie mindestens einen vorgeschlagenen Ort aus oder klicken Sie auf „Eingegebenen Ort ungeprüft hinzufügen“.",
        "Favorites and application history are not saved in guest mode. Create a profile now?": "Favoriten und Bewerbungsverlauf werden im Gastmodus nicht gespeichert. Jetzt ein Profil erstellen?",
        "The update has been verified and is ready to install. JobCompass will close. Start the installer now?": "Die Aktualisierung wurde geprüft und kann installiert werden. JobCompass wird geschlossen. Installationsprogramm jetzt starten?",
        "The latest online search returned no jobs, so changing the threshold cannot change the list. Check the source status above the table.": "Die letzte Onlinesuche lieferte keine Stellen. Eine Änderung des Schwellenwerts kann die Liste daher nicht ändern. Prüfen Sie den Quellenstatus über der Tabelle.",
        "Check: ": "Prüfen: ",
        "Transfer guest data?": "Gastdaten übertragen?",
        "Transfer the current resume, filters, results, and favorites to the new profile?": "Aktuellen Lebenslauf, Filter, Ergebnisse und Favoriten in das neue Profil übertragen?",
        "Scheduled search stores new jobs separately for each candidate. Create a profile?": "Die geplante Suche speichert neue Stellen für jeden Kandidaten separat. Profil erstellen?",
        "Searching…": "Suche…",
        "Profile exported successfully.": "Profil erfolgreich exportiert.",
        "The profile and all search settings were saved locally": "Das Profil und alle Sucheinstellungen wurden lokal gespeichert",
        "Profile, resume, cities, roles, filters, and schedule were saved.": "Profil, Lebenslauf, Orte, Positionen, Filter und Zeitplan wurden gespeichert.",
        "The resume is active in the current session. You can correct the fields before saving.\n\n": "Der Lebenslauf ist in der aktuellen Sitzung aktiv. Sie können die Felder vor dem Speichern korrigieren.\n\n",
        "Resume loaded — click ‘Save profile’ to keep it after closing": "Lebenslauf geladen — klicken Sie auf „Profil speichern“, um ihn nach dem Schließen zu behalten",
        "The schedule and current search settings were saved.\n\n": "Der Zeitplan und die aktuellen Sucheinstellungen wurden gespeichert.\n\n",
        "Select a job first.": "Wählen Sie zuerst eine Stelle aus.",
        "Select an application first.": "Wählen Sie zuerst eine Bewerbung aus.",
        "Create a profile first.": "Erstellen Sie zuerst ein Profil.",
        "Text copied to the clipboard": "Text in die Zwischenablage kopiert",
        "The required installer file is missing from the GitHub Release.": "Die erforderliche Installationsdatei fehlt im GitHub Release.",
        "Guest mode enabled": "Gastmodus aktiviert",
        "All files": "Alle Dateien",
        "The draft, prompt, and selected settings were saved locally.": "Entwurf, Prompt und ausgewählte Einstellungen wurden lokal gespeichert.",
        "Create a profile to save applications and cover letters. Create one now?": "Erstellen Sie ein Profil, um Bewerbungen und Anschreiben zu speichern. Jetzt erstellen?",
        "excluded companies: ": "ausgeschlossene Unternehmen: ",
        "excluded words: ": "ausgeschlossene Wörter: ",
        "additional requirements: ": "zusätzliche Anforderungen: ",
        "no online sources selected": "keine Online-Quellen ausgewählt",
        "has not run yet": "noch nicht ausgeführt",
        "Received after source filters: ": "Nach Quellenfiltern erhalten: ",
        "Online search: ": "Onlinesuche: ",
        "Link": "Link",
        "Remote": "Remote",
        "Hybrid": "Hybrid",
        "Office": "Vor Ort",
        "Email": "E-Mail",
        "JobCompass profile": "JobCompass-Profil",
        "Vacancy-specific cover letter draft created": "Stellenspezifischer Anschreibenentwurf erstellt",
    }
)

INLINE_EN_TO_DE.update(
    {
        "\n\nContinue anyway?": "\n\nTrotzdem fortfahren?",
        "\n\nWindows background task: ": "\n\nWindows-Hintergrundaufgabe: ",
        "\nNewly added: ": "\nNeu hinzugefügt: ",
        "\nLast updated: ": "\nZuletzt aktualisiert: ",
        "  Address: ": "  Adresse: ",
        "  Resume: ": "  Lebenslauf: ",
        " (installed ": " (installiert ",
        " (partial results)": " (Teilergebnisse)",
        " | received: ": " | erhalten: ",
        " | at threshold ": " | bei Schwellenwert ",
        " | after merging and JobCompass filters: ": " | nach Zusammenführung und JobCompass-Filtern: ",
        " jobs for the roles and locations, but additional filters removed them.\n\n": " Stellen für die Positionen und Orte, die jedoch durch zusätzliche Filter entfernt wurden.\n\n",
        " jobs. Highest available score: ": " Stellen. Höchste verfügbare Bewertung: ",
        " jobs. Highest score: ": " Stellen. Höchster Wert: ",
        " and verifying SHA-256…": " und SHA-256 wird geprüft…",
        " — copy": " — Kopie",
        "% displayed: ": "% angezeigt: ",
        "% hidden ": "% ausgeblendet ",
        "% — without querying the sites again": "% — ohne erneute Abfrage der Websites",
        "%, configured threshold: ": "%, eingestellter Schwellenwert: ",
        "%. Lower the minimum match.": "%. Senken Sie die Mindestübereinstimmung.",
        ", new jobs added: ": ", neue Stellen hinzugefügt: ",
        ". Open ⚙.": ". Öffnen Sie ⚙.",
        ". Select the exact city from the list.": ". Wählen Sie den genauen Ort aus der Liste.",
        ". All personal data is isolated from other profiles.": ". Alle personenbezogenen Daten sind von anderen Profilen getrennt.",
        ": error": ": Fehler",
        "’ together with its applications, favorites, and schedule?": "“ zusammen mit Bewerbungen, Favoriten und Zeitplan endgültig löschen?",
        "Automatic search complete: new jobs — ": "Automatische Suche abgeschlossen: neue Stellen — ",
        "Automatic search not started: ": "Automatische Suche nicht gestartet: ",
        "Profile activated: ": "Profil aktiviert: ",
        "Jobs reaching the match threshold: ": "Stellen ab dem Übereinstimmungsschwellenwert: ",
        "Added: ": "Hinzugefügt: ",
        "Downloading ": "Herunterladen von ",
        "Found ": "Gefunden: ",
        "Local threshold changed to ": "Lokaler Schwellenwert geändert auf ",
        "An application was already submitted for this job or it has a post-submission status.\n\nStatus: ": "Für diese Stelle wurde bereits eine Bewerbung versendet oder sie hat einen Status nach dem Versand.\n\nStatus: ",
        "Permanently delete profile ‘": "Profil „",
        "Could not download update: ": "Aktualisierung konnte nicht heruntergeladen werden: ",
        "Could not check for updates: ": "Aktualisierungen konnten nicht geprüft werden: ",
        "Note: ": "Notiz: ",
        "Partial results received; subsequent pages are unavailable: ": "Teilergebnisse erhalten; weitere Seiten sind nicht verfügbar: ",
        "Matching jobs displayed: ": "Angezeigte passende Stellen: ",
        "Schedule error: ": "Zeitplanfehler: ",
        "Threshold ": "Schwellenwert ",
        "Read ": "Gelesen ",
        "Read: ": "Gelesen: ",
        "Profile created: ": "Profil erstellt: ",
        "Application materials saved: ": "Bewerbungsunterlagen gespeichert: ",
    }
)
