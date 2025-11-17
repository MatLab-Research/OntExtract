# Document Versioning Enhancement Plan

**Created:** 2024-11-16
**Status:** Planning
**Goal:** Implement comprehensive document version management that preserves metadata and experiment relationships across document versions

---

## Problem Statement

Currently, when documents are processed (e.g., cleaned with LLM), child versions are created but:
- Metadata from parent documents doesn't carry over
- Experiment associations are version-specific, making it hard to see all experiments across a document family
- No clear UI indication of version status or navigation between versions
- Users can't see which version of a document is associated with which experiment

---

## User Requirements (From Discussion)

1. **Metadata Strategy:** Both inherited AND document-specific metadata (if no disadvantage)
2. **Version Display:** Show requested version with clear label if other versions exist and if not latest
3. **Experiment Scope:** Show both this-version experiments AND all-version experiments with clear indicators
4. **Version Selector:** Dropdown on document page where version label is, latest version as default, no processing details in selector

---

## Technical Analysis

### Current Architecture

**Document Model Fields:**
- `parent_document_id` - Links to parent version
- `version_type` - 'original', 'processed', etc.
- `version_number` - Integer version counter
- `source_metadata` - JSONB field for metadata

**Related Models:**
- `ExperimentDocument` - Links specific document ID to experiment
- `DocumentTemporalMetadata` - Temporal metadata per document
- `ProcessingJob` - Processing operations per document

**Key Files:**
- `app/models/document.py` - Document model
- `app/routes/text_input/crud.py` - Document CRUD routes
- `app/templates/text_input/document_detail_simplified.html` - Detail page template
- `upload_agent_documents.py` - Script for uploading documents
- `clean_agent_documents.py` - Script for creating cleaned versions

### Metadata Strategy Decision

**Question:** Both inherited AND document-specific metadata?

**Analysis:**
- **Advantage:** Maximum flexibility - versions can have unique metadata while inheriting shared metadata
- **Disadvantage:** Complexity in UI (which metadata to show?), potential confusion about "source of truth"
- **Recommendation:** Use **automatic inheritance at creation time** for simplicity

**Proposed Approach:**
```
When creating child version:
1. Copy parent's source_metadata to child
2. Copy parent's publication_year to child
3. Copy parent's DocumentTemporalMetadata record
4. Add metadata_inherited_from field to track inheritance
5. Allow manual editing of child metadata (breaks inheritance)
6. Add "Sync from parent" button to re-inherit
```

**Pros:**
- Simple mental model: each version has its own metadata
- Metadata stays with version even if parent changes
- Can override if needed
- Easy to implement

**Cons:**
- Storage duplication (minimal - JSONB is efficient)
- Metadata drift if parent updated after child creation

**Decision Needed:** Proceed with automatic inheritance at creation time? Y/N

---

## Implementation Plan

### Phase 1: Backend - Metadata Inheritance

**Files to Modify:**
1. `app/services/inheritance_versioning_service.py` - Update version creation
2. `clean_agent_documents.py` - Add metadata copying
3. `upload_agent_documents.py` - Already has metadata, ensure child versions copy

**Changes:**
```python
# In version creation logic:
def create_child_version(parent_document, **kwargs):
    child = Document(**kwargs)

    # Copy metadata from parent
    if parent_document.source_metadata:
        child.source_metadata = parent_document.source_metadata.copy()

    if parent_document.publication_year:
        child.publication_year = parent_document.publication_year

    # Copy temporal metadata
    if parent_document.temporal_metadata:
        child_temporal = DocumentTemporalMetadata(
            document_id=child.id,  # After flush
            publication_year=parent_document.temporal_metadata.publication_year,
            discipline=parent_document.temporal_metadata.discipline,
            key_definition=parent_document.temporal_metadata.key_definition
        )

    # Track inheritance
    child.metadata_inherited_from = parent_document.id

    return child
```

