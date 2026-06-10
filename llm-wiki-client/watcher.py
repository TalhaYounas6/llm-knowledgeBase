import os
import time
import json
import requests
import pwinput
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import re

# CONFIGURATION
SERVER_URL         = "http://localhost:3000"
CONFIG_FILE        = "config.json"
INPUT_FOLDER       = "./Raw_Sources"
OUTPUT_FOLDER      = "./Wiki_Notes"
ALLOW_DEFAULT_LLM  = False
LOG_TAIL_LINES     = 20        # number of recent log entries to send to the engine

# Local Wiki Paths
NOTES_DIR    = os.path.join(OUTPUT_FOLDER, "notes")
CONCEPTS_DIR = os.path.join(OUTPUT_FOLDER, "concepts")
ENTITIES_DIR = os.path.join(OUTPUT_FOLDER, "entities")
INDEX_PATH   = os.path.join(OUTPUT_FOLDER, "index.md")
LOG_PATH     = os.path.join(OUTPUT_FOLDER, "log.md")
SCHEMA_PATH  = os.path.join(OUTPUT_FOLDER, "SCHEMA.md")

# Ensure all local directories exist
for folder in [INPUT_FOLDER, OUTPUT_FOLDER, NOTES_DIR, CONCEPTS_DIR, ENTITIES_DIR]:
    os.makedirs(folder, exist_ok=True)


