import time
import mimetypes
from google import genai
import os
import re
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from google.genai.types import HarmCategory, HarmBlockThreshold
from google import genai as google_genai
from markitdown import MarkItDown


class DocumentClassification(BaseModel):
    doc_type: str = Field(
        description=(
            "The document type. Must be one of: "
            "Research | Article | Meeting | Journal | Tutorial | Legal | Book  | Personal | Educational | Other"
        )
    )
    suggested_sections: list[str] = Field(
        default=[
            "Overview",
            "Core Concepts",
            "Key Details",
            "Implications",
            "Open Questions"
        ],
        description=(
            "Ordered list of section headings appropriate for this document type. "
            "Examples for Research: ['Executive Summary', 'Core Concepts and Entities', "
            "'Deep Dive', 'Notable Specifics', 'Tensions and Limitations', "
            "'Implications and Applications', 'Open Questions and Follow-Up']. "
            "Adapt freely for other types. Do NOT include 'References and Related' — "
            "that section is always added automatically."
        )
    )


class ContentSection(BaseModel):
    heading: str = Field(
        description="Section heading text only — no numbering, no markdown formatting"
    )
    body: str = Field(
        description=(
            "Full markdown content for this section. "
            "Use [[wikilinks]] for all concepts, entities, people, tools, and frameworks. "
            "Use callout blocks: > [!NOTE], > [!IMPORTANT], > [!TIP], > [!QUOTE], > [!WARNING]. "
            "Use ### subheadings freely for long content. "
            "Use tables for comparative data. Use code blocks with language tags for code. "
            "Do NOT include the section heading here — it is already in the heading field above. "
            "Do NOT include YAML frontmatter here."
        )
    )


class WikiNote(BaseModel):
    title: str = Field(
        description="Descriptive title of the content — not the filename, but what the document is about"
    )
    aliases: list[str] = Field(
        description="Alternative names or abbreviations someone might search for. 2-4 entries."
    )
    tags: list[str] = Field(
        description=(
            "Hierarchical tags in topic/subtopic format. "
            "Examples: nlp/spelling-correction, ml/transformers, education/lecture. "
            "3-6 tags."
        )
    )
    author: str = Field(
        description="Author(s) of the source document. Empty string if not found."
    )
    source: str = Field(
        description="URL, DOI, filename, or publication name of the source"
    )
    date_published: str = Field(
        description="Publication date extracted from document in YYYY-MM-DD format. Empty string if not found."
    )
    sections: list[ContentSection] = Field(
        description=(
            "All content sections for this note in order. "
            "Use the suggested sections provided in the prompt. "
            "Only include sections that have real content — never invent filler sections."
        )
    )
    source_citations: list[str] = Field(
        description=(
            "References cited in the source document as plain text strings. "
            "Format each as: Author(s), Year, Title, Journal or Publisher. "
            "Only citations that actually appear in the source — do not add external sources. "
            "Empty list if document has no citations (journal entries, meeting notes, etc.)."
        )
    )
    see_also: list[str] = Field(
        description=(
            "Related concepts, frameworks, tools, and entities worth having their own vault page. "
            "Format each as a [[wikilink]]. "
            "Do NOT list citations here — only concepts and named entities."
        )
    )


class WikiMetadata(BaseModel):
    index_entry: str = Field(
        description=(
            "A single pipe-delimited markdown table row in EXACTLY this format: "
            "| [[NoteFilename]] | One sentence summary of the note | Category | YYYY-MM-DD | "
            "The category MUST be one of the exact strings from the SCHEMA Index Categories list. "
            "Do not invent new categories. Do not change the column order. "
            "Example: | [[Real_Word_Spelling_Errors]] | Surveys detection methods for real-word spelling errors in Urdu NLP | NLP & Linguistics | 2026-05-16 |"
        )
    )
    index_category: str = Field(
        description=(
            "The exact category string this note belongs to. "
            "Must be one of: 'NLP & Linguistics', 'Machine Learning', "
            "'Systems & Architecture', 'Personal Knowledge Management', "
            "'Meetings & Notes', 'Journal & Reflections', 'General'. "
            "Copy the string exactly — no variations, no new categories."
        )
    )
    cross_links: list[str] = Field(
        description=(
            "List of exact filenames without .md extension of existing pages "
            "from the CURRENT INDEX that this new note meaningfully relates to. "
            "To find valid filenames look for [[Filename]] patterns in the index. "
            "Extract only the text between [[ and ]]. "
            "Only include pages where the conceptual overlap is substantial — "
            "shared methodology, shared topic, shared domain, or directly cited work. "
            "Max 5. Empty list only if the index is empty or no genuine overlap exists."
        )
    )


