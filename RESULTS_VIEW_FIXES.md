# Results View Fixes

Fixed processing results pages to display artifacts from the new experiment processing system.

## Problem

The results pages (segments, entities, etc.) were not displaying data from the new experiment processing system because:

1. Old system stored data in dedicated tables (`TextSegment`, `ExtractedEntity`)
2. New system stores data in `ProcessingArtifact` table with `artifact_type` field
3. Results routes only queried the old tables

## Solution

Updated result routes to query BOTH old and new storage systems using wrapper classes for compatibility.

## Changes Made

### 1. Segments Results ([pipeline.py](app/routes/processing/pipeline.py) lines 1658-1695)

**Before**: Only queried `TextSegment` table
**After**: Queries both `TextSegment` AND `ProcessingArtifact` with `artifact_type='text_segment'`

```python
# Old segments from TextSegment table
old_segments = TextSegment.query.filter(...)

# New segments from ProcessingArtifact table
new_artifacts = ProcessingArtifact.query.filter(
    artifact_type == 'text_segment'
)

# Wrapper class for compatibility
class SegmentWrapper:
    def __init__(self, artifact):
        content_data = artifact.get_content()
        self.segment_number = artifact.artifact_index + 1
        self.content = content_data.get('text', '')
        self.word_count = metadata.get('word_count')
        self.character_count = len(self.content)
```

**URL**: `/process/document/{uuid}/results/segments`

### 2. Entities Results ([pipeline.py](app/routes/processing/pipeline.py) lines 1549-1595)

**Before**: Only queried `ExtractedEntity` table
**After**: Queries both `ExtractedEntity` AND `ProcessingArtifact` with `artifact_type='extracted_entity'`

```python
# Old entities from ExtractedEntity table
old_entities = ExtractedEntity.query.filter_by(document_id=document.id)

# New entities from ProcessingArtifact table
new_artifacts = ProcessingArtifact.query.filter(
    artifact_type == 'extracted_entity'
)

# Wrapper class for compatibility
class EntityWrapper:
    def __init__(self, artifact):
        content_data = artifact.get_content()
        self.entity_text = content_data.get('entity', '')
        self.entity_type = content_data.get('entity_type', 'UNKNOWN')
        self.start_position = content_data.get('start_char')
        self.end_position = content_data.get('end_char')
        self.confidence = content_data.get('confidence', 0)
        self.context = content_data.get('context', '')
```

**URL**: `/process/document/{uuid}/results/entities`

## How It Works

1. **Dual Query System**: Each results route now queries BOTH storage systems
2. **Wrapper Classes**: New `SegmentWrapper` and `EntityWrapper` classes make `ProcessingArtifact` objects look like the old model objects
3. **Template Compatibility**: Templates remain unchanged - they receive the same data structure as before
4. **Migration Path**: Supports both old and new data simultaneously, allowing gradual migration

## Artifact Types in ProcessingArtifact Table

The new system uses these `artifact_type` values:

- `text_segment` - Segmentation results (paragraph/sentence)
- `embedding_vector` - Embedding vectors
- `extracted_entity` - Named entities and concepts
- `term_definition` - Definition extraction results
- `temporal_expression` - Temporal markers (dates, periods)
- `extracted_term` - Enhanced processing (term extraction + OED)

## Testing

To verify the fixes work:

1. Run any processing tool on a document (e.g., segment_paragraph)
2. Click "View Results" or navigate to results page
3. Should now see:
   - Processing history in sidebar
   - Statistics (total count, averages)
   - Actual artifacts/segments/entities in main area

## Future Work

Other results pages that may need similar updates:

- `/results/embeddings` - Check if it queries ProcessingArtifact
- `/results/temporal` - May need temporal_expression artifact support
- `/results/definitions` - May need term_definition artifact support
- `/results/enhanced` - May need extracted_term artifact support

## Backward Compatibility

These changes maintain full backward compatibility:

- Old data in `TextSegment`/`ExtractedEntity` still works
- New data in `ProcessingArtifact` now works
- Can have mix of old and new data for same document
- Templates don't need any changes
