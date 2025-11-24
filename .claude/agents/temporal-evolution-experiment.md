# Temporal Evolution Experiment Creation Agent

Specialized agent for creating repeatable temporal evolution experiments in OntExtract, tracking semantic change across historical periods and domains.

## Agent Purpose

This agent automates the creation of temporal evolution experiments by:
1. Analyzing document collections for metadata (dates, domains, definitions)
2. Creating/validating focus terms with reference definitions
3. Designing temporal periods aligned with historical milestones
4. Identifying semantic change events with ontology backing
5. Processing documents in multi-session workflows (handling large PDFs)
6. Generating timeline visualizations for JCDL demonstrations

## Technical Requirements

**Application**: OntExtract
**Port**: http://localhost:8765
**Database**: ontextract_db (PostgreSQL)
**User**: demo/demo123 (or current authenticated user)
**Focus**: Temporal Evolution experiments with ontology-informed semantic events

**Prerequisites**:
- OntExtract server running (port 8765)
- PostgreSQL database accessible
- Source documents available in filesystem
- Semantic Change Ontology loaded (semantic-change-ontology-v2.ttl)

## Experiment Creation Workflow

### Phase 1: Document Collection Analysis

**Objective**: Extract metadata from all source documents to plan temporal coverage and session strategy

**Process**:
1. **Locate Document Collection**
   ```bash
   ls -lh /home/chris/onto/OntExtract/experiments/documents/
   # Expected structure:
   # - *.pdf (overview papers, reference documents)
   # - source_documents/ (primary sources for experiment)
   ```

2. **Read Each Document for Metadata**
   For each PDF in collection, extract:
   - **Publication Date**: Exact year (YYYY) or date range
   - **Authors**: Primary authors and affiliations
   - **Domain**: Law, Philosophy, Computer Science, AI, Linguistics, etc.
   - **Document Type**: Book, article, dictionary entry, conference paper, book chapter, book section
   - **Page Count**: To determine if multi-session processing needed
   - **Chapter/Section Info**: Detect if document is pre-extracted chapter or full book
   - **Key Definitions**: How document defines focus term
   - **Relevant Sections**: Which chapters/pages to extract (if full book >200 pages)

   **Chapter Detection**:
   Determine if PDF is a pre-extracted chapter or full document:
   - **Filename indicators**: "Ch 2", "Chapter 2", "Ch. 2", "Intelligent Agents" (chapter title)
   - **Page count heuristics**:
     - Textbook with <100 pages → likely extracted chapter
     - Conference paper with <20 pages → full paper (not chapter)
     - Legal dictionary with <50 pages → likely excerpt/definition
   - **Content inspection**: Check first page for chapter number, section heading
   - **Source attribution**: Note if part of larger work (e.g., "Chapter 2 from AI: A Modern Approach")

   **Chapter Metadata Fields**:
   - **Is Chapter**: true/false
   - **Chapter Number**: e.g., "2", "VII", "Introduction"
   - **Chapter Title**: e.g., "Intelligent Agents"
   - **Source Book**: Full title of parent work (if chapter)
   - **Source Book Pages**: Total pages of parent work (e.g., "1132 pages")
   - **Chapter Pages**: Pages in this extracted chapter (e.g., "44 pages")

3. **Create Metadata Summary**
   Format as markdown table with chapter awareness:
   ```markdown
   | # | Document | Date | Domain | Type | Pages | Is Chapter? | Chapter Info | Status |
   |---|----------|------|--------|------|-------|-------------|--------------|--------|
   | 1 | OED Entry | Historical | Lexicography | Dictionary | 15 | No | Full entry | Ready |
   | 2 | Black's Law 1910 | 1910 | Law | Legal Dictionary | 30 | No | "Agent" definition | Ready |
   | 3 | Anscombe Intention | 1956 | Philosophy | Book | 285 | No | Full book | Need extraction |
   | 4 | Russell & Norvig - Intelligent Agents | 2022 | AI/CS | Book Chapter | 44 | Yes | Ch 2 from "AI: A Modern Approach" (1132pp) | Ready |
   | 5 | Wooldridge & Jennings | 1995 | AI/CS | Conference Paper | 18 | No | Full paper | Ready |
   ```

4. **Assess Processing Strategy**
   **Chapter-Aware Processing**:
   - **Pre-extracted chapters (<100 pages)**: Upload as-is (already optimized)
     - Example: "Russell & Norvig - Intelligent Agents.pdf" (44 pages, Chapter 2)
     - No further extraction needed
     - Document type: "Book Chapter"
     - Title includes chapter info: "Intelligent Agents (Chapter 2)"

   - **Small full documents (<50 pages)**: Upload full PDF in Session 1
     - Example: OED entries, legal definitions, short articles
     - No extraction needed

   - **Medium full documents (50-200 pages)**: Upload full or extract key chapters in Session 2-3
     - Example: Full books under 200 pages, conference proceedings
     - Assess if full book is relevant or specific chapters needed

   - **Large full books (>200 pages, NOT pre-extracted)**: Extract relevant chapters before upload
     - Example: Anscombe "Intention" (285 pages) → Extract Ch 1-3 (pp. 1-45)
     - Use pdftk or manual extraction to create chapter PDFs
     - Create separate document for each chapter

5. **Validate Temporal Coverage**
   - Identify earliest and latest publication dates
   - Confirm date range (e.g., 1910-2024 = 114 years)
   - Check for temporal gaps (>20 years between documents)
   - Flag missing periods that may need additional sources

**Deliverables**:
- Metadata summary table (markdown)
- Processing session plan (which documents per session)
- Temporal coverage report (date range, gaps, completeness)

### Phase 2: Focus Term Creation/Validation

**Objective**: Ensure focus term exists in database with baseline reference definition