def extract_preview(file_path: str) -> str:
    md = MarkItDown()
    try:
        result = md.convert(file_path)
        return result.text_content[:3000]
    except Exception as e:
        print(f"  Preview extraction failed: {e}")
        return ""


GEMINI_MIME_MAP = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg"
}

def get_mime_type(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in GEMINI_MIME_MAP:
        return GEMINI_MIME_MAP[ext]
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"


def upload_to_gemini(file_path: str, user_key: str, original_filename: str):
    client = genai.Client(api_key=user_key)
    detected_mime = get_mime_type(original_filename)
    print(f"  Uploading to Gemini File API: {os.path.basename(file_path)} (Detected as {detected_mime})...")
    uploaded = client.files.upload(
        file=file_path,
        config={"mime_type": detected_mime}
    )
    while uploaded.state.name == "PROCESSING":
        print(f"  File processing... waiting")
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)
    if uploaded.state.name == "FAILED":
        raise Exception(f"Gemini file upload failed: {uploaded.name}")
    print(f"  Upload complete. Name: {uploaded.name}")
    return uploaded


def delete_gemini_file(file_name: str, user_key: str):
    try:
        client = google_genai.Client(api_key=user_key)
        client.files.delete(name=file_name)
        print(f"  Gemini file deleted: {file_name}")
    except Exception as e:
        print(f"  Could not delete Gemini file {file_name}: {e}")


def clean_broken_tables(body: str) -> str:
    lines  = body.split('\n')
    result = []
    i      = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('|') and line.strip().endswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            col_counts = []
            for tl in table_lines:
                stripped = tl.strip().strip('|')
                if re.match(r'^[\s\-\:\|]+$', stripped):
                    continue
                cols = len(stripped.split('|'))
                col_counts.append(cols)
            if col_counts and len(set(col_counts)) == 1:
                result.extend(table_lines)
            else:
                print(f"  Malformed table detected, converting to bullets.")
                for tl in table_lines:
                    stripped = tl.strip().strip('|')
                    if re.match(r'^[\s\-\:\|]+$', stripped):
                        continue
                    cells = [c.strip() for c in stripped.split('|') if c.strip()]
                    if cells:
                        result.append(f"- {' — '.join(cells)}")
        else:
            result.append(line)
            i += 1
    return '\n'.join(result)


def clean_section_body(body: str) -> str:
    body = re.sub(r'(?m)^#{2,6}\s+', '', body)
    body = re.sub(r'(?m)^\*\s+', '- ', body)
    body = clean_broken_tables(body)
    return body


def assemble_markdown(note: WikiNote, doc_type: str, today: str) -> str:
    def quote(s: str) -> str:
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

    lines = []

    lines.append("---")
    lines.append(f"title: {quote(note.title)}")
    lines.append("aliases:")
    for alias in note.aliases:
        lines.append(f"  - {quote(alias)}")
    lines.append("tags:")
    for tag in note.tags:
        lines.append(f"  - {tag}")
    lines.append(f"doc_type: {doc_type}")
    lines.append(f"author: {quote(note.author)}")
    lines.append(f"source: {quote(note.source)}")
    lines.append(f"date_published: {quote(note.date_published)}")
    lines.append(f'date_noted: "{today}"')
    lines.append("status: fresh")
    lines.append("---")
    lines.append("")

    section_num = 1
    for section in note.sections:
        body = clean_section_body(section.body.strip())
        body = re.sub(r'\n{3,}', '\n\n', body)
        if not body:
            print(f"  Skipped empty section: {section.heading}")
            continue
        lines.append(f"## {section_num}. {section.heading}")
        lines.append("")
        lines.append(body)
        lines.append("")
        section_num += 1

    lines.append(f"## {section_num}. References and Related")
    lines.append("")

    if note.source_citations:
        lines.append("### Source Citations")
        lines.append("")
        for i, citation in enumerate(note.source_citations, 1):
            lines.append(f"{i}. {citation}")
        lines.append("")

    if note.see_also:
        lines.append("### See Also")
        lines.append("")
        for item in note.see_also:
            item = item.strip()
            if not item.startswith("[["):
                item = f"[[{item}]]"
            lines.append(f"- {item}")
        lines.append("")

    lines.append("### Vault Pages")
    lines.append("")
    lines.append("(backfilled automatically on ingest)")
    lines.append("")

    return "\n".join(lines)