**Tasks:**
- [ ] Update `InheritanceVersioningService.create_document_version()` to copy metadata
- [ ] Update `clean_agent_documents.py` to copy metadata when creating cleaned versions
- [ ] Add `metadata_inherited_from` field to Document model (migration needed)
- [ ] Test metadata inheritance with existing documents

### Phase 2: Backend - Version Family Queries

**Files to Modify:**
1. `app/routes/text_input/crud.py` - Update `document_detail()` route
2. `app/models/document.py` - Add version family helper methods

**New Methods Needed:**
```python
class Document:
    def get_version_family(self):
        """Get all versions in this document family"""
        # Find root document
        root = self
        while root.parent_document_id:
            root = Document.query.get(root.parent_document_id)

        # Get all descendants
        return Document.query.filter(
            (Document.id == root.id) |
            (Document.parent_document_id == root.id) |
            # Add recursive descendants...
        ).order_by(Document.version_number).all()

    def get_latest_version(self):
        """Get the latest version in this family"""
        family = self.get_version_family()
        return max(family, key=lambda d: d.version_number)

    def is_latest_version(self):
        """Check if this is the latest version"""
        return self.id == self.get_latest_version().id
```

**Tasks:**
- [ ] Add version family query methods to Document model
- [ ] Update `document_detail()` to fetch version family
- [ ] Update `document_detail()` to fetch experiments across all versions
- [ ] Add version status to response (is_latest, has_other_versions, etc.)

### Phase 3: Frontend - Version Selector UI

**Files to Modify:**
1. `app/templates/text_input/document_detail_simplified.html`

**UI Design:**
```html
<!-- Version Selector (replaces static version badge) -->
<div class="d-flex align-items-center mb-2">
    <label class="text-muted me-2">Version:</label>
    <select class="form-select form-select-sm w-auto"
            onchange="window.location.href='/input/document/' + this.value">
        {% for version in version_family %}
        <option value="{{ version.uuid }}"
                {% if version.id == document.id %}selected{% endif %}>
            v{{ version.version_number }} - {{ version.version_type|title }}
            {% if version.is_latest %} (Latest){% endif %}
        </option>
        {% endfor %}
    </select>

    {% if not document.is_latest_version %}
    <span class="badge bg-warning ms-2">
        <i class="fas fa-exclamation-triangle me-1"></i>
        Older Version - Newer version available
    </span>
    {% endif %}
</div>
```

**Tasks:**
- [ ] Add version selector dropdown
- [ ] Add warning badge for non-latest versions
- [ ] Style version selector to match existing UI
- [ ] Test navigation between versions

### Phase 4: Frontend - Experiment Display Enhancement

**Files to Modify:**
1. `app/templates/text_input/document_detail_simplified.html`

**UI Design:**
```html
<div class="card-header d-flex justify-content-between align-items-center">
    <h6 class="mb-0">
        <i class="fas fa-flask me-2"></i>Related Experiments
    </h6>
    <div class="btn-group btn-group-sm" role="group">
        <input type="radio" class="btn-check" name="expScope"
               id="expThisVersion" checked>
        <label class="btn btn-outline-primary" for="expThisVersion">
            This Version ({{ this_version_experiments|length }})
        </label>

        <input type="radio" class="btn-check" name="expScope"
               id="expAllVersions">
        <label class="btn btn-outline-primary" for="expAllVersions">
            All Versions ({{ all_version_experiments|length }})
        </label>
    </div>
</div>

<div class="card-body">
    <!-- This Version Experiments -->
    <div id="this-version-exps">
        {% for exp_doc in this_version_experiments %}
        <div class="experiment-item">
            <span class="badge bg-success mb-2">
                <i class="fas fa-check me-1"></i>v{{ document.version_number }}
            </span>
            <!-- Experiment details -->
        </div>
        {% endfor %}
    </div>

    <!-- All Version Experiments (hidden by default) -->
    <div id="all-version-exps" style="display: none;">
        {% for exp_doc in all_version_experiments %}
        <div class="experiment-item">
            <span class="badge {% if exp_doc.document_id == document.id %}bg-success{% else %}bg-secondary{% endif %} mb-2">
                <i class="fas fa-file-alt me-1"></i>v{{ exp_doc.document_version_number }}
            </span>
            <!-- Experiment details -->
        </div>
        {% endfor %}
    </div>
</div>
```

**Tasks:**
- [ ] Add toggle between "This Version" and "All Versions" experiments
- [ ] Show version badge on each experiment
- [ ] Highlight experiments using current version
- [ ] Add JavaScript toggle functionality

### Phase 5: Metadata Display Enhancement

**Files to Modify:**
1. `app/templates/text_input/document_detail_simplified.html`

**UI Changes:**
- If metadata inherited, show source indicator
- Add "Sync from Parent" button if parent metadata differs
- Show inheritance chain if multiple levels

**Tasks:**
- [ ] Update metadata display to show inheritance source
- [ ] Add sync button (if needed)
- [ ] Test with multi-level version hierarchies

---

## Testing Plan

### Test Scenarios

1. **Single Document with Multiple Versions:**
   - Upload original → Create cleaned version → Create processed version
   - Verify metadata inheritance at each level
   - Verify version selector shows all versions
   - Verify navigation between versions

2. **Experiments Across Versions:**
   - Create experiment with v1
   - View v1: should show experiment in "This Version"
   - View v2: should show experiment in "All Versions" only
   - Create experiment with v2
   - View v2: should show v2 experiment in "This Version", v1 in "All Versions"

3. **Metadata Management:**
   - Verify inherited metadata displays correctly
   - Edit metadata on child version
   - Verify parent metadata unchanged
   - Test sync functionality (if implemented)

### Test Documents
- Use existing Agent experiment documents (6 documents, each with original + cleaned versions)

---

## Migration Strategy

**For Existing Documents:**

Option 1: Retroactive Metadata Copy
```sql
-- Copy metadata from parent to children
UPDATE documents child
SET source_metadata = parent.source_metadata,
    publication_year = parent.publication_year
FROM documents parent
WHERE child.parent_document_id = parent.id
  AND child.source_metadata IS NULL;
```

Option 2: Leave existing, apply going forward
- Simpler, less risky
- Existing cleaned versions stay without metadata
- All new versions get metadata

**Decision Needed:** Retroactive fix or forward-only?

---

## Progress Tracking

### Phase 1: Backend - Metadata Inheritance
- [ ] Update InheritanceVersioningService
- [ ] Update clean_agent_documents.py
- [ ] Add metadata_inherited_from field (if needed)
- [ ] Test metadata inheritance

### Phase 2: Backend - Version Family Queries
- [ ] Add version family methods to Document model
- [ ] Update document_detail route
- [ ] Fetch all-version experiments
- [ ] Add version status flags

### Phase 3: Frontend - Version Selector
- [ ] Add version dropdown
- [ ] Add non-latest warning badge
- [ ] Test navigation

### Phase 4: Frontend - Experiment Display
- [ ] Add This/All versions toggle
- [ ] Show version badges on experiments
- [ ] Add toggle JavaScript

### Phase 5: Metadata Display
- [ ] Show inheritance indicator
- [ ] Add sync button (optional)
- [ ] Test display

---

## Open Questions

1. **Metadata Strategy:** Proceed with automatic inheritance at creation time?
2. **Migration:** Retroactive metadata copy for existing documents?
3. **UI Complexity:** Is the This/All versions toggle too complex? Alternative: always show all with clear indicators?
4. **Recursive Versions:** How many levels of versioning do we expect? (impacts query complexity)

---

## Next Steps

1. Get approval on metadata strategy decision
2. Get approval on migration strategy
3. Begin Phase 1 implementation
4. Update this document with progress

---

## Notes

- Keep version selector simple - just version number and type, no processing details
- Metadata inheritance should be transparent and automatic
- Version navigation should be seamless
- Clear visual indicators for version status critical for UX

---

## Progress Update 2024-11-16

### Phase 1: Backend - Metadata Inheritance ✅ COMPLETED

**✅ Completed Tasks:**
1. **Retroactive Migration**: Successfully copied temporal metadata from 6 parent documents to 6 child documents using SQL migration
2. **clean_agent_documents.py**: Updated to copy both `source_metadata` and `DocumentTemporalMetadata` when creating cleaned versions
3. **InheritanceVersioningService**: Updated `create_new_version()` to automatically copy metadata from source document

**Key Finding:**
- Metadata is stored in separate `document_temporal_metadata` table, NOT in `source_metadata` JSON field
- Original documents have temporal metadata with: publication_year, discipline, key_definition
- Template currently checks for `source_metadata` which is empty - needs update

**Next:** Phase 2 - Add version family methods and update routes to fetch all versions


### Phase 2: Backend - Version Family Queries ✅ COMPLETED

**✅ Completed Tasks:**
1. **Document Model**: Added `is_latest_version()` method (other version family methods already existed)
2. **document_detail Route**: Enhanced to fetch:
   - Version family (all versions)
   - Temporal metadata
   - Experiments for this version
   - Experiments for all versions in family
3. **Data Enrichment**: Added version info and flags to experiment data for template

### Phase 3: Frontend - Version Selector & Experiment Toggle ✅ COMPLETED

**✅ Completed Tasks:**
1. **Version Selector Dropdown**:
   - Added dropdown showing all versions (v1 - Original, v2 - Processed, etc.)
   - Shows "(Latest)" indicator on latest version
   - Yellow warning badge if viewing older version
   - Navigation to other versions via dropdown

2. **Temporal Metadata Display**:
   - Shows publication year and discipline from `document_temporal_metadata`
   - Replaces previous language detection info when temporal metadata available

3. **Experiment Scope Toggle**:
   - Button group to switch between "This Version" and "All Versions"
   - Shows experiment count for each scope
   - This Version: Only experiments using current document version
   - All Versions: All experiments across entire version family
   - Version badges on each experiment (green for current, gray for others)

4. **JavaScript Toggle**: Added `showExperimentScope()` function for smooth view switching

**Files Modified:**
- `app/routes/text_input/crud.py` - Enhanced `document_detail()` route
- `app/templates/text_input/document_detail_simplified.html` - Added UI components

**Ready for Testing:** ✅


### Phase 4: Title Cleanup ✅ COMPLETED

**Issue:** Cleaned documents had " (Cleaned)" suffix appended to titles, redundant with version selector showing "v2 - Processed"

**✅ Completed Tasks:**
1. **Database Cleanup**: Removed " (Cleaned)" suffix from 6 existing processed documents
   ```sql
   UPDATE documents
   SET title = REPLACE(title, ' (Cleaned)', '')
   WHERE title LIKE '% (Cleaned)'
     AND version_type = 'processed'
     AND parent_document_id IS NOT NULL;
   ```
   - Result: 6 documents updated

2. **Script Update**: Modified [clean_agent_documents.py:78](clean_agent_documents.py#L78) to keep original title
   ```python
   # Changed from:
   title=f"{document.title} (Cleaned)",
   # To:
   title=document.title,
   ```

**Verification:** All 6 processed documents now have clean titles:
- Black's Law Dictionary 1910 - Agent
- Anscombe - Intention (1957)
- Wooldridge & Jennings - Intelligent Agents (1995)
- Russell & Norvig - AI: A Modern Approach (2020) - Agents Chapter
- Black's Law Dictionary 2024 - Agent
- Oxford English Dictionary 2024 - Agent

**Impact:** Future cleaned documents will maintain original title, version info shown only in version selector dropdown

