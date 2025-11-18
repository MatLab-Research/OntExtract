# Hierarchical Embeddings Implementation

Hierarchical embedding system that creates both document-level and segment-level embeddings for flexible analysis.

## Architecture

### Two-Tier Embedding Structure

**Document-Level Embeddings** (artifact_index = -1):
- Created for every document (always)
- Embeds first 2000 characters of document
- Used for: Document similarity, clustering, high-level comparison
- Stored with `embedding_level: 'document'` in both content and metadata

**Segment-Level Embeddings** (artifact_index = 0, 1, 2, ...):
- Created when segments exist (optional)
- One embedding per segment (up to 2000 chars each)
- Used for: Fine-grained semantic search, passage retrieval
- Stored with `embedding_level: 'segment'` in both content and metadata
- Links back to parent via `document_embedding_id` in metadata

## Implementation

### Backend: pipeline_service.py (lines 557-672)

```python
def _process_embeddings(
    self,
    processing_op: ExperimentDocumentProcessing,
    index_entry: DocumentProcessingIndex,
    exp_doc: ExperimentDocument,
    processing_method: str
):
    """
    Process embeddings for a document - hierarchical approach

    Creates:
    1. Document-level embedding (always) - for document similarity/clustering
    2. Segment-level embeddings (if segments exist) - for fine-grained search
    """
    # STEP 1: Always create document-level embedding
    text_to_embed = content[:2000]
    doc_embedding_result = embedding_service.generate_embeddings(text_to_embed, processing_method)

    doc_embedding_artifact = ProcessingArtifact(
        processing_id=processing_op.id,
        document_id=exp_doc.document_id,
        artifact_type='embedding_vector',
        artifact_index=-1  # -1 indicates document-level embedding
    )
    doc_embedding_artifact.set_content({
        'text': text_to_embed,
        'vector': doc_embedding_result['vector'],
        'model': doc_embedding_result['model'],
        'embedding_level': 'document'
    })
    doc_embedding_artifact.set_metadata({
        'dimensions': doc_embedding_result['dimensions'],
        'method': processing_method,
        'embedding_level': 'document'
    })
    db.session.add(doc_embedding_artifact)
    db.session.flush()  # Get ID for linking

    document_embedding_id = str(doc_embedding_artifact.id)

    # STEP 2: Create segment-level embeddings if segments exist
    existing_segments = ProcessingArtifact.query.filter(
        ProcessingArtifact.document_id == exp_doc.document_id,
        ProcessingArtifact.artifact_type == 'text_segment'
    ).order_by(ProcessingArtifact.artifact_index).all()

    if existing_segments:
        for idx, segment_artifact in enumerate(existing_segments):
            segment_data = segment_artifact.get_content()
            text_to_embed = segment_data.get('text', '')[:2000]

            embedding_result = embedding_service.generate_embeddings(text_to_embed, processing_method)

            embedding_artifact = ProcessingArtifact(
                processing_id=processing_op.id,
                document_id=exp_doc.document_id,
                artifact_type='embedding_vector',
                artifact_index=idx
            )
            embedding_artifact.set_content({
                'text': text_to_embed,
                'vector': embedding_result['vector'],
                'model': embedding_result['model'],
                'segment_index': idx,
                'embedding_level': 'segment'
            })
            embedding_artifact.set_metadata({
                'dimensions': embedding_result['dimensions'],
                'method': processing_method,
                'source_segment_id': str(segment_artifact.id),
                'document_embedding_id': document_embedding_id,  # Link to parent
                'embedding_level': 'segment'
            })
            db.session.add(embedding_artifact)

    # Completion summary
    processing_op.mark_completed({
        'total_embeddings': embeddings_created,
        'document_embeddings': 1,
        'segment_embeddings': segment_embeddings_created,
        'note': f'Hierarchical: 1 document + {segment_embeddings_created} segment embeddings'
    })
```

### Results Display: embeddings_results.html

Updated to show two separate sections:

**Document-Level Embeddings Section** (Blue Header):
- Shows all document-level embeddings (artifact_index = -1)
- Displays: Model, dimensions, text length, embedded text preview
- Shows first 10 dimensions of actual vector values

**Segment-Level Embeddings Section** (Teal Header):
- Shows segment-level embeddings (artifact_index >= 0)
- Displays: Segment number, text preview, vector preview
- Limited to first 10 segments with overflow indication
- Each segment linked to its parent document embedding

### Route Updates: pipeline.py (lines 1489-1514)

