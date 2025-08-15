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

Phase 1b — Research Design metadata (experimental) [Low risk]
- Goal: Capture essential research design facets from academic PDFs to enable design-aware experiments.
- Reference basis: Attached research design paper (Choi) emphasizes explicit declaration of design elements to improve rigor and comparability. We mirror that structure in lightweight metadata.
- Extract (heuristics first, optional LLM assist later):
  - Design type: experimental | quasi-experimental | observational | survey | mixed-methods
  - Hypotheses: list of short text strings (H1, H2, …)
  - Variables:
    - Independent variables (IV) with factors/levels
    - Dependent variables (DV) with measurement notes
    - Control/covariates
  - Sampling & assignment: population, sampling strategy, randomization/blocking/stratification
  - Groups/conditions: names, N per group (if reported)
  - Manipulation checks / validity notes
  - Timeline: pre/post measures, sessions, follow-up windows
  - Threats/limitations: brief bullet points if present
- Storage shape (within Document.source_metadata.design):
  {
    "type": "experimental",
    "hypotheses": ["H1: …", "H2: …"],
    "variables": {
      "independent": [{"name": "Agent definition", "levels": ["OED", "AI textbook"]}],
      "dependent": [{"name": "terminology alignment score", "measure": "cosine similarity"}],
      "control": ["domain", "publication year"]
    },
    "sampling": {"population": "articles about agency", "strategy": "purposive"},
    "assignment": {"randomization": false, "blocking": ["domain"]},
    "groups": [{"name": "OED senses", "n": 12}, {"name": "AI definitions", "n": 10}],
    "timeline": {"pre": false, "post": true, "follow_up_days": null},
    "validity": {"manipulation_checks": [], "notes": []}
  }
- Wiring to experiments: experiments.configuration.design mirrors the above to specify the intended design for analysis; when present, analysis services read from experiment.configuration.design, and reference-level design enrichments serve as inputs/evidence.

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
  - Design-aware analysis runners:
    - Factor/level comparisons aligned to IV definitions in configuration.design.variables.independent
    - Group summaries and between-group tests based on configuration.design.groups
    - Pre/post deltas if configuration.design.timeline indicates repeated measures

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
  - [ ] Design-aware utilities (factors/groups/pre-post)
- [ ] Phase 5: UX polish

Config & env
- PREFILL_METADATA=true|false
- PREFILL_USE_LANGEXTRACT=true|false
- PREFILL_USE_ZOTERO=true|false
- ZOTERO_API_KEY, ZOTERO_USER_ID, ZOTERO_COLLECTION_KEY (optional)

Data contracts
- Input: file path (PDF/DOCX) and optional user-provided hints (design type, key variables)
- Output: source_metadata delta with top-level bibliographic fields and nested design object (see Phase 1b)
- Experiment config: experiments.configuration can include a "design" object; if absent, services may infer a minimal design from selected references.

Risk & compliance
- Do not store long copyrighted text from PDFs as metadata fields; abstracts truncated.
- Respect OED terms where applicable; generic PDFs OK within user-controlled uploads.
- Network calls are optional and gated (Crossref/Zotero).

Next steps (immediate)
- Implement Phase 0 hook and basic Phase 1 extractor as a service class (not wired yet to UI).
- Add a “Prefill metadata” toggle on the upload form (default on when enabled).
- Add a one-click “Fetch from DOI” on Edit Reference (Phase 3 later).

Implementation notes (2025-08-14)
- The Domain Comparison analysis reads `Experiment.configuration.design` when present:
  - If `design.groups` is provided, results are grouped by these names.
  - Else if an independent variable provides `levels`, results are grouped by those levels.
  - Otherwise it falls back to discipline-based grouping (journal/context inference or explicit assignments).
