# Reference Metadata Enrichment — Plan and Progress

Purpose
- Improve reference uploads by auto-prefilling metadata from PDFs (title, authors, year, DOI, abstract, etc.).
- Keep it generic (not OED-specific) and safe: only extract non-copyright metadata and short excerpts.
- Primary focus: make references analysis-ready so experiments can meaningfully compare terms across domains and time.

Non-goals (for now)
- Perfect bibliographic parsing (we’ll get close, but not exhaustive).
- Heavy-weight layout analysis (no full OCR/page geometry in v1).

Phased approach

Phase 0 — Hook & Flags (small)
- Add a metadata enrichment hook to the reference upload flow, after saving the file.
- Feature flags via env/config:
  - PREFILL_METADATA=true|false (default true)
  - PREFILL_USE_LANGEXTRACT=true|false (default false)
  - PREFILL_USE_ZOTERO=true|false (default false)
- If the user fills a field manually, don’t overwrite; only fill gaps or offer “Review & apply”.

Phase 1 — Local Heuristics (pypdf) [Low risk]
- Extract PDF document info: title, author(s), creation date, subject (pypdf metadata).
- First pages text scan (1–3 pages) to heuristically detect:
  - Title: first non-empty line(s); fallback to metadata title.
  - Authors: lines with comma-separated names; simple regex (Last, First | First Last; allow diacritics).
  - Year: regex for 19xx/20xx; prefer the one near title/authors.
  - DOI: robust regex (10.\d{4,9}/[-._;()/:A-Z0-9]+), also “doi.org/…”. Clean trailing punctuation.
  - ISBN: regex for 10/13; for books.
  - Abstract: detect heading “Abstract” (case-insensitive), capture paragraph(s) until blank or next heading; truncate to ~1000 chars.
  - Journal/Publisher hints: look for common patterns (“Proceedings of…”, “Journal of…”, publisher lines), low-confidence tag.
- Build/merge source_metadata safely:
  - Only set fields if empty or flagged as low-confidence.
  - Preserve user-entered values.

Phase 2 — LangExtract assist (optional) [Medium]
- Use existing LangExtract integration to extract a structured block:
  - title, authors[], year, journal/publisher, doi, abstract (short), keywords[], domain, key terms.
- Gate on API key (GOOGLE_GEMINI_API_KEY or LANGEXTRACT_API_KEY) and flag PREFILL_USE_LANGEXTRACT.
- Store under source_metadata.lx_* keys and/or apply fills with confidence scores; never persist long copyrighted text.

Phase 3 — Zotero/Crossref enrichment (optional) [Medium]
- If DOI present (from Phase 1/2):
  - Fetch metadata via Crossref API as a fast public fallback.
  - If PREFILL_USE_ZOTERO and ZOTERO_API_KEY/ZOTERO_USER_ID set:
    - Option A: Use Crossref result to build a Zotero item; POST to Zotero collection (optional) and store itemKey in source_metadata.zotero_item_key.
    - Option B (Later): Integrate Zotero Translation Server for richer identifier-based lookup.
- Add UI buttons on Edit Reference: “Fetch from DOI”, “Sync to Zotero”, “Pull from Zotero”.

Phase 4 — Analysis wiring (priority) [Medium]
- Ensure extracted full text is available for experiments:
  - Extract PDF text on upload and store in Document.content (or as segments) for RAG/analysis.
  - Segment text (pages/sections) and index embeddings if enabled.
- Provide experiment utilities:
  - Term frequency/time slices (by publication year).
  - Domain clustering via keywords/entity extraction.
  - Cross-reference with OED senses (mapping selected senses to occurrences).

Phase 5 — Quality & UX (nice-to-have)
- Confidence badges and inline edits for auto-filled fields.
- Background enrichment job with progress.
- Per-source analytics (coverage of DOI/abstract match rate).

Data contract (initial)
- Input: PDF file path.
- Output: source_metadata delta (title?, authors[]?, publication_date?, journal?, doi?, isbn?, abstract?, url?, citation?), plus optional lx_* fields and zotero_* fields.
- Error modes: missing/invalid PDF; non-standard text; no DOI/abstract found.

Edge cases
- Scanned PDFs (no text): skip heuristics, optionally suggest OCR.
- Very long abstracts: truncate to 1000 chars.
- Multiple DOIs: pick first near title or highest-confidence.
- Mismatched years: prefer DOI metadata once verified.

Progress tracker
- [ ] Phase 0: Flags and upload hook (no-op wiring)
- [ ] Phase 1: pypdf heuristics extraction
  - [ ] Doc info (title/author/date)
  - [ ] First pages scan and regex detectors (DOI/ISBN/year/abstract)
  - [ ] Safe merge into source_metadata
- [ ] Phase 2: LangExtract assist (optional)
  - [ ] Prompt + parser + confidence scores
  - [ ] Safe merge, cap excerpts
- [ ] Phase 3: Zotero/Crossref (optional)
  - [ ] Crossref fetch by DOI
  - [ ] Zotero item create/sync (collection optional)
  - [ ] UI buttons on Edit Reference
- [ ] Phase 4: Analysis wiring
  - [ ] Ensure Document.content populated from PDFs
  - [ ] Segment/index for experiments
  - [ ] Time-slice and domain comparison utilities
- [ ] Phase 5: UX polish

Config & env
- PREFILL_METADATA=true|false
- PREFILL_USE_LANGEXTRACT=true|false
- PREFILL_USE_ZOTERO=true|false
- ZOTERO_API_KEY, ZOTERO_USER_ID, ZOTERO_COLLECTION_KEY (optional)

Risk & compliance
- Do not store long copyrighted text from PDFs as metadata fields; abstracts truncated.
- Respect OED terms where applicable; generic PDFs OK within user-controlled uploads.
- Network calls are optional and gated (Crossref/Zotero).

Next steps (immediate)
- Implement Phase 0 hook and basic Phase 1 extractor as a service class (not wired yet to UI).
- Add a “Prefill metadata” toggle on the upload form (default on when enabled).
- Add a one-click “Fetch from DOI” on Edit Reference (Phase 3 later).