```python
# Get document-level embeddings (artifact_index = -1)
document_embeddings = ProcessingArtifact.query.filter(
    ProcessingArtifact.document_id == document.id,
    ProcessingArtifact.artifact_type == 'embedding_vector',
    ProcessingArtifact.artifact_index == -1
).all()

# Get segment-level embeddings (artifact_index >= 0)
segment_embeddings = ProcessingArtifact.query.filter(
    ProcessingArtifact.document_id == document.id,
    ProcessingArtifact.artifact_type == 'embedding_vector',
    ProcessingArtifact.artifact_index >= 0
).order_by(ProcessingArtifact.artifact_index).all()

return render_template('processing/embeddings_results.html',
                     document=document,
                     jobs=jobs,
                     embedding_count=len(document_embeddings) + len(segment_embeddings),
                     document_embeddings=document_embeddings,
                     segment_embeddings=segment_embeddings)
```

## User Experience

### Workflow

1. **Upload Document** - Any document with text content
2. **Optional: Segment Document** - Run paragraph or sentence segmentation
3. **Generate Embeddings** - Run "Local Embeddings" (or other method)
4. **View Results** - Navigate to embeddings results page

### Results Page Display

**Without Segments**:
- 1 document-level embedding shown
- Blue "Document-Level Embeddings" card
- Shows model, dimensions, text preview, vector values

**With Segments**:
- 1 document-level embedding (blue card)
- N segment-level embeddings (teal card)
- Each section shows actual vector data
- Segment embeddings limited to first 10 for performance

### Example Output

**Document-Level:**
```
Model: sentence-transformers/all-MiniLM-L6-v2
Dimensions: 384
Text Length: 2000 chars (from 5432 total)
Text: This is the beginning of the document...
Vector (first 10 dimensions): [0.1234, -0.5678, 0.9012, ...]
```

**Segment-Level:**
```
Segment 1 (450 chars)
Text: This is the first paragraph of the document...
Vector: [0.2345, -0.6789, 0.0123, ...]

Segment 2 (392 chars)
Text: The second paragraph continues the discussion...
Vector: [0.3456, -0.7890, 0.1234, ...]

...

Showing first 10 of 42 segment embeddings
```

## Database Schema

### ProcessingArtifact Table

**artifact_index**:
- -1 = Document-level embedding
- 0, 1, 2, ... = Segment-level embeddings (matches segment index)

**content_json** (for embedding_vector artifacts):
```json
{
  "text": "Text that was embedded",
  "vector": [0.1234, -0.5678, ...],  // Full embedding vector
  "model": "sentence-transformers/all-MiniLM-L6-v2",
  "embedding_level": "document" or "segment",
  "segment_index": 0  // Only for segment-level
}
```

**metadata_json**:
```json
{
  "dimensions": 384,
  "method": "local",
  "chunk_size": 2000,
  "tokens_used": "N/A",
  "embedding_level": "document" or "segment",
  "original_length": 5432,  // Only for document-level
  "source_segment_id": "123",  // Only for segment-level
  "document_embedding_id": "456"  // Only for segment-level
}
```

## Use Cases

### Document Similarity
Query: "Find documents similar to this one"
- Use document-level embeddings only
- Fast comparison across entire corpus
- Good for clustering, deduplication, recommendation

### Passage Retrieval
Query: "Find specific paragraphs about X"
- Use segment-level embeddings
- Fine-grained semantic search
- Returns specific passages, not entire documents

### Hybrid Search
Query: "Find relevant documents and highlight key passages"
1. Filter documents using document-level embeddings
2. Search within filtered documents using segment-level embeddings
3. Return documents with relevant passages highlighted

## Benefits

**Efficiency**:
- Can skip segment embeddings for document-level tasks
- Don't need to embed entire long documents for similarity

**Flexibility**:
- Choose embedding granularity based on use case
- Support both coarse and fine-grained search

**Clarity**:
- Clear parent-child relationships
- Easy to understand what was embedded and why

**Scalability**:
- Document embeddings grow linearly with document count
- Segment embeddings only created when needed
- Can delete segment embeddings to save space while keeping document embeddings

## Future Enhancements

Possible improvements:

- Vector search using pgvector for similarity queries
- Hierarchical search (document-level filter → segment-level retrieval)
- Embedding caching (reuse document embedding across multiple experiments)
- Dimension reduction visualization (t-SNE/UMAP of embeddings)
- Similarity matrix heatmap for multiple documents