# DEFAULT SCHEMA TEMPLATE
# Written to SCHEMA.md on first run.
DEFAULT_SCHEMA = """# Wiki Schema & Constitution

> The LLM's operating manual. Every operation — Ingest, Query, Lint — reads this file first.
> Edit the categories, wikilink targets, and domain notes to match your knowledge domain.

---

## 1. Architecture

This wiki follows Andrej Karpathy's LLM-Maintained Wiki pattern.
The core idea: instead of re-deriving knowledge from raw sources at query time (RAG),
the LLM incrementally builds and maintains a persistent, interlinked wiki.
Knowledge is compiled once and kept current — not re-discovered on every question.

Three layers:
- Raw Sources    → your uploaded documents (immutable, never modified)
- The Wiki       → this directory (LLM writes and maintains everything here)
- This Schema    → the LLM's constitution for how to operate on the wiki

---

## 2. Directory Structure

Wiki_Notes/
├── SCHEMA.md          ← This file. Read before every operation.
├── index.md           ← Master catalog. Entry point for all queries. Append-only.
├── log.md             ← Chronological audit trail. Append-only always.
├── notes/             ← One file per ingested source document.
├── concepts/          ← Synthesized topic pages. Created when a theme recurs
│                         across 3+ notes. Never tied to a single source.
└── entities/          ← Dedicated pages for people, tools, organisations,
                          frameworks, and datasets that appear across multiple notes.

---

## 3. Page Types

notes/
  Created once per ingested source. Depth scales to the source —
  a 2-page article gets a thorough single-page note, a 50-page paper
  gets an exhaustive multi-section breakdown. Never a summary.

concepts/
  Created by the lint service or persist-query route when a theme,
  methodology, or idea recurs across multiple notes and deserves its
  own synthesized page. Examples: a concept page for "Noisy Channel Model"
  once 3+ notes reference it, or a comparison page generated from a query.

entities/
  Created for named things that appear across multiple notes:
  a researcher whose work spans several papers, a tool used in multiple
  experiments, an organisation referenced repeatedly.
  One entity page per named thing — not one per mention.

---

## 4. Operations

INGEST
  Triggered when a new source document is dropped into Raw_Sources/.
  The LLM reads the source, produces a structured note, identifies cross-links
  to existing pages, and returns an integration plan.
  watcher.py executes the plan locally: saves the note, updates index.md,
  backfills cross-links into related pages, appends to log.md.
  A single ingest may touch 5-15 wiki pages via cross-link backfill.

QUERY
  The LLM reads index.md as its entry point, identifies relevant pages,
  reads them via tool calls, follows wikilinks when relevant, and synthesizes
  an answer with citations. The LLM navigates the wiki autonomously —
  it is never handed a pre-selected context blob.
  Good answers that contain novel synthesis should be filed back into the wiki
  via the PERSIST operation. Knowledge compounds — it does not disappear into chat.

LINT
  Periodic health check. Scans recently modified pages for:
  orphan pages (no inbound links), contradictions between pages,
  stale claims superseded by newer notes, missing concept pages
  (wikilinks appearing in 3+ notes with no corresponding file),
  and suggested new sources to ingest.
  Lint reports are saved as concept pages and integrated into the wiki.

PERSIST
  Takes a query answer worth keeping and files it as a new page in concepts/.
  Triggers the same integration logic as INGEST: index update, log entry.
  This is how the wiki grows from questions, not just from uploaded documents.

---

## 5. Index Entry Format

One line per page, pipe-separated, inserted under the correct category header:
| [[Filename]] | One-sentence summary | Category | YYYY-MM-DD |

The [[Filename]] must match the exact filename on disk without the .md extension.

---

## 6. Index Categories

Expand this list when General accumulates enough entries on a specific theme.
Never invent new categories during ingest — only use categories listed here.

- NLP & Linguistics
- Machine Learning
- Systems & Architecture
- Personal Knowledge Management
- Meetings & Notes
- Journal & Reflections
- General

---

## 7. Log Entry Format

## [YYYY-MM-DD HH:MM] ACTION | Title | Files Affected
ACTION must be one of: INGEST | QUERY | PERSIST | LINT | EDIT

Example entries:
## [2026-05-10 14:32] INGEST | Real_Word_Spelling_Errors | Real_Word_Spelling_Errors, NLP_Preprocessing
## [2026-05-10 15:01] QUERY | "How does Urdu handle real-word errors?" | answered
## [2026-05-10 15:04] PERSIST | Urdu_vs_English_Comparison | concepts/Urdu_vs_English_Comparison.md
## [2026-05-11 09:00] LINT | Weekly pass | 8 pages scanned

---

## 8. Cross-Link Rule

All connections are bidirectional.
When a new note is ingested and relates to an existing page,
that existing page must be updated to reference the new note back.
The wiki is a graph — edges run in both directions.

---

## 9. Compounding Rule

Good query answers must not disappear into chat history.
When a query produces a synthesis, comparison, or connection that does not
exist as its own page, it should be filed via PERSIST into concepts/.
Every question asked is an opportunity to make the wiki richer.
The wiki grows from ingestion AND from exploration.

---

## 10. Mandatory Wikilink Targets

Any note touching these concepts must wikilink them without exception.
Edit this list to match your domain — these are just defaults.

- [[Machine Learning]]
- [[Natural Language Processing]]
- [[Large Language Model]]
- [[Obsidian]]

---

## 11. Domain Notes

Use this section to record domain-specific conventions for your wiki.
The LLM reads this on every operation — use it to guide emphasis,
terminology preferences, recurring entities, and known relationships.

Example:
  This wiki focuses on Urdu NLP research. Key recurring entities:
  [[Urdu Language]], [[Spell Checking]], [[Noisy Channel Model]].
  When ingesting papers, always check for connections to corpus size,
  evaluation metrics (precision, recall, F1), and baseline comparisons.

(Edit this section to describe your own domain.)
"""

# DEFAULT INDEX TEMPLATE
DEFAULT_INDEX = """# Wiki Index

> Master catalog of all pages. Updated on every ingest.
> Format: | [[Filename]] | Summary | Category | Date |
> Query with: grep the category headers to find relevant sections.

## NLP & Linguistics
| Page | Summary | Category | Date |
|------|---------|----------|------|

## Machine Learning
| Page | Summary | Category | Date |
|------|---------|----------|------|

## Systems & Architecture
| Page | Summary | Category | Date |
|------|---------|----------|------|

## Personal Knowledge Management
| Page | Summary | Category | Date |
|------|---------|----------|------|

## General
| Page | Summary | Category | Date |
|------|---------|----------|------|

"""

