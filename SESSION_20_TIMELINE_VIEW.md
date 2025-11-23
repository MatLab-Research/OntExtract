# Session 20: Horizontal Timeline View

**Feature**: Alternative visualization for temporal semantic events

---

## What Was Added

A new **horizontal timeline view** alongside the existing list view for visualizing semantic events and temporal periods.

### UI Components

1. **View Toggle Buttons** (Top right of page)
   - **List** button - Shows vertical card layout (default)
   - **Timeline** button - Shows horizontal timeline visualization

2. **Horizontal Timeline Layout**
   - **Periods Row**: Colored segments showing temporal periods side-by-side
   - **Events Row**: Semantic event cards with arrows showing transitions

---

## Visual Design

### Periods Row
- Each period displayed as a colored segment
- Shows period label and year range (e.g., "1850–1900")
- Hover effect: lifts up with shadow
- Uses period colors from configuration

### Events Row
- Event cards displayed vertically below periods
- Each card shows:
  - Arrow (→) indicating transition
  - Event type badge (e.g., "Intensional Drift")
  - Event description
  - Academic citation

---

## Implementation Details

### Files Modified

**Template**: [app/templates/experiments/temporal_term_manager.html](app/templates/experiments/temporal_term_manager.html)

**Changes**:
1. Added view toggle buttons (lines 573-582)
2. Added horizontal timeline HTML (lines 796-841)
3. Added CSS for horizontal layout (lines 542-654)
4. Added JavaScript toggle function (lines 1183-1201)

### CSS Classes

**Periods**:
- `.horizontal-timeline-container` - Main container with scroll
- `.periods-row` - Flex container for period segments
- `.period-segment` - Individual period block
- `.period-label` - Period name
- `.period-years` - Year range

**Events**:
- `.events-row` - Container for event cards
- `.timeline-event-card` - Individual event card
- `.event-arrow` - Right arrow (→)
- `.event-type-badge` - Event type label
- `.event-description` - Event description text
- `.event-citation` - Academic citation

### JavaScript

**Function**: `switchView(view)`
- **Parameters**: `'list'` or `'timeline'`
- **Action**: Toggles display between vertical list and horizontal timeline
- **Updates**: Button active states

---

## How To Use

### For Demo

1. Navigate to: http://localhost:8765/experiments/75/manage_temporal_terms
2. Click the **Timeline** button (top right)
3. View periods arranged horizontally
4. See events with arrows showing transitions
5. Hover over periods/events for effects
6. Click **List** to return to card view

### Benefits for JCDL Demo

**List View** (default):
- Detailed cards with all metadata
- Good for close reading
- Shows documents linked to each event

**Timeline View**:
- Spatial/temporal understanding
- Shows progression visually
- Better for presentations
- Demonstrates chronological flow

---

## Data Requirements

The timeline view requires:
- `config.periods` - Array of period objects with:
  - `id`: Period identifier (e.g., "period_1")
  - `label`: Period name (e.g., "Pre-Standardization")
  - `start_year`: Starting year (e.g., 1850)
  - `end_year`: Ending year (e.g., 1900)
  - `color`: CSS color code

- `semantic_events` - Array of event objects with:
  - `id`: Event identifier
  - `type_label`: Display name (e.g., "Intensional Drift")
  - `description`: Event description
  - `citation`: Academic citation
  - `from_period`: Starting period ID
  - `to_period`: Ending period ID

Demo experiment (ID 75) has all required data.

---

## Visual Features

### Responsive Design
- Horizontal scroll for wide timelines
- Minimum widths ensure readability
- Hover effects for interaction feedback

### Color Scheme
- Period colors from configuration (blues gradient)
- Event cards: purple gradient (#6f42c1)
- Citations: muted gray
- Consistent with Bootstrap theme

### Transitions
- Smooth opacity/transform on hover
- 0.3s ease-in-out animations
- Shadow effects on hover

---

## Future Enhancements (Optional)

Could add:
- **Zoom controls**: Expand/collapse timeline scale
- **Filtering**: Show only certain event types
- **Positioning**: Place events between periods they connect
- **Connections**: Draw lines from events to their periods
- **Export**: Screenshot or PDF of timeline

---

## Technical Notes

**Browser Compatibility**:
- Uses modern CSS (flexbox, gradients)
- JavaScript ES6 (const, arrow functions)
- Should work in all modern browsers

**Performance**:
- CSS animations hardware-accelerated
- No heavy JavaScript processing
- Renders instantly with 4-5 events

**Accessibility**:
- Semantic HTML structure
- Color-blind friendly (text labels)
- Keyboard navigation supported

---

**Status**: Timeline view implemented and ready for testing

**Demo Ready**: Yes - switch views during presentation to show different perspectives