**Process**:
1. **Check Term Existence**
   - Navigate to http://localhost:8765/terms
   - Search for focus term (e.g., "agent", "ontology", "algorithm")
   - Note term ID if exists

2. **Create Term (if not exists)**
   - Navigate to http://localhost:8765/terms/new
   - Enter term text (lowercase, singular form preferred)
   - Description: Brief summary (e.g., "One who acts or has agency")
   - Save and note new term ID

3. **Add Baseline Reference Definition**
   Use Quick Add Reference feature to create lexicographic baseline:

   **Option A: Merriam-Webster**
   - Navigate to http://localhost:8765/experiments/new
   - In "Quick Add Reference" panel, search for term
   - Select sense(s) relevant to experiment
   - Create reference document for each sense

   **Option B: Oxford English Dictionary**
   - Same workflow as MW, using OED API
   - Preferred for historical/etymological analysis
   - Provides dated quotations (critical for temporal experiments)

4. **Verify Reference Documents Created**
   - Navigate to http://localhost:8765/documents
   - Filter by type: "reference"
   - Confirm MW/OED documents exist for focus term

**Deliverables**:
- Focus term created/validated (term ID)
- Reference documents created (MW and/or OED)
- Baseline definitions documented

### Phase 3: Experiment Structure Creation

**Objective**: Create experiment with metadata, description, and initial configuration

**Process**:
1. **Navigate to Experiment Creation**
   http://localhost:8765/experiments/new

2. **Select Experiment Type**
   - Choose: "Temporal Evolution"
   - This triggers:
     - Focus Term dropdown appears at top
     - Description auto-fills (can be customized)
     - Timeline features enabled

3. **Select Focus Term**
   - Choose term from dropdown (created in Phase 2)
   - Experiment name auto-fills: "{term} Temporal Evolution"
   - Can customize name (e.g., "Agent: From Law to AI (1910-2024)")

4. **Customize Description**
   Default auto-fill:
   > "Track semantic change and evolution of terminology across historical periods and different domains."

   Enhanced example:
   > "Tracking semantic evolution of 'agent' from legal/philosophical concept (intentional human actor with moral responsibility) to autonomous AI systems across law, philosophy, and computer science (1910-2024). Demonstrates extensional drift, intensional drift, and disciplinary capture."

5. **Save Experiment**
   - Click "Create Experiment"
   - Note experiment ID from URL: `/experiments/{id}/view`

6. **Navigate to Temporal Term Manager**
   - From experiment view, click "Manage Temporal Terms"
   - URL: `/experiments/{id}/manage_temporal_terms`

**Deliverables**:
- Experiment created (experiment ID)
- Experiment accessible at management page
- Ready for document upload

### Phase 4: Document Processing (Multi-Session)

**Objective**: Upload/reference all source documents, extract text, clean with LLM, and create processing records

**Session Planning** (Chapter-Aware):
Based on Phase 1 metadata analysis, divide documents into sessions. Pre-extracted chapters are treated as ready-to-upload (no extraction needed).