# DEFAULT LOG TEMPLATE 
DEFAULT_LOG = f"""# Wiki Log
> Append-only chronological record of all wiki operations.
> Query with: grep "^## \\[" log.md | tail -20
>
> Format: ## [YYYY-MM-DD HH:MM] ACTION | Title | Files Affected
> ACTION types: INGEST | QUERY | PERSIST | LINT | EDIT
>
> Example entries:
> ## [2026-01-01 09:00] INGEST | My_First_Note | My_First_Note, Existing_Page
> ## [2026-01-01 09:05] QUERY | "What is X?" | My_First_Note
> ## [2026-01-01 09:10] PERSIST | Comparison_X_vs_Y | concepts/Comparison_X_vs_Y.md

## [{datetime.now().strftime("%Y-%m-%d %H:%M")}] INGEST | Wiki Initialized | SCHEMA.md, index.md, log.md

"""


# Make Special Files
def bootstrap_wiki():
    """
    Creates SCHEMA.md, index.md, and log.md with full default content
    on first run. Never overwrites existing files.
    """
    if not os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
            f.write(DEFAULT_SCHEMA)
        print("Created SCHEMA.md with default template. Edit it to match your domain.")

    if not os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            f.write(DEFAULT_INDEX)
        print("Created index.md with category structure.")

    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write(DEFAULT_LOG)
        print("Created log.md.")


# --- HELPER FUNCTIONS ---
def save_local_key(api_key):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"api_key": api_key}, f)

def get_local_key():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("api_key")
    return None

def verify_token(api_key):
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        res = requests.get(f"{SERVER_URL}/user/get-status", headers=headers)
        if res.status_code == 200:
            print(f"Authenticated! Daily Quota: {res.json().get('usage')}")
            return True
        return False
    except requests.exceptions.ConnectionError:
        print("Check your internet connection.")
        return False

def ask_user(prompt_text, is_password=False):
    display_prompt = f"{prompt_text} (or type 'back'): "
    while True:
        if is_password:
            val = pwinput.pwinput(prompt=display_prompt, mask="*")
        else:
            val = input(display_prompt)

        val = val.strip()

        if val.lower() in ['back', 'cancel', 'exit']:
            print("\nAction cancelled. Returning to menu...")
            return None

        if not val:
            print("Input cannot be empty. Please try again.")
            continue

        return val

def get_log_tail(n=LOG_TAIL_LINES):
   
    if not os.path.exists(LOG_PATH):
        return ""
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    # Each entry starts with "## ["
    entries=[]
    cont = content.split("\n## [")
    for e in cont:
        if e.strip():
            entries.append(e)
  
    tail = entries[-n:] if len(entries) > n else entries
    return "\n## [".join(tail)


# LOCAL VAULT UTILITIES
def find_local_page(name):
    """Searches all wiki subdirectories for an existing page to backlink."""
    for subdir in [NOTES_DIR, CONCEPTS_DIR, ENTITIES_DIR]:
        candidate = os.path.join(subdir, f"{name}.md")
        if os.path.exists(candidate):
            return candidate
    return None

def backfill_local_crosslink(target_path, new_note_name):
    """
    Appends a backlink to an existing page's Vault Pages subsection.
    Never rewrites the file — only appends. Skips if link already exists.
    """
    with open(target_path, "r", encoding="utf-8") as f:
        content = f.read()

    backlink = f"- [[{new_note_name}]]"
    if backlink in content:
        return  # Already linked, skip

    # Target the Vault Pages subsection specifically
    # This is where backlinks belong per the note structure
    if "### Vault Pages" in content:
        new_content = content.replace(
            "(backfilled automatically on ingest)",
            f"(backfilled automatically on ingest)\n{backlink}"
        )

    # Fallback: older notes or notes without Vault Pages subsection
    # Check for any variant of the References section header
    elif re.search(r'##\s+(?:\d+\.\s+)?References', content, re.IGNORECASE):
        new_content = content + f"\n{backlink}"

    else:
        # No References section at all — create the full structure
        new_content = (
            content +
            f"\n\n## References and Related\n\n"
            f"### Vault Pages\n"
            f"(backfilled automatically on ingest)\n"
            f"{backlink}"
        )

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(new_content)