def build_classification_prompt() -> str:
    return (
        "You are a document classifier. Read the source document and determine "
        "its type and the best section structure for a knowledge base note.\n\n"

        "Document types: Research | Article | Meeting | Journal | Tutorial | "
        "Legal | Reference | Book | Slides | Other\n\n"

        "You MUST return both fields:\n"
        "1. doc_type — the document type from the list above\n"
        "2. suggested_sections — a complete ordered list of 5-8 section headings "
        "appropriate for this specific document. This field is required and must "
        "never be empty.\n\n"

        "Be specific with sections — a Machine Learning lecture should have sections "
        "like 'Course Overview', 'Key Algorithms', 'Mathematical Foundations', "
        "not generic research paper sections.\n\n"

        "SOURCE DOCUMENT (first 3000 chars for classification):\n{raw_text_preview}"
    )


def build_note_generation_prompt() -> str:
    return (
        "You are a Wiki Engineer building a permanent, highly interconnected "
        "Obsidian knowledge base.\n\n"

        "Read the SCHEMA below — it defines the wiki's architecture and rules.\n\n"

        "═══════════════════════════════════════\n"
        "SCHEMA:\n"
        "═══════════════════════════════════════\n"
        "{schema}\n\n"

        "═══════════════════════════════════════\n"
        "YOUR TASK\n"
        "═══════════════════════════════════════\n"
        "Extract the content of the source document into a structured WikiNote object.\n\n"

        "This is NOT a summary. Extract every distinct concept, finding, argument, "
        "and piece of data the source contains. Cover each thing once, thoroughly. "
        "Do not repeat information across sections. Do not elaborate beyond what "
        "the source directly supports.\n\n"

        "You will populate these sections in order: {suggested_sections}\n\n"

        "For each section body:\n"
        "  - Write full markdown content — do NOT include the heading (it is separate)\n"
        "  - Use [[wikilinks]] for ALL concepts, entities, people, tools, frameworks\n"
        "  - Use callout blocks: > [!NOTE], > [!IMPORTANT], > [!TIP], > [!QUOTE], > [!WARNING]\n"
        "  - Use ### subheadings freely for long content\n"
        "  - Use tables for comparative or multi-attribute data\n"
        "  - Use code blocks with language tags for any code or commands\n"
        "  - Bold (**term**) key terms on first definition only\n\n"

        "SOURCE FIDELITY RULES:\n"
        "  The source document (especially slides) may contain visual formatting cues —\n"
        "  bullet glyphs, bold headers, asterisks used as list markers, or markdown-like\n"
        "  symbols (###, **, *) embedded in the extracted text. These are NOT content,\n"
        "  they are presentation artifacts from the original slide layout.\n"
        "  Do NOT copy these symbols literally into your output.\n"
        "  Rewrite the underlying information into clean prose or proper markdown\n"
        "  bullet lists (using '- ' for list items, not '*').\n"
        "  Only use ** for bolding a term you are deliberately emphasizing on first\n"
        "  definition — never because the source happened to render it that way.\n"
        "  If a slide title looks like a heading in the source, treat it as a cue for\n"
        "  what the section is about, not something to reproduce verbatim with hashes.\n"
        "  Slide decks often repeat the same title across multiple continuation slides\n"
        "  (e.g. 'Technical Implementation', 'Technical Implementation (cont.)',\n"
        "  'Technical Implementation 2/5'). Do NOT create a separate section for each\n"
        "  continuation slide. Merge all content from continuation slides into one\n"
        "  section under a single heading. A section with no substantive content\n"
        "  should not exist — if a slide has no text beyond its title, skip it.\n"
        "  Only use markdown tables for data that is genuinely tabular — where rows and\n"
        "  columns are meaningful and every cell has a value. Do NOT attempt to force\n"
        "  side-by-side slide layouts, comparison bullet lists, or multi-column slide\n"
        "  content into tables. If the columns would be uneven or cells empty, use a\n"
        "  bullet list or prose instead.\n\n"

        "CHARACTER BUDGET — use this to calibrate your output length:\n"
        "  Total note target:    {total_char_budget} characters\n"
        "  A character is one letter, space, or punctuation mark — count as you write.\n"
        "  When a section body reaches its target, wrap up that section and move to the next.\n"
        "  Cover everything once. Stop when every section is complete.\n\n"

        "For source_citations: only citations from the document's own bibliography. "
        "Plain text, no wikilinks, no filenames.\n\n"

        "For see_also: related concepts and entities as [[wikilinks]], not citations.\n\n"

        "The source document is attached — read it directly."
    )