**Session 1: Small Documents & Pre-Extracted Chapters (<100 pages)**
- Dictionary entries (OED, MW references already created)
- Legal definitions (Black's Law excerpts)
- Short articles/conference papers
- **Pre-extracted book chapters** (e.g., "Russell & Norvig - Intelligent Agents.pdf" - 44 pages, Chapter 2)
- **Goal**: Establish temporal baseline, create initial periods, add key technical chapters

**Session 2: Medium Documents (50-200 pages, full works)**
- Full books or substantial chapters that need review
- Philosophy texts (e.g., Anscombe "Intention" - assess if full book or extract needed)
- Historical analyses
- **Goal**: Add humanistic perspective, refine period definitions

**Session 3: Large Full Books (>200 pages, NOT pre-extracted)**
- ONLY if you have full books that need chapter extraction
- Extract relevant chapters first (use pdftk or manual extraction)
- Create separate PDFs for each chapter
- Upload extracted chapters as "book_chapter" type
- **Goal**: Complete temporal coverage with extracted sections

**Session 4: Refinement & Validation**
- Review all uploaded documents
- Verify metadata (dates, authors, domains, chapter info)
- Confirm document-period alignment
- Verify chapter citations include source book info
- **Goal**: Clean up, prepare for period/event creation

**Example Session 1** (for "agent" experiment):
1. OED "agent" entry (15 pages) - dictionary
2. Black's Law 1910 (30 pages) - legal definition
3. **Russell & Norvig - Intelligent Agents (44 pages, Chapter 2) - book chapter** ← Pre-extracted, ready!
4. Wooldridge & Jennings 1995 (18 pages) - conference paper
5. Black's Law 2019 (30 pages) - legal definition
6. Black's Law 2024 (30 pages) - legal definition

Result: 6 documents uploaded in Session 1 (no extraction needed)

**Document Upload Process** (per session):

1. **From Temporal Term Manager** (`/experiments/{id}/manage_temporal_terms`)
   - Scroll to "Documents" section (if present in future UI)
   - OR navigate to `/upload` and select experiment

2. **Upload Process** (Chapter-Aware):
   ```
   For each document:
   a. Click "Upload Document"
   b. Select PDF file
   c. Enter metadata:
      - Title: Full citation title
        * For chapters: "Intelligent Agents (Chapter 2)" or "Ch 2: Intelligent Agents"
        * For full books: "Intention" or "AI: A Modern Approach"
      - Authors: Last, First (comma-separated)
      - Publication Date: YYYY or YYYY-MM-DD
      - Domain: Law, Philosophy, CS, AI, etc.
      - Document Type: book, article, dictionary, report, book_chapter, book_section
        * Use "book_chapter" for pre-extracted chapters
        * Use "book" for full books
      - Chapter/Section Info (if applicable):
        * Chapter Number: "2", "VII", "Introduction"
        * Chapter Title: "Intelligent Agents"
        * Source Book: "Artificial Intelligence: A Modern Approach (4th ed.)"
        * Source Book Total Pages: "1132"
   d. Click "Upload"
   e. Wait for processing (may take 1-2 minutes per document)
   ```

   **Chapter Upload Example**:
   ```
   Title: Intelligent Agents (Chapter 2)
   Authors: Russell, Stuart; Norvig, Peter
   Publication Date: 2022
   Domain: AI/CS
   Document Type: book_chapter
   Chapter Number: 2
   Chapter Title: Intelligent Agents
   Source Book: Artificial Intelligence: A Modern Approach (4th ed.)
   Source Book Total Pages: 1132
   This Document Pages: 44
   ```

3. **Large Document Handling** (ONLY for full books, NOT pre-extracted chapters):

   **IMPORTANT**: If you already have a pre-extracted chapter (e.g., "Russell and Norvig - Intelligent Agents.pdf" is 44 pages),
   skip this section. Upload the chapter as-is using document type "book_chapter".

   For FULL BOOKS >200 pages that need chapter extraction:

   **Option A: PDF Extraction (Manual)**
   ```bash
   # Using pdftk or similar tool (if you have full book and need to extract chapter)
   pdftk "Russell and Norvig - 2022 - AI Modern Approach FULL.pdf" \
     cat 34-78 \
     output "Russell_Norvig_2022_Ch2_Intelligent_Agents.pdf"
   ```

   **Option B: Reference Creation (Preferred for very large books)**
   - Use Quick Add Reference to create conceptual document
   - Include key excerpts in description
   - Link to full source in notes
   - Avoids large file upload

   **Option C: Use Pre-Extracted Chapter** (BEST)
   - If you already have the chapter extracted (like your source_documents folder), use it directly
   - No extraction needed
   - Upload with document type "book_chapter"
   - Include chapter metadata fields

4. **Verify Document Upload** (Chapter-Aware):
   After each upload, verify:
   - Document appears in experiment document list
   - Publication date extracted correctly
   - Metadata complete and accurate
   - **For chapters**: Chapter metadata fields populated (number, title, source book)
   - **For chapters**: Document type set to "book_chapter" (not just "book")
   - **For chapters**: Title includes chapter info (e.g., "Intelligent Agents (Chapter 2)")
   - No upload errors in logs

**Deliverables** (per session):
- Documents uploaded and verified
- Metadata validated (including chapter info for extracted chapters)
- Document-experiment associations confirmed
- Chapter citations properly formatted

**Post-Upload Processing**:

After uploading documents, additional processing is required:

1. **Verify Document Association**

   Documents must be associated in BOTH tables:
   - `experiment_documents` (legacy association table)
   - `experiment_documents_v2` (current processing table)

   ```sql
   -- Check associations
   SELECT d.id, d.title, ed.experiment_id
   FROM documents d
   LEFT JOIN experiment_documents_v2 ed ON d.id = ed.document_id
   WHERE d.id BETWEEN [start_id] AND [end_id];

   -- If missing, insert into experiment_documents_v2:
   INSERT INTO experiment_documents_v2 (
       experiment_id, document_id, processing_status,
       embeddings_applied, segments_created, nlp_analysis_completed,
       added_at, updated_at
   )
   VALUES (experiment_id, document_id, 'pending', false, false, false, NOW(), NOW());
   ```

2. **Extract and Clean Document Text**

   All documents need text extraction and LLM cleanup:

   ```python
   from app.utils.file_handler import FileHandler
   from app.services.text_cleanup_service import TextCleanupService

   file_handler = FileHandler()
   cleanup_service = TextCleanupService()

   # Extract text from PDF
   result = file_handler.extract_text_with_method(file_path, filename)
   text, extraction_method = result

   # Clean with LLM (Claude)
   cleaned_text, metadata = cleanup_service.clean_text(text)

   # Update document
   document.content = cleaned_text
   document.word_count = len(cleaned_text.split())
   document.character_count = len(cleaned_text)
   document.status = 'processed'
   document.processing_metadata['text_cleanup'] = {
       'method': 'llm_claude',
       'model': metadata.get('model'),
       'input_tokens': metadata.get('input_tokens'),
       'output_tokens': metadata.get('output_tokens'),
       'chunks_processed': metadata.get('chunks_processed')
   }
   db.session.commit()
   ```

3. **Create Processing Operation Records**

   Track LLM cleanup in processing operations table:

   ```python
   from app.models.experiment_processing import ExperimentDocumentProcessing

   processing_op = ExperimentDocumentProcessing(
       experiment_document_id=exp_doc.id,
       processing_type='text_cleanup',
       processing_method='llm_claude',
       status='completed',
       configuration_json=json.dumps({
           'model': 'claude-sonnet-4-5-20250929',
           'max_chunk_size': 8000,
           'temperature': 0.0
       }),
       results_summary_json=json.dumps({
           'chunks_processed': metadata.get('chunks_processed'),
           'input_tokens': metadata.get('input_tokens'),
           'output_tokens': metadata.get('output_tokens')
       }),
       started_at=processing_start,
       completed_at=processing_end
   )
   db.session.add(processing_op)
   db.session.commit()
   ```

4. **Verify Processing**

   ```sql
   -- Check all documents have text
   SELECT id, title, word_count, status FROM documents
   WHERE id BETWEEN [start_id] AND [end_id];

   -- Check all have processing operations
   SELECT d.title, edp.processing_type, edp.status
   FROM experiment_document_processing edp
   JOIN experiment_documents_v2 ed ON edp.experiment_document_id = ed.id
   JOIN documents d ON ed.document_id = d.id
   WHERE ed.experiment_id = [experiment_id];
   ```

5. **Create PROV-O Provenance Records**

   Track complete workflow in W3C PROV-O format for research reproducibility:

   ```python
   from app import create_app, db
   from app.models import Document
   import uuid, json
   from datetime import datetime, timezone, timedelta

   app = create_app()
   with app.app_context():
       # Create agents (if not exist)
       # 1. demo user (Person)
       # 2. pypdf (SoftwareAgent)
       # 3. Claude (SoftwareAgent)

       # For each document, create 3 activities + 3 entities:

       # Activity 1: document_upload (by demo user)
       # Entity 1: Document (uploaded PDF)

       # Activity 2: text_extraction (by pypdf)
       # Entity 2: ExtractedText (derived from Document)

       # Activity 3: text_cleanup_llm (by Claude)
       # Entity 3: CleanedText (derived from ExtractedText)

       # Insert into prov_agents, prov_activities, prov_entities tables
       # with proper wasgeneratedby, wasattributedto, wasderivedfrom links
   ```

   See full implementation in Phase 4 provenance script.

   Provenance timeline accessible at: `/provenance/timeline`

**Deliverables** (Phase 4 complete):
- All source documents processed (typically 5-10 documents)
- Pre-extracted chapters uploaded with full metadata
- Full books either: (a) extracted to chapters, or (b) uploaded if small enough
- Temporal coverage complete (earliest to latest dates)
- Chapter source attributions documented
- **All documents have extracted and cleaned text (word counts visible)**
- **Processing operations created for LLM cleanup (visible in document_pipeline)**
- **Documents properly associated in experiment_documents_v2 table**
- **PROV-O provenance records created (agents, activities, entities)**
- **Provenance timeline accessible at /provenance/timeline**
- Ready for period generation

### Phase 5: Temporal Period Design

**Objective**: Create temporal periods aligned with historical milestones and semantic shifts

**Auto-Generation Process**:

1. **Navigate to Period Management**
   From Temporal Term Manager: `/experiments/{id}/manage_temporal_terms`

2. **Auto-Generate Periods from Documents**
   - Locate "Auto-generate from document dates" button
   - Click to generate initial periods
   - System creates periods based on document publication dates
   - Default labels: "Period 1", "Period 2", etc.

3. **Review Generated Periods**
   System creates:
   - Period start/end years from document date ranges
   - Automatic color assignment
   - Document associations (documents within date range)
   - Timeline visualization (horizontal cards)

**Manual Refinement**:

After auto-generation, refine periods to align with semantic/historical milestones:

1. **Rename Periods** (meaningful labels)
   Example transformation:
   - "Period 1 (1900-1955)" → "Early Legal Foundation (1900-1955)"
   - "Period 2 (1956-1994)" → "Philosophical Refinement (1956-1994)"
   - "Period 3 (1995-2018)" → "Computing Emergence (1995-2018)"
   - "Period 4 (2019-2024)" → "AI Autonomy Era (2019-2024)"

2. **Add Period Metadata**
   For each period, document:
   - **Theme**: Dominant conceptual framework (e.g., "Agent as legal representative")
   - **Key Concepts**: Core definitions in this period (e.g., "Principal-agent relationship")
   - **Domains**: Disciplines active in this period (e.g., "Law, Contract Theory")
   - **Transitions**: What changes at period boundaries

3. **Adjust Period Boundaries** (if needed)
   - Align boundaries with historical events (e.g., 1995 = first AI agent paper)
   - Ensure documents map correctly to periods
   - Avoid gaps or overlaps unless intentional

4. **Assign Period Colors**
   Use distinct colors for timeline visualization:
   - Early periods: Blues, grays (historical, foundational)
   - Middle periods: Greens, purples (transitional, philosophical)
   - Recent periods: Oranges, reds (contemporary, technical)

**Period Design Principles**:

1. **Alignment with Semantic Shifts**
   - Periods should correspond to semantic change events
   - Boundaries mark major conceptual transitions
   - Example: 1956 (Anscombe) marks shift to intentionality focus

2. **Disciplinary Coherence**
   - Each period should have dominant discipline(s)
   - Cross-disciplinary periods should highlight interaction
   - Example: 1995-2018 is "Computing Emergence" (CS/AI focus)

3. **Document Distribution**
   - Avoid periods with zero documents (add sources or merge periods)
   - Prefer 1-3 documents per period for focused analysis
   - Too many documents (>5) may need period subdivision

4. **Temporal Granularity**
   - For 100+ year spans: 4-6 periods (20-30 years each)
   - For 50-100 year spans: 3-5 periods (15-25 years each)
   - For <50 year spans: 2-4 periods (10-15 years each)

**Deliverables**:
- 4-6 temporal periods created
- Periods named with meaningful labels
- Period metadata documented (theme, concepts, domains)
- Period boundaries aligned with semantic shifts
- Timeline visualization rendering correctly

### Phase 6: Semantic Event Identification

**Objective**: Create semantic change events backed by the Semantic Change Ontology

**Preparation**:

1. **Review Ontology Event Types**
   Navigate to: `/experiments/ontology/info`
   - View all 18+ event types from semantic-change-ontology-v2.ttl
   - Read definitions and academic citations
   - Identify event types matching observed changes

2. **Common Event Types for Temporal Evolution**:
   - **Extensional Drift**: Extension of term to new referents (e.g., humans → software agents)
   - **Intensional Drift**: Change in definitional properties (e.g., simple automation → intelligent decision-making)
   - **Amelioration**: Term gains positive connotation
   - **Pejoration**: Term gains negative connotation
   - **Specialization**: Term narrows to domain-specific meaning
   - **Generalization**: Term broadens to wider contexts
   - **Semantic Borrowing**: Term adopted from one discipline to another
   - **Metaphorical Extension**: Term extended via metaphor

**Event Creation Process**:

1. **Navigate to Event Creation**
   From Temporal Term Manager: Click "Add Semantic Event" button

2. **Event Form Fields**:
   - **Event Type**: Select from ontology-backed dropdown (18+ types)
   - **Description**: Analytical description of semantic change (2-4 sentences)
   - **From Period**: Source period (where change originates)
   - **To Period**: Target period (where change manifests)
   - **Citation**: Auto-populated from ontology (academic paper)
   - **Example** (optional): Specific usage demonstrating change

3. **Create Events for Major Transitions**:

   **Example Event 1: Extensional Drift (Philosophy → Computing)**
   ```
   Type: Extensional Drift
   Description: The term "agent" extends from exclusively biological entities
   (humans with intentionality and moral responsibility) to include computational
   entities (software agents with autonomy and goal-directedness). This shift
   represents a fundamental broadening of the extension without necessarily
   changing the core intensional properties (autonomy, goal-direction).
   From Period: Philosophical Refinement (1956-1994)
   To Period: Computing Emergence (1995-2018)
   Citation: Hamilton, W. L., Leskovec, J., & Jurafsky, D. (2016). Diachronic
   word embeddings reveal statistical laws of semantic change. ACL.
   ```

   **Example Event 2: Specialization (Legal → AI)**
   ```
   Type: Specialization
   Description: While legal discourse continues to use "agent" for human
   representatives in principal-agent relationships, AI discourse develops a
   specialized technical meaning focused on autonomous computational systems.
   The term becomes polysemous with domain-specific specialization rather than
   wholesale replacement.
   From Period: Early Legal Foundation (1900-1955)
   To Period: AI Autonomy Era (2019-2024)
   Citation: Vanhove, M. (2008). Semantic, pragmatic and lexicological change.
   In From polysemy to semantic change (pp. 1-14). John Benjamins.
   ```

   **Example Event 3: Intensional Drift (Computing → AI)**
   ```
   Type: Intensional Drift
   Description: The definition of "agent" in computing narrows and deepens from
   simple task automation (early software agents) to sophisticated decision-making
   and learning capabilities (modern AI agents). Key intensional properties shift
   from "executes predefined tasks" to "learns and adapts behavior dynamically."
   From Period: Computing Emergence (1995-2018)
   To Period: AI Autonomy Era (2019-2024)
   Citation: Stavropoulos, P., Vavliakis, K. N., & Pitas, I. (2019). Lexical
   change detection using Wikipedia. IEEE Transactions on Knowledge and Data
   Engineering.
   ```

   **Example Event 4: Semantic Borrowing (Philosophy → AI)**
   ```
   Type: Semantic Borrowing
   Description: AI research explicitly borrows philosophical concepts of
   intentionality, autonomy, and rational agency but redefines them in
   computational and functional terms. Philosophical vocabulary is adopted but
   stripped of phenomenological and moral dimensions, creating a technical
   homonym of the original term.
   From Period: Philosophical Refinement (1956-1994)
   To Period: AI Autonomy Era (2019-2024)
   Citation: Lucy, L., Demszky, D., Bromley, P., & Jurafsky, D. (2023).
   Content analysis of textbooks via natural language processing. In Proceedings
   of ICQE.
   ```

4. **Event Creation Workflow**:
   ```
   For each identified semantic change:
   a. Click "Add Semantic Event"
   b. Select event type from dropdown (loads definition + citation)
   c. Review definition in metadata panel
   d. Write analytical description (use definition as guide)
   e. Select from/to periods (must exist from Phase 5)
   f. Verify citation auto-populated
   g. Add example usage (optional but recommended)
   h. Click "Create Event"
   i. Verify event appears on timeline
   ```

5. **Event Validation**:
   After creating each event, verify:
   - Event card appears in timeline between correct periods
   - Arrow shows transition direction (from → to)
   - Citation displayed with book icon
   - Event type badge shows correct color
   - Description is analytical (not merely descriptive)

**Event Design Principles**:

1. **Ontology Grounding**
   - Every event must use ontology-backed event type
   - Citation should support the specific type of change
   - Definition should inform description writing

2. **Analytical Depth**
   - Descriptions should explain WHY change occurred (not just WHAT changed)
   - Reference historical/disciplinary context
   - Connect to broader semantic change patterns

3. **Period Alignment**
   - Events should span period boundaries (from Period N to Period N+1)
   - Events can skip periods if change is gradual (e.g., Period 1 → Period 4)
   - Avoid creating events within single period

4. **Evidence-Based**
   - Each event should be evidenced by documents in relevant periods
   - Cross-reference document quotations/definitions
   - Avoid speculative or unfounded claims

**Deliverables**:
- 3-5 semantic change events created
- Each event backed by ontology type + citation
- Events span period boundaries on timeline
- Descriptions are analytical and evidence-based
- Timeline visualization complete

### Phase 7: Timeline Visualization & Verification

**Objective**: Generate and verify complete timeline visualization for JCDL presentation

**Timeline Access**:

1. **Management View** (vertical cards)
   URL: `/experiments/{id}/manage_temporal_terms`
   - Shows periods and events as vertical cards
   - Includes edit/delete buttons
   - Used for experiment configuration

2. **Full-Page Timeline View** (horizontal presentation)
   URL: `/experiments/{id}/timeline`
   - Shows periods as horizontal timeline
   - Events displayed as transition arrows
   - Optimized for presentations and screenshots
   - No edit controls (read-only)

**Verification Checklist**:

1. **Period Display**
   - [ ] All periods appear in chronological order (left to right)
   - [ ] Period labels are meaningful and concise
   - [ ] Period date ranges are correct (start-end years)
   - [ ] Period colors are distinct and readable
   - [ ] Documents listed under correct periods

2. **Event Display**
   - [ ] All events appear between correct periods
   - [ ] Event type badges show correct colors
   - [ ] Citations display with book icon
   - [ ] Descriptions are complete and readable
   - [ ] Transition arrows point in correct direction

3. **Overall Timeline**
   - [ ] Timeline spans complete date range (earliest to latest)
   - [ ] No gaps or overlaps in periods
   - [ ] Event density is reasonable (not overcrowded)
   - [ ] Timeline renders correctly in full-page view
   - [ ] Timeline is screenshot-ready for presentations

**Screenshot Preparation** (for JCDL):

1. **Capture Full-Page Timeline**
   - Navigate to `/experiments/{id}/timeline`
   - Use browser full-screen (F11)
   - Capture full timeline (may need browser zoom adjustment)
   - Save as PNG: `{term}_temporal_evolution_timeline.png`

2. **Capture Management View** (optional)
   - Navigate to `/experiments/{id}/manage_temporal_terms`
   - Capture vertical card layout
   - Shows edit capabilities and metadata
   - Save as PNG: `{term}_management_view.png`

3. **Prepare Demo Notes**
   Create markdown file documenting:
   - Experiment ID and URL
   - Focus term and date range
   - Number of documents, periods, events
   - Key semantic shifts demonstrated
   - Academic citations used
   - Demo talking points

**Deliverables**:
- Timeline visualization complete and verified
- Screenshots captured for presentation
- Demo notes prepared
- Experiment ready for JCDL demonstration

### Phase 8: Provenance Tracking & Export

**Objective**: Verify PROV-O provenance tracking and prepare experiment for publication

**Provenance Verification**:

1. **Check Provenance Records**
   Query database for provenance entities:
   ```sql
   -- From ontextract_db
   SELECT * FROM provenance_entity WHERE experiment_id = {experiment_id};
   SELECT * FROM provenance_activity WHERE experiment_id = {experiment_id};
   SELECT * FROM provenance_agent WHERE experiment_id = {experiment_id};
   ```

2. **Expected Provenance Records**:
   - **Entities**: Documents, periods, semantic events, timeline
   - **Activities**: Document upload, period creation, event creation, timeline generation
   - **Agents**: User (demo), System (OntExtract), Ontology (semantic-change-ontology-v2)
   - **Associations**: Which agent performed which activity
   - **Derivations**: Which entities derived from which sources

3. **Verify Ontology Metadata**:
   For each semantic event, verify stored metadata:
   - `type_uri`: Link to semantic-change-ontology-v2.ttl class
   - `type_label`: Human-readable event type name
   - `citation`: Academic paper citation from ontology
   - `definition`: Event type definition from ontology

**Export & Documentation**:

1. **Export Experiment Metadata**
   Create JSON export:
   ```json
   {
     "experiment_id": 75,
     "name": "Agent Temporal Evolution",
     "focus_term": "agent",
     "type": "temporal_evolution",
     "date_range": "1910-2024",
     "documents": [...],
     "periods": [...],
     "semantic_events": [...],
     "provenance": {...}
   }
   ```

2. **Create Experiment Summary Document**
   Markdown file: `{term}_temporal_evolution_summary.md`
   Sections:
   - Experiment Overview
   - Document Collection
   - Temporal Periods
   - Semantic Change Events
   - Academic Citations
   - Timeline Visualization
   - Provenance Records

3. **Prepare JCDL Materials**
   - Experiment summary (markdown)
   - Timeline screenshots (PNG)
   - Demo script (talking points)
   - Backup plan (if live demo fails)

**Deliverables**:
- Provenance records verified
- Experiment metadata exported
- Summary documentation complete
- JCDL presentation materials ready

## Repeatable Workflow Summary

To create a new temporal evolution experiment, follow this sequence:

```bash
# Phase 1: Analyze documents
# - Read all PDFs for metadata
# - Create processing session plan
# - Validate temporal coverage

# Phase 2: Create/validate focus term
# - Navigate to /terms
# - Create term if needed
# - Add MW/OED reference definitions

# Phase 3: Create experiment
# - Navigate to /experiments/new
# - Select "Temporal Evolution"
# - Select focus term (auto-fills name)
# - Customize description
# - Save experiment (note ID)

# Phase 4: Upload documents (multi-session, chapter-aware)
# Session 1: Small documents + pre-extracted chapters (<100 pages)
# Session 2: Medium full documents (50-200 pages)
# Session 3: Large full books (>200 pages, extract chapters first)
# Session 4: Verify and clean up (including chapter metadata)

# Phase 5: Design periods
# - Auto-generate from document dates
# - Rename with meaningful labels
# - Add period metadata (theme, concepts)
# - Adjust boundaries if needed

# Phase 6: Create semantic events
# - Review ontology event types
# - Create 3-5 events spanning periods
# - Use ontology-backed types + citations
# - Write analytical descriptions

# Phase 7: Verify timeline
# - Check management view (vertical cards)
# - Check full-page timeline view
# - Capture screenshots for presentation
# - Prepare demo notes

# Phase 8: Export & document
# - Verify provenance records
# - Export experiment metadata
# - Create summary documentation
# - Prepare JCDL materials
```

## Technical Details

### Database Tables Used

**Core Experiment Tables**:
- `experiments`: Experiment metadata (name, type, description)
- `terms`: Focus term definition
- `documents`: Source documents with metadata
- `experiment_documents`: Document-experiment associations

**Temporal Analysis Tables**:
- `temporal_periods`: Period definitions (start_year, end_year, label, theme)
- `semantic_change_events`: Event records (type, description, from_period, to_period)
- `period_metadata`: Additional period data (JSON)

**Provenance Tables**:
- `provenance_entity`: PROV-O entities (documents, periods, events)
- `provenance_activity`: PROV-O activities (creation, modification)
- `provenance_agent`: PROV-O agents (user, system, ontology)

### API Endpoints Used

**Experiment Management**:
- `GET /experiments/new` - Create experiment form
- `POST /experiments/create` - Create experiment
- `GET /experiments/{id}/view` - View experiment
- `GET /experiments/{id}/manage_temporal_terms` - Manage temporal experiment

**Document Management**:
- `GET /upload` - Upload form
- `POST /upload/upload_document` - Upload PDF
- `POST /upload/create_reference` - Create reference document (Quick Add)

**Temporal Period Management**:
- `POST /experiments/{id}/temporal/periods/auto_generate` - Auto-generate periods
- `POST /experiments/{id}/temporal/periods` - Create period
- `PUT /experiments/{id}/temporal/periods/{period_id}` - Update period
- `DELETE /experiments/{id}/temporal/periods/{period_id}` - Delete period

**Semantic Event Management**:
- `GET /experiments/{id}/semantic_event_types` - Get ontology event types
- `POST /experiments/{id}/temporal/semantic_events` - Create event
- `PUT /experiments/{id}/temporal/semantic_events/{event_id}` - Update event
- `DELETE /experiments/{id}/temporal/semantic_events/{event_id}` - Delete event

**Timeline Visualization**:
- `GET /experiments/{id}/timeline` - Full-page timeline view

**Ontology Integration**:
- `GET /experiments/ontology/info` - View ontology metadata

### Configuration Files

**Semantic Change Ontology**:
- Path: `/home/chris/onto/OntExtract/ontologies/semantic-change-ontology-v2.ttl`
- Classes: 34 event type classes
- Citations: 33 academic citations from 12 papers
- Validation: Pellet reasoner (PASSED)

**OntExtract Settings**:
- Database: `ontextract_db` (PostgreSQL)
- Port: 8765
- Virtual Environment: `/home/chris/onto/OntExtract/venv/`

## Common Issues & Solutions

### Issue 1: Focus Term Not Available in Dropdown

**Symptom**: When creating experiment, focus term dropdown is empty or missing desired term

**Solution**:
1. Navigate to `/terms/new`
2. Create term with exact spelling (lowercase, singular)
3. Save term and note ID
4. Return to `/experiments/new`
5. Refresh page and select term from dropdown

### Issue 2: Large PDF Upload Fails

**Symptom**: Upload times out or returns error for PDFs >100 pages

**Solution**:
- **Option A**: Extract relevant sections using `pdftk` or PDF editor
  ```bash
  pdftk input.pdf cat 1-50 output excerpt.pdf
  ```
- **Option B**: Use Quick Add Reference to create conceptual document
  - Include key excerpts in description field
  - Link to full source in notes
- **Option C**: Increase server timeout (development only)
  - Edit `app/__init__.py`: `app.config['TIMEOUT'] = 600`

### Issue 3: Auto-Generated Periods Have Generic Names

**Symptom**: Periods created as "Period 1", "Period 2" instead of meaningful labels

**Solution**:
This is expected behavior. Auto-generation creates periods from dates only.
1. After auto-generation, click "Edit" on each period card
2. Rename with meaningful labels (e.g., "Early Legal Foundation (1900-1955)")
3. Add period metadata (theme, concepts, domains)
4. Save changes

### Issue 4: Semantic Event Citation Not Displaying

**Symptom**: Event created but citation field is empty on timeline

**Solution**:
1. Verify ontology loaded: Navigate to `/experiments/ontology/info`
2. Check event type selection: Citation auto-populates from ontology
3. If ontology not loaded:
   ```bash
   # Check ontology file exists
   ls -lh /home/chris/onto/OntExtract/ontologies/semantic-change-ontology-v2.ttl

   # Restart OntExtract server
   cd /home/chris/onto/OntExtract
   source venv/bin/activate
   python run.py
   ```
4. Recreate event with correct event type selection

### Issue 5: Timeline Not Rendering

**Symptom**: Navigate to `/experiments/{id}/timeline` but page is blank or errors

**Solution**:
1. Check browser console for JavaScript errors
2. Verify periods exist: At least 2 periods required for timeline
3. Verify events exist: At least 1 event required for timeline
4. Check period metadata: Ensure start_year < end_year for all periods
5. Clear browser cache and reload

### Issue 6: Document Dates Not Parsing Correctly

**Symptom**: Publication date shows as "None" or incorrect year

**Solution**:
1. When uploading, use explicit date format: `YYYY` or `YYYY-MM-DD`
2. Avoid ambiguous formats: "1956" not "56", "2022-03-15" not "March 2022"
3. For date ranges, use earliest year: "1995-1998" → "1995"
4. After upload, verify date in document list
5. Edit document to correct date if needed

### Issue 7: Provenance Records Missing

**Symptom**: Querying provenance tables returns no records for experiment

**Solution**:
1. Check ProvenanceService is enabled in config
2. Verify database schema up to date:
   ```bash
   cd /home/chris/onto/OntExtract
   source venv/bin/activate
   flask db upgrade
   ```
3. Check service logs for provenance errors
4. Recreate experiment (provenance tracked on creation)

### Issue 8: Documents Not Appearing in Experiment View

**Symptom**: Documents uploaded successfully but don't appear in experiment view, or "View" links show "Not Found"

**Solution**:
This occurs when documents are associated in the wrong table. OntExtract uses two tables:
- `experiment_documents` (legacy association table)
- `experiment_documents_v2` (current processing table with ID primary key)

The web interface reads from `experiment_documents_v2`, so documents must be in this table.

```sql
-- Check which table has the associations
SELECT COUNT(*) FROM experiment_documents WHERE experiment_id = [id];
SELECT COUNT(*) FROM experiment_documents_v2 WHERE experiment_id = [id];

-- If documents are in wrong table, insert into v2:
INSERT INTO experiment_documents_v2 (
    experiment_id, document_id, processing_status,
    embeddings_applied, segments_created, nlp_analysis_completed,
    added_at, updated_at
)
SELECT
    experiment_id, document_id, 'pending',
    false, false, false,
    NOW(), NOW()
FROM experiment_documents
WHERE experiment_id = [id]
ON CONFLICT (experiment_id, document_id) DO NOTHING;
```

After fixing associations, documents will appear in the interface and "View" links will work.

### Issue 9: Documents Show 0 Words After Upload

**Symptom**: Documents uploaded but show 0 word count, no text content visible

**Solution**:
OntExtract does not automatically extract text from PDFs during upload. You must run text extraction and cleanup manually:

```python
from app import create_app, db
from app.models import Document
from app.utils.file_handler import FileHandler
from app.services.text_cleanup_service import TextCleanupService

app = create_app()
file_handler = FileHandler()
cleanup_service = TextCleanupService()

with app.app_context():
    docs = Document.query.filter(Document.id.between(start_id, end_id)).all()

    for doc in docs:
        # Extract text from PDF
        full_path = os.path.join('/home/chris/onto/OntExtract', doc.file_path)
        result = file_handler.extract_text_with_method(full_path, os.path.basename(full_path))

        if result:
            text, extraction_method = result

            # Clean with LLM
            cleaned_text, metadata = cleanup_service.clean_text(text)

            # Update document
            doc.content = cleaned_text
            doc.word_count = len(cleaned_text.split())
            doc.character_count = len(cleaned_text)
            doc.status = 'processed'
            doc.processing_metadata['text_cleanup'] = {
                'method': 'llm_claude',
                'model': metadata.get('model'),
                'chunks_processed': metadata.get('chunks_processed')
            }
            db.session.commit()
```

After extraction, create processing operation records to track the cleanup in the UI.

### Issue 10: Confusion About Chapter Extraction

**Symptom**: Agent says "handle Russell & Norvig's 1000+ pages" but you already have a 44-page chapter extracted

**Solution**:
This is a chapter detection issue. The agent should recognize pre-extracted chapters.

**How to identify pre-extracted chapters**:
1. **Check filename**: Contains chapter title (e.g., "Intelligent Agents") or chapter number (e.g., "Ch 2")
2. **Check page count**: Textbook with <100 pages is likely extracted chapter
3. **Check first page**: Look for chapter heading, not book cover

**Correct handling**:
- **If you have pre-extracted chapter** (like "Russell and Norvig - Intelligent Agents.pdf" at 44 pages):
  - Upload as-is (no extraction needed)
  - Document type: "book_chapter" (NOT "book")
  - Title: "Intelligent Agents (Chapter 2)"
  - Fill chapter metadata: Chapter Number=2, Source Book="AI: A Modern Approach (4th ed.)", Source Pages=1132

- **If you have full book** (like "AI: A Modern Approach FULL.pdf" at 1132 pages):
  - Extract relevant chapter first using pdftk
  - Then upload extracted chapter as "book_chapter"

**Why chapter awareness matters**:
- Proper attribution (cite chapter, not full book)
- Accurate page counts for provenance
- Better citations in timeline and documentation
- Avoids unnecessary extraction work

**Example**:
```
WRONG: "Russell & Norvig 2022 (1132 pages)" - implies full book uploaded
RIGHT: "Russell & Norvig 2022, Chapter 2: Intelligent Agents (44 pages) from AI: A Modern Approach (4th ed., 1132 pages)"
```

## Agent Usage

Invoke this agent to create temporal evolution experiments:

**New Experiment from Document Collection**:
"Create a temporal evolution experiment for 'agent' using documents in /home/chris/onto/OntExtract/experiments/documents/source_documents/"

**Recreate Existing Experiment** (for JCDL testing):
"Recreate the 'agent' temporal evolution experiment with updated periods and events"

**Add Documents to Existing Experiment**:
"Add the following documents to experiment 75: [list of document paths]"

**Generate Timeline Visualization**:
"Generate and verify the timeline visualization for experiment 75"

The agent will execute the complete 8-phase workflow, handling document analysis, term creation, experiment setup, period design, event identification, and timeline generation autonomously.

## JCDL Presentation Checklist

Before conference presentation, verify:

- [ ] Experiment created with meaningful name and description
- [ ] Focus term exists with reference definitions (MW/OED)
- [ ] All documents uploaded with correct metadata (dates, authors, domains)
- [ ] 4-6 temporal periods created with meaningful labels and themes
- [ ] 3-5 semantic events created with ontology-backed types and citations
- [ ] Timeline renders correctly in full-page view (`/experiments/{id}/timeline`)
- [ ] Screenshots captured for slides (timeline + management views)
- [ ] Demo script prepared with talking points
- [ ] Backup plan documented (if live demo fails)
- [ ] Provenance records verified (PROV-O compliance)
- [ ] Experiment summary documentation complete

**Demo Credentials**:
- URL: http://localhost:8765 (development) or https://ontextract.ontorealm.net (production)
- Username: demo
- Password: demo123

**Demo Experiment Examples**:
- Experiment ID 75: "Professional Ethics Evolution (1867-1947)" - 7 documents, 4 periods, 4 events
- URL: http://localhost:8765/experiments/75/timeline

## References

**Semantic Change Ontology**:
- Hamilton et al. (2016). Diachronic word embeddings reveal statistical laws of semantic change. ACL.
- Vanhove (2008). Semantic, pragmatic and lexicological change. John Benjamins.
- Stavropoulos et al. (2019). Lexical change detection using Wikipedia. IEEE TKDE.
- Lucy et al. (2023). Content analysis of textbooks via NLP. ICQE.

**OntExtract Documentation**:
- [JCDL_STANDALONE_IMPLEMENTATION.md](../JCDL_STANDALONE_IMPLEMENTATION.md) - Conference implementation plan
- [JCDL_TESTING_CHECKLIST.md](../JCDL_TESTING_CHECKLIST.md) - Browser testing checklist
- [DEMO_EXPERIMENT_SUMMARY.md](../DEMO_EXPERIMENT_SUMMARY.md) - Demo data reference
- [PROGRESS.md](../PROGRESS.md) - Development progress tracker

**Related Agents**:
- None (first OntExtract agent)