def append_to_log(action, title, affected_files):
    
    timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M")
    affected_str = ", ".join(affected_files)
    log_line     = f"\n## [{timestamp}] {action} | {title} | {affected_str}"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(log_line)

def append_to_index(index_entry, category):
    """
    Inserts the index entry under the correct category section.
    If the category doesn't exist yet, creates a new section.
    Never rewrites existing entries.
    """
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    section_header = f"## {category}\n"
    new_entry = f"{index_entry}\n"
    inserted = False
    new_lines = []
    i = 0

    while i < len(lines):
        new_lines.append(lines[i])
        if lines[i] == section_header:
            # Append the table header row
            if i + 1 < len(lines):
                new_lines.append(lines[i + 1])
                i += 1
            # Only insert after the divider row, verify it actually is one
            if i + 1 < len(lines) and lines[i + 1].startswith("|---"):
                new_lines.append(lines[i + 1])
                i += 1
                new_lines.append(new_entry)
                inserted = True
        i += 1
    if not inserted:
        # Category doesn't exist yet sop append a new section at the end
        new_lines.append(f"\n## {category}\n")
        new_lines.append("| Page | Summary | Category | Date |\n")
        new_lines.append("|------|---------|----------|------|\n")
        new_lines.append(new_entry)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

# QUERY UTILITIES

def read_local_page(filename):
    # reads a page from any vault subdirectory by filename without extension
    path = find_local_page(filename)
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def send_query(api_key, question, page_contents=None):
    # sends query to server with index, schema, and any pre-loaded page contents
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index_text = f.read()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_text = f.read()

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "question":     question,
        "indexText":    index_text,
        "schemaText":   schema_text,
        "pageContents": page_contents or {}
    }

    response = requests.post(
        f"{SERVER_URL}/wiki/query",
        json=payload,
        headers=headers
    )

    if response.status_code == 200:
        return response.json()
    else:
        err = response.json().get("message", response.text)
        raise Exception(f"Query failed: {err}")


def persist_answer(answer, question, api_key):
    today     = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug      = re.sub(r'[^a-zA-Z0-9 ]', '', question)[:50].strip().replace(" ", "_")
    filename  = f"Query_{slug}_{timestamp}"

    # extract wikilinks from the answer — these are the pages the model cited
    cited_pages = re.findall(r'\[\[([^\]]+)\]\]', answer)
    # deduplicate while preserving order
    seen = set()
    unique_cited = []
    for p in cited_pages:
        if p not in seen:
            seen.add(p)
            unique_cited.append(p)

    # build vault pages section from cited wikilinks
    if unique_cited:
        vault_pages_lines = "\n".join(f"- [[{p}]]" for p in unique_cited)
    else:
        vault_pages_lines = "(backfilled automatically on ingest)"

    note_content = f"""---
title: "{question[:80]}"
aliases: []
tags:
  - query/persisted
doc_type: "Query"
date_noted: "{today}"
status: fresh
---

## Query

{question}

## Answer

{answer}

## References and Related

### Vault Pages

{vault_pages_lines}
"""

    note_path = os.path.join(CONCEPTS_DIR, f"{filename}.md")
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(note_content)
    print(f"Saved: {filename}.md")

    # backfill bidirectionally — the cited pages should link back to this concept
    affected = [f"concepts/{filename}.md"]
    for cited in unique_cited:
        target_path = find_local_page(cited)
        if target_path:
            backfill_local_crosslink(target_path, filename)
            affected.append(cited)
            print(f"  Backfilled link into: {cited}.md")
        else:
            print(f"  Cited page not found on disk: {cited}")

    index_entry = f"| [[{filename}]] | Persisted query: {question[:60]} | General | {today} |"
    append_to_index(index_entry, "General")
    append_to_log("PERSIST", filename, affected)
    print("Index and log updated.")