def build_meta_system_prompt() -> str:
    return (
        "You are a Wiki Metadata Specialist. You will be given a completed Obsidian wiki note "
        "and must produce three pieces of metadata for it: an index entry, a category, "
        "and a list of cross-links to existing pages.\n\n"

        "═══════════════════════════════════════\n"
        "CURRENT INDEX (find cross-link targets here):\n"
        "═══════════════════════════════════════\n"
        "{index}\n\n"

        "═══════════════════════════════════════\n"
        "RECENT LOG (understand what has been ingested recently):\n"
        "═══════════════════════════════════════\n"
        "{log_tail}\n\n"

        "═══════════════════════════════════════\n"
        "VALID CATEGORIES — must match SCHEMA exactly, copy character for character:\n"
        "═══════════════════════════════════════\n"
        "- NLP & Linguistics\n"
        "- Machine Learning\n"
        "- Systems & Architecture\n"
        "- Personal Knowledge Management\n"
        "- Meetings & Notes\n"
        "- Journal & Reflections\n"
        "- General\n\n"

        "If the note does not clearly fit any specific category use General. "
        "Never invent a new category — only use the ones listed above.\n\n"

        "═══════════════════════════════════════\n"
        "RULES:\n"
        "═══════════════════════════════════════\n"
        "INDEX ENTRY:\n"
        "  - Format exactly: | [[NoteFilename]] | One sentence summary | Category | YYYY-MM-DD |\n"
        "  - Use the wiki page filename provided in the user message for [[NoteFilename]]\n"
        "  - Date is today: {today}\n"
        "  - Category must be one of the valid categories above, copied exactly\n"
        "  - Summary must be one sentence — no more, no less\n\n"

        "CROSS LINKS:\n"
        "  - Only use filenames that appear as [[Filename]] in the CURRENT INDEX\n"
        "  - Extract the exact text between [[ and ]] — no .md extension\n"
        "  - Only link pages with substantial conceptual overlap: shared methodology, "
        "    shared topic, shared domain, or directly cited work\n"
        "  - Maximum 5. Empty list only if the index is genuinely empty\n"
    )


