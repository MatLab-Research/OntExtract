# Temporal Evolution Experiments Guide

## Overview

The Temporal Evolution experiment type in OntExtract allows you to track how terms and concepts evolve over time across your document corpus. This feature provides sophisticated analysis of semantic drift, frequency changes, and contextual evolution of terminology.

## Features

### 1. Advanced Temporal Analysis Service
- **Term Evolution Tracking**: Monitor how definitions and usage of terms change over time periods
- **Semantic Drift Detection**: Analyze how the semantic field around terms shifts across periods
- **Frequency Analysis**: Track term usage frequency trends over time
- **Context Evolution**: Understand how the contexts in which terms appear change
- **Narrative Generation**: Automatically generate human-readable evolution narratives

### 2. Interactive Term Management Interface
- **Timeline Visualization**: Visual representation of terms across time periods
- **Period-by-Period Analysis**: Detailed breakdown of term usage in each time period
- **Evolution Status Indicators**: Visual cues showing term evolution (emerging, developing, established, etc.)
- **Semantic Field Display**: Related terms that co-occur with your target terms

## How to Use

### Step 1: Create a Temporal Evolution Experiment

1. Navigate to **Experiments → New Experiment**
2. Select **Temporal Evolution** as the experiment type
3. Configure your time periods:
   - **Start Year**: Beginning of your analysis period
   - **End Year**: End of your analysis period
   - **Period Length**: How to divide the time range (e.g., 5-year periods)
4. Select documents and references to analyze
5. Click **Create Experiment**

### Step 2: Manage Terms

After creating the experiment, you'll be redirected to the Temporal Term Manager:

1. **Add Terms**: Click "Add New Term to Track" and enter terms you want to analyze
2. **Fetch Historical Data**: For each term, click "Fetch Historical Data" to extract temporal information
3. **Analyze Evolution**: Click "Analyze Evolution" to get detailed semantic drift analysis
4. **Save Progress**: Your work is automatically saved, but you can manually save at any time

### Step 3: Understanding the Results

#### Evolution Status
- **Absent**: Term not found in this period
- **Emerging**: Low frequency (< 10 occurrences)
- **Developing**: Moderate frequency (10-50 occurrences)
- **Evolving**: Multiple definitions found, indicating semantic change
- **Established**: High frequency with stable usage

#### Semantic Drift Metrics
- **Drift Score**: Percentage change in semantic field between periods (0-100%)
- **Similarity**: How similar the term's context is between periods
- **New Terms**: Terms that start appearing with your target term
- **Lost Terms**: Terms that stop appearing with your target term
- **Stable Terms**: Terms consistently associated across all periods

### Step 4: Running Analysis

Once you've configured your terms:

1. Click **Continue to Analysis** to proceed
2. The system will perform comprehensive temporal analysis
3. View results including:
   - Evolution narratives for each term
   - Semantic drift visualizations
   - Frequency trend charts
   - Period-by-period comparisons

## Advanced Features

### Document Metadata Requirements

For best results, ensure your documents include temporal metadata:

```json
{
  "year": 2020,
  "publication_date": "2020-03-15",
  "title": "Document Title"
}
```

The system will attempt to extract dates from:
1. Document metadata fields (year, publication_year, date, published)
2. Document content (looks for year patterns like "2020")

### Ontology Integration

The temporal analysis service integrates with PROV-O ontology mappings to provide:
- Standardized term classifications
- Cross-domain concept alignment
- Provenance tracking for term evolution

### API Access

You can also access temporal analysis programmatically:

```python
from shared_services.temporal import TemporalAnalysisService
from shared_services.ontology.ontology_importer import OntologyImporter

# Initialize services
ontology_importer = OntologyImporter()
temporal_service = TemporalAnalysisService(ontology_importer)

# Analyze term evolution
temporal_data = temporal_service.extract_temporal_data(
    documents=document_list,
    term="artificial intelligence",
    time_periods=[2000, 2005, 2010, 2015, 2020]
)

# Analyze semantic drift
drift_analysis = temporal_service.analyze_semantic_drift(
    documents=document_list,
    term="artificial intelligence",
    time_periods=[2000, 2005, 2010, 2015, 2020]
)

# Generate narrative
narrative = temporal_service.generate_evolution_narrative(
    temporal_data=temporal_data,
    term="artificial intelligence",
    time_periods=[2000, 2005, 2010, 2015, 2020]
)
```

## Use Cases

### Academic Research
- Track evolution of scientific terminology
- Analyze paradigm shifts in academic fields
- Study emergence of new concepts

### Industry Analysis
- Monitor technology trend evolution
- Track industry jargon changes
- Analyze market terminology shifts

### Historical Linguistics
- Study language evolution
- Track semantic changes in words
- Analyze cultural concept evolution

### Policy and Legal Studies
- Track legal terminology evolution
- Monitor policy language changes
- Analyze regulatory concept development

## Tips for Best Results

1. **Document Coverage**: Ensure you have documents spanning your entire time range
2. **Consistent Metadata**: Use consistent date formats in document metadata
3. **Term Selection**: Choose terms that are likely to appear across multiple periods
4. **Period Length**: Select period lengths that match your domain (e.g., 5 years for technology, 10 years for legal)
5. **Reference Documents**: Include reference materials (dictionaries, glossaries) from different periods

## Troubleshooting

### No Data Found for Period
- Check if documents exist for that time period
- Verify document metadata includes date information
- Consider expanding the time window for sparse data

### High Semantic Drift Scores
- This indicates significant change in term usage
- Review the new/lost terms to understand the shift
- Consider if external factors (technology changes, events) explain the drift

### Low Frequency Counts
- Term may be too specific or technical
- Try broader or more common terms
- Check for spelling variations or synonyms

## Integration with Other Features

### Domain Comparison
- Compare how terms evolved differently across domains
- Identify domain-specific evolution patterns

### Ontology Mapping
- Map evolving terms to stable ontology concepts
- Track how ontology alignments change over time

### Reference Integration
- Use historical dictionaries and references
- Compare formal definitions with usage evolution

## Future Enhancements

Planned improvements include:
- Visual timeline graphs
- Automated period detection
- Multi-term correlation analysis
- Export to temporal knowledge graphs
- Integration with external temporal databases

## Support

For questions or issues with temporal evolution experiments:
1. Check this documentation
2. Review the test examples in `test_temporal_analysis.py`
3. Contact support with experiment ID and error details