def action_query(api_key):
    print("\n--- QUERY WIKI ---")
    print("Ask a question about your knowledge base.")
    print("Type 'back' to return to the menu.\n")

    question = ask_user("Your question")
    if not question:
        return

    print("Reading local vault context...")

    try:
        # first call — no page contents, let the model identify what it needs
        print("Sending query to server...")
        result = send_query(api_key, question)

        if result.get("status") == "missing_pages":
            missing = result.get("missingPages", [])
            print(f"\n  Model needs {len(missing)} page(s): {missing}")

            page_contents = {}
            for page in missing:
                # strip .md and any path prefix the model may have included
                name = os.path.basename(page).replace(".md", "")
                content = read_local_page(name)
                if content:
                    page_contents[page] = content
                    print(f"  Loaded: {page}")
                else:
                    print(f"  Not found locally: {page}")

            if not page_contents:
                print("  None of the requested pages were found locally.")
                return

            print("  Retrying with page contents...")
            result = send_query(api_key, question, page_contents)

        answer = result.get("answer")
        if not answer:
            print("No answer returned.")
            return

        print("\n" + "="*60)
        print("ANSWER")
        print("="*60)
        print(answer)
        print("="*60 + "\n")

        append_to_log("QUERY", f'"{question[:60]}"', ["answered"])

        if "wiki-worthy? yes" in answer.lower():
            print("The answer was flagged as wiki-worthy.")
            save = input("Save to wiki? (y/n): ").strip().lower()
        else:
            save = input("Save this answer to the wiki? (y/n): ").strip().lower()

        if save == "y":
            persist_answer(answer, question, api_key)
            print("Answer saved to concepts/ and indexed.")

    except requests.exceptions.ConnectionError:
        print("Could not connect to server.")
    except Exception as e:
        print(f"Query failed: {e}")

# POLLING & EXECUTION LOGIC
def poll_for_result(job_id, api_key, original_filename):
    print(f"  Waiting for Cloud AI to process '{original_filename}'...")
    headers = {"Authorization": f"Bearer {api_key}"}

    
    try:
        while True:
            try:
                res = requests.get(f"{SERVER_URL}/wiki/job/{job_id}", headers=headers)

                if res.status_code == 200:
                    job_data = res.json()
                    status   = job_data.get("status")
                    error_msg = job_data.get("error_message")

                    if status == "completed":
                        print("\n  AI finished. Executing integration plan locally...")
                        plan = job_data.get("markdown_content", {}) # Changed plan to markdown_content

                        note_filename = plan.get(
                            "note_filename",
                            os.path.splitext(original_filename)[0].replace(" ", "_")
                        )

                        # Step 1: Save the new note 
                        note_path = os.path.join(NOTES_DIR, f"{note_filename}.md")
                        with open(note_path, "w", encoding="utf-8") as f:
                            f.write(plan.get("note_content", ""))
                        print(f"Saved note: {note_filename}.md")

                        # Step 2: Append to index (never rewrite)
                        index_entry    = plan.get("index_entry", "")
                        index_category = plan.get("index_category", "General")
                        if index_entry:
                            append_to_index(index_entry, index_category)
                        print("Index updated")

                        # Step 3: Backfill cross-links (bidirectional) 
                        affected = [note_filename]
                        for target in plan.get("cross_links", []):
                            target_path = find_local_page(target)
                            if target_path:
                                backfill_local_crosslink(target_path, note_filename)
                                affected.append(target)
                                print(f"Backfilled link into: {target}.md")
                            else:
                                print(f"Cross-link target not found on disk: {target}")

                        # Step 4: Append to log 
                        append_to_log("INGEST", note_filename, affected)
                        print("Log updated")

                        print(f"\n  Integration complete. Vault is up to date!")
                        break

                    elif status == "failed":
                        print(f"AI failed to process '{original_filename}'. Error : {error_msg}")
                        append_to_log("INGEST", f"FAILED: {original_filename}", [])
                        break

                    elif status == "pending":
                        print("...", end="\r")

            except requests.exceptions.ConnectionError:
                print("Lost connection to server while waiting. Retrying...")
            time.sleep(5)
    finally:
        print("Cleaning up job on server...")
        
        try:
            del_res = requests.delete(f"{SERVER_URL}/wiki/delete-job/{job_id}", headers=headers)
            if del_res.status_code == 200:
                print(f"{del_res.json().get('message', 'Cleanup successful.')}")
            else:
                print(f"Cleanup failed with status {del_res.status_code}: {del_res.text}")
        except Exception as e:
            print(f" Network error during cleanup: {e}")

# FILE WATCHER
class FileDropHandler(FileSystemEventHandler):
    def __init__(self, api_key):
        self.api_key = api_key

    def on_created(self, event):
        if event.is_directory or os.path.basename(event.src_path).startswith("."):
            return

        time.sleep(1)  # Brief wait to ensure file is fully written
        file_path = event.src_path
        filename  = os.path.basename(file_path)

        # Only process supported file types
        supported = {".pdf", ".docx", ".txt", ".html", ".md"}
        _, ext = os.path.splitext(filename)
        if ext.lower() not in supported:
            print(f"\n  Skipped unsupported file type: {filename}")
            return

        print(f"\nDetected new file: {filename}")

        try:
            # Read all three context files to send to the Cloud Engine
            with open(SCHEMA_PATH, "r", encoding="utf-8") as sf:
                schema_text = sf.read()
            with open(INDEX_PATH, "r", encoding="utf-8") as idxf:
                index_text = idxf.read()

            log_tail = get_log_tail(LOG_TAIL_LINES)

            with open(file_path, "rb") as f:
                files = {"document": f}
                data  = {
                    "schemaText": schema_text,
                    "indexText":  index_text,
                    "logTail":    log_tail,
                }
                
                headers = {"Authorization": f"Bearer {self.api_key}"}

                print("  Uploading document and vault context to Cloud Engine...")
                response = requests.post(
                    f"{SERVER_URL}/wiki/ingest",
                    files=files,
                    data=data,
                    headers=headers
                )

                if response.status_code == 202:
                    job_id = response.json().get("jobId")
                    print(f"  Server accepted. Job ID: {job_id}")
                    if job_id:
                        poll_for_result(job_id, self.api_key, filename)
                else:
                    err_msg = response.json().get("message", response.text)
                    print(f"  Server Error: {err_msg}")

        except Exception as e:
            print(f"  Upload failed: {e}")
            append_to_log("INGEST", f"UPLOAD_FAILED: {filename}", [])


def startWatching(api_key):
    bootstrap_wiki()

    print("\n===============================")
    print("  Vault is ready.")
    print("===============================")

    while True:
        print("\nVAULT MENU")
        print("1) Watch for new files")
        print("2) Query the wiki")
        print("3) Back to main menu")

        choice = input("> ").strip()

        if choice == "1":
            event_handler = FileDropHandler(api_key)
            observer      = Observer()
            observer.schedule(event_handler, INPUT_FOLDER, recursive=True)
            observer.start()

            print(f"\n  Monitoring '{INPUT_FOLDER}' for new files.")
            print(f"  Supported types: PDF, DOCX, TXT, HTML, MD")
            print("  Press CTRL+C to stop watching and return to vault menu.\n")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
                observer.join()
                print("\n\nWatcher paused.")

        elif choice == "2":
            action_query(api_key)

        elif choice == "3":
            return