def generate_integration_plan(
    file_path: str,
    user_key: str,
    original_filename: str,
    schema_text: str,
    index_text: str,
    log_tail: str = "",
    progress_callback=None
):
    def emit_progress(stage: str, stage_message: str):
        if progress_callback is None:
            return
        try:
            progress_callback(stage, stage_message)
        except Exception as callback_error:
            print(f"  Progress callback failed: {callback_error}")

    # Using original temp file path directly
    text_preview = extract_preview(file_path)

    emit_progress("uploading", f"Uploading {original_filename} to Server")
    gemini_file = upload_to_gemini(file_path, user_key, original_filename)

    file_size_bytes   = os.path.getsize(file_path)
    estimated_input   = file_size_bytes // 3
    total_char_budget = max(8000, min(60000, int(estimated_input * 0.45)))

    print(f"  Total char budget:       {total_char_budget:,}")

    note_filename = os.path.splitext(original_filename)[0]
    note_filename = re.sub(r'\s*-\s*Copy$', '', note_filename, flags=re.IGNORECASE)
    note_filename = note_filename.replace(" ", "_")

    today = datetime.now().strftime("%Y-%m-%d")

    safety = {
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH:        HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT:         HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:  HarmBlockThreshold.BLOCK_NONE,
    }

    classify_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=user_key,
        temperature=0.1,
        max_output_tokens=1024,
        safety_settings=safety
    )
    structured_classify_llm = classify_llm.with_structured_output(DocumentClassification)
    classify_prompt = ChatPromptTemplate.from_messages([
        ("user", build_classification_prompt()),
    ])
    classify_chain = classify_prompt | structured_classify_llm

    print(f"  Brain [1/3]: Classifying '{original_filename}'...")
    emit_progress("classifying", f"Classifying {original_filename}")
    classification = classify_chain.invoke({
        "raw_text_preview": text_preview
    })

    doc_type           = classification.doc_type
    suggested_sections = ", ".join(classification.suggested_sections)
    num_sections       = len(classification.suggested_sections)

    per_section_budget = max(500, total_char_budget // max(1, num_sections))

    print(f"  Detected type:     {doc_type}")
    print(f"  Sections:          {suggested_sections}")
    print(f"  Per-section budget: {per_section_budget:,} chars")

    emit_progress("generating_note", f"Generating structured note for {original_filename}")
    client = google_genai.Client(api_key=user_key)

    system_prompt = build_note_generation_prompt().format(
        schema=schema_text,
        suggested_sections=suggested_sections,
        total_char_budget=f"{total_char_budget:,}",
    )

    user_message = (
        f"Original filename: {original_filename}\n"
        f"Wiki page filename: {note_filename}\n"
        f"Per-section character target: {per_section_budget:,} characters per section body.\n"
        f"Major sections may use up to 1.5x this. Minor sections 0.5x this."
    )

    print(f"  Brain [2/3]: Generating structured note for '{original_filename}'...")

    wiki_note  = None
    last_error = None

    for attempt in range(3):
        try:
            from google.genai import types as genai_types

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    genai_types.Content(
                        role="user",
                        parts=[
                            genai_types.Part.from_uri(
                                file_uri=gemini_file.uri,
                                mime_type=gemini_file.mime_type
                            ),
                            genai_types.Part.from_text(text=user_message),
                        ]
                    )
                ],
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=WikiNote,
                    max_output_tokens=65536,
                    temperature=0.2,
                    safety_settings=[
                        genai_types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_NONE"
                        ),
                        genai_types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="BLOCK_NONE"
                        ),
                        genai_types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT",
                            threshold="BLOCK_NONE"
                        ),
                        genai_types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            threshold="BLOCK_NONE"
                        ),
                    ]
                )
            )

            import json
            raw_json  = response.text
            wiki_note = WikiNote.model_validate(json.loads(raw_json))
            break

        except Exception as e:
            last_error = e
            print(f"  Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                print(f"  Retrying...")

    delete_gemini_file(gemini_file.name, user_key)

    if wiki_note is None:
        raise Exception(f"Note generation failed after 3 attempts. Last error: {last_error}")

    print(f"  Sections generated: {[s.heading for s in wiki_note.sections]}")
    print(f"  Citations found:    {len(wiki_note.source_citations)}")
    print(f"  See Also entries:   {len(wiki_note.see_also)}")

    note_content = assemble_markdown(wiki_note, doc_type, today)
    actual_chars = len(note_content)

    print(f"  Note chars:        {actual_chars:,}")
    print(f"  Ratio:             {actual_chars / max(1, estimated_input):.2f}x estimated input")

    if actual_chars > estimated_input * 2:
        print(f"  WARNING: Note may be verbose relative to input size.")

    emit_progress("generating_metadata", f"Generating metadata for {original_filename}")
    meta_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=user_key,
        temperature=0.1,
        max_output_tokens=4096,
        safety_settings=safety
    )
    structured_meta_llm = meta_llm.with_structured_output(WikiMetadata)

    meta_prompt = ChatPromptTemplate.from_messages([
        ("system", build_meta_system_prompt()),
        ("user", (
            "Wiki page filename: {note_filename}\n\n"
            "COMPLETED NOTE:\n{note_content}"
        ))
    ])

    meta_chain = meta_prompt | structured_meta_llm
    print(f"  Brain [3/3]: Generating metadata for '{original_filename}'...")

    meta_result = meta_chain.invoke({
        "index":         index_text,
        "log_tail":      log_tail if log_tail else "No log entries yet.",
        "today":         today,
        "note_filename": note_filename,
        "note_content":  note_content
    })

    print(f"  Cross-links identified: {meta_result.cross_links}")
    print(f"  Index category:         {meta_result.index_category}")
    emit_progress("finalizing", f"Finalizing integration plan for {original_filename}")

    return {
        "note_filename":  note_filename,
        "note_content":   note_content,
        "index_entry":    meta_result.index_entry,
        "cross_links":    meta_result.cross_links,
        "index_category": meta_result.index_category
    }