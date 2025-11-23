# Session 20: Full-Page Timeline View

**Feature**: Dedicated full-width timeline visualization page

---

## What Was Added

A new **dedicated timeline page** for full-width horizontal visualization of temporal periods and semantic events, following the same pattern as the provenance graph view.

### New Route

**URL**: `/experiments/<id>/timeline`

**Access**: Click "View Timeline" button from temporal term manager when semantic events exist

### UI Components

1. **Timeline Header** (Sticky)
   - Experiment title
   - "Temporal Timeline Visualization" subtitle
   - Back to Management button

2. **Full-Width Timeline Content**
   - **Periods Row**: Horizontal colored segments showing all temporal periods
   - **Events Section**: Semantic change events with arrows and citations
   - Clean, presentation-ready layout

---

## Visual Design

### Periods Row
- Full-width horizontal layout with 4px gap between segments
- Each period:
  - Minimum width: 250px
  - Gradient background with period color
  - Centered label and year range
  - Hover: Lifts up with enhanced shadow
  - Box shadow for depth

### Events Section
- Title: "Semantic Change Events" with bolt icon
- Event cards:
  - Large right arrow (→) indicator
  - Event type badge with gradient background
  - Description text (1.05rem)
  - Citation with book icon
  - Hover: Shifts right with enhanced shadow
  - Min width: 700px, max width: 1200px

---

## Implementation Details

### Files Created

**Template**: [app/templates/experiments/temporal_timeline_view.html](app/templates/experiments/temporal_timeline_view.html)

**Features**:
1. Extends base.html
2. Full-width container (container-fluid)
3. Sticky header at top
4. Background: #f8f9fa
5. Responsive design with media queries

### Files Modified

**Route**: [app/routes/experiments/temporal.py](app/routes/experiments/temporal.py) (lines 95-124)

**Added**:
```python
@experiments_bp.route('/<int:experiment_id>/timeline')
@api_require_login_for_write
def timeline_view(experiment_id):
    """Full-page horizontal timeline visualization"""
    data = temporal_service.get_temporal_ui_data(experiment_id)

    return render_template(
        'experiments/temporal_timeline_view.html',
        experiment=data['experiment'],
        periods=data.get('periods', []),
        semantic_events=data['semantic_events']
    )
```

**Template**: [app/templates/experiments/temporal_term_manager.html](app/templates/experiments/temporal_term_manager.html)

**Changes**:
1. Replaced toggle buttons with link to timeline page (lines 672-677)
2. Removed horizontal timeline HTML section
3. Removed `switchView()` JavaScript function
4. Removed horizontal timeline CSS

**Before**:
```html
<div class="btn-group me-2" role="group">
    <button type="button" class="btn btn-outline-secondary active" id="view-list-btn" onclick="switchView('list')">
        <i class="fas fa-list"></i> List
    </button>
    <button type="button" class="btn btn-outline-secondary" id="view-timeline-btn" onclick="switchView('timeline')">
        <i class="fas fa-stream"></i> Timeline
    </button>
</div>
```

**After**:
```html
<a href="{{ url_for('experiments.timeline_view', experiment_id=experiment.id) }}"
   class="btn btn-outline-secondary me-2">
    <i class="fas fa-stream"></i> View Timeline
</a>
```

---

## How To Use

### For Demo

1. Navigate to: http://localhost:8765/experiments/75/manage_temporal_terms
2. Click the **View Timeline** button (top left, after Save Configuration)
3. Full-page timeline opens with:
   - 4 colored period segments across the top
   - 4 semantic events below with arrows and citations
4. Hover over periods/events for visual effects
5. Click **Back to Management** to return

### Benefits Over Toggle Approach

**Full Page**:
- Uses entire screen width for better visualization
- Cleaner separation between management and visualization
- Optimized layout for presentations
- Consistent with provenance graph pattern
- Dedicated URL for bookmarking/sharing

**Management Page**:
- Remains focused on editing/configuration
- No layout switching complexity
- Simpler button design

---

## Data Requirements

Same as before:
- `periods` - Array of period objects with id, label, start_year, end_year, color
- `semantic_events` - Array of event objects with type_label, description, citation

Demo experiment (ID 75) has all required data.

---

## CSS Features

### Full-Width Layout
```css
.timeline-content {
    padding: 40px 60px;
    min-height: calc(100vh - 140px);
    background: #f8f9fa;
}
```

### Sticky Header
```css
.timeline-header {
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
```

### Period Segments
- Min width: 250px
- Padding: 30px 24px (larger than toggle version)
- Border radius: 12px
- Box shadow: 0 2px 8px

### Event Cards
- Min width: 700px (wider than toggle version)
- Max width: 1200px
- Padding: 24px 28px
- Border-left: 5px solid #6f42c1
- Hover: translateX(12px)

---

## Responsive Design

Mobile breakpoint (< 768px):
- Reduces padding to 20px
- Shrinks period min-width to 200px
- Reduces event card min-width to 500px
- Adjusts font sizes

---

## Empty State

When no periods or events exist:
- Centered message with stream icon
- Link back to Temporal Term Manager
- Instruction to configure periods/events

---

## URL Structure

```
/experiments/75/manage_temporal_terms  - Management page (list view)
/experiments/75/timeline               - Full-page timeline visualization
```

Similar to provenance:
```
/provenance/timeline                   - Provenance list view
/provenance/graph                      - Full-page graph visualization
```

---

## Performance

**Advantages**:
- No JavaScript view switching
- Simpler DOM (no hidden elements)
- Dedicated CSS (no unused styles)
- Better browser performance
- Cleaner code separation

---

## Future Enhancements (Optional)

Could add:
- **Zoom controls**: Expand/collapse timeline scale
- **Export**: PDF or PNG export of timeline
- **Print stylesheet**: Optimized for printing
- **Fullscreen mode**: Hide header for presentations
- **Event filtering**: Show only certain event types
- **Period details**: Click to see documents in period

---

## Technical Notes

**Pattern Consistency**:
- Follows same approach as `/provenance/graph`
- Dedicated route + template for visualization
- Management page remains focused on editing
- Clean URL structure

**Code Cleanup**:
- Removed 113 lines of unused CSS
- Removed 18 lines of unused JavaScript
- Removed 42 lines of unused HTML
- Total reduction: ~173 lines

**Maintainability**:
- Clearer separation of concerns
- Easier to modify visualization independently
- No toggle state management
- Simpler testing

---

**Status**: Full-page timeline view implemented and ready

**Demo Ready**: Yes - dedicated URL for presentations

**URL**: http://localhost:8765/experiments/75/timeline