# MENU ACTIONS 
def action_login():
    print("\n--- LOGIN ---")
    local_key = get_local_key()
    if local_key:
        print("Found saved session. Verifying...")
        if verify_token(local_key):
            return local_key
        else:
            print("Saved session expired. Please log in manually.")

    email = ask_user("Email")
    if not email: return None

    password = ask_user("Password", is_password=True)
    if not password: return None

    try:
        response = requests.post(
            f"{SERVER_URL}/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            api_key = response.json().get("apiKey")
            save_local_key(api_key)
            print("Login successful! Credentials saved.")
            return api_key
        else:
            print(f"Login failed: {response.json().get('message')}")
            return None
    except requests.exceptions.ConnectionError:
        print("Could not connect to the server.")
        return None

def action_register():
    print("\n--- REGISTER ---")
    username = ask_user("Username")
    if not username: return None

    email = ask_user("Email")
    if not email: return None

    password = ask_user("Password", is_password=True)
    if not password: return None

    if ALLOW_DEFAULT_LLM:
        print("\n(Optional) Bring your own Gemini API key for unlimited use.")
        custom_key = ask_user("Custom LLM Key (or type 'skip' to use default)", is_password=True)
    else:
        print("\nRequired: You must provide your own Gemini API key to use this tool.")
        custom_key = ask_user("Custom LLM Key", is_password=True)

    if not custom_key: return None

    payload = {"username": username, "email": email, "password": password}

    if ALLOW_DEFAULT_LLM:
        if custom_key.lower() != "skip":
            payload["customLLMKey"] = custom_key
    else:
        payload["customLLMKey"] = custom_key

    try:
        response = requests.post(f"{SERVER_URL}/auth/register", json=payload)
        if response.status_code == 201:
            api_key = response.json().get("apiKey")
            save_local_key(api_key)
            print("Account created successfully!")
            return api_key
        else:
            print(f"Registration failed: {response.json().get('message')}")
            return None
    except requests.exceptions.ConnectionError:
        print("Could not connect to the server.")
        return None

def action_change_key():
    print("\n--- CHANGE CUSTOM LLM KEY ---")
    print("Please verify your account first.")

    email = ask_user("Email")
    if not email: return None

    password = ask_user("Password", is_password=True)
    if not password: return None

    try:
        login_res = requests.post(
            f"{SERVER_URL}/auth/login",
            json={"email": email, "password": password}
        )
        if login_res.status_code != 200:
            print("Invalid email or password.")
            return None

        api_key = login_res.json().get("apiKey")
        save_local_key(api_key)

        new_custom_key = ask_user("Enter your NEW Gemini API Key", is_password=True)
        if not new_custom_key: return None

        headers    = {"Authorization": f"Bearer {api_key}"}
        update_res = requests.put(
            f"{SERVER_URL}/user/key",
            json={"customKey": new_custom_key},
            headers=headers
        )

        if update_res.status_code == 200:
            print(update_res.json().get("message"))
            return api_key
        else:
            print(f"Failed to update key: {update_res.json().get('message')}")
            return None

    except requests.exceptions.ConnectionError:
        print("Cannot reach the server.")
        return None


# MAIN MENU
if __name__ == "__main__":
    print("\n===============================")
    print("    Welcome to LLM-Wiki CLI    ")
    print("  Based on Andrej Karpathy's   ")
    print("  LLM Knowledge Base pattern   ")
    print("===============================")

    while True:
        print("\nMAIN MENU")
        print("1) Login & Start")
        print("2) Register & Start")
        print("3) Change Custom LLM Key")
        print("4) Exit")

        choice = input("> ").strip()
        API_KEY = None

        if choice == "1":
            API_KEY = action_login()
        elif choice == "2":
            API_KEY = action_register()
        elif choice == "3":
            action_change_key()
        elif choice == "4":
            print("Goodbye!")
            exit(0)
        else:
            print("Invalid choice. Please press 1, 2, 3, or 4.")

        if API_KEY and choice in ["1", "2"]:
            startWatching(API_KEY)