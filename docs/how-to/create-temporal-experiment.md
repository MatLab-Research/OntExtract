# How to Create a Temporal Evolution Experiment

Complete guide for setting up experiments to track semantic change across historical periods.

## Overview

Temporal evolution experiments analyze how term meanings change over time by combining historical documents with anchor terms across defined time periods.

## Prerequisites

Before creating an experiment:

- [ ] OntExtract installed and running
- [ ] User account created and logged in
- [ ] Historical documents ready for upload (spanning the target time range)

## Step 1: Create Anchor Terms

First, create anchor terms to define the concepts to be tracked:

1. Navigate to **Library → Terms**
2. Click **Add New Anchor Term**
3. Enter:
   - **Term text** - The word/phrase to track (e.g., "agent")
   - **Domain** - Subject area
   - **Notes** - Research context

See [Create Anchor Terms](create-anchor-terms.md) for detailed instructions.

## Step 2: Create the Experiment

### Navigate to Experiments

1. Click **Experiments** in the main navigation
2. Click **New Experiment**

![Create New Experiment](../assets/images/screenshots/experiment-new-content.png)

### Fill in Experiment Details

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | Descriptive experiment name | "Agent Temporal Evolution 1910-2024" |
| **Description** | Research goals and scope | "Tracking the semantic evolution of 'agent' in AI literature" |
| **Start Year** | Beginning of time range | 1910 |
| **End Year** | End of time range | 2024 |
| **Status** | Experiment state | draft, active, completed |

### Temporal Periods

OntExtract automatically generates temporal periods based on the date range. Options include:

- **Auto-generate** - System creates periods based on document dates
- **Manual** - Define custom period boundaries

Click **Create Experiment** to save.

## Manage Temporal Terms

After creating a temporal evolution experiment, access the **Manage Temporal Terms** feature to configure the timeline in detail.

### Accessing the Manager

1. Go to the experiment's detail page
2. Click **Manage Temporal Terms** button

### Timeline Configuration

The Temporal Term Manager provides two ways to set up periods:

| Method | Description |
|--------|-------------|
| **Auto-generate from documents** | Creates artifact markers for each document's publication year |
| **Manual Entry** | Manually specify time period boundaries |

### Adding Semantic Events

The timeline can be annotated with semantic change events:

1. Click **Add Event** in the Periods & Events section
2. Select the event type (e.g., amelioration, pejoration, drift)
3. Specify the time range (from/to periods)
4. Add a description of the semantic shift
5. Link related documents as evidence

### Period Cards

The timeline displays period cards showing:

- **Year** - The period's date marker
- **Source badge** - ARTIFACT (auto-generated) or MANUAL
- **Documents** - Papers associated with that period
- **Events** - Semantic change events spanning periods

Period boundaries are color-coded:

- **Green (START)** - Beginning of a defined period
- **Red (END)** - End of a defined period

### Saving Configuration

Click **Save Configuration** to persist the temporal setup before proceeding to analysis.

## Step 3: Add Documents

### Upload Documents

1. Go to the experiment's **Document Pipeline**
2. Click **Add Documents**
3. Upload files with publication dates
4. Documents are automatically assigned to periods based on publication date

### Document Requirements

For meaningful temporal analysis:

- **Multiple documents per period** - More data improves accuracy
- **Date coverage** - Documents spanning the full time range
- **Consistent domain** - Documents from related subject areas

See [Upload Documents](upload-documents.md) for detailed upload instructions.

## Step 4: Process Documents

### LLM Text Cleanup (Recommended)

For scanned or OCR'd documents:

1. In **Document Pipeline**, click the broom icon for each document
2. Review suggested corrections
3. Accept or modify changes
4. Save cleaned version

### Run Processing Operations

From the **Document Pipeline** or individual document pages:

1. **Segmentation** - Split into paragraphs/sentences
2. **Embeddings** - Generate vector representations
3. **Entity Extraction** - Identify named entities

Use **Run Local Tools** for batch processing without API costs.

## Step 5: Run Analysis

### LLM Orchestration (Advanced)

For AI-assisted analysis:

1. Go to the experiment's **Document Pipeline**
2. Click **Start LLM Orchestration**
3. Review the generated strategy
4. Approve or modify the approach
5. Execute the analysis

### Manual Analysis

Explore results through:

- **Timeline View** - Visual evolution across periods
- **Document Comparison** - Side-by-side period analysis
- **Term Context** - Source passages for each period

## Step 6: Review Results

### Timeline Visualization

The timeline shows:
- Term usage frequency per period
- Semantic change events
- Context snippets from source documents

### Export Options

Export analysis results:

- **CSV** - Tabular data for spreadsheets
- **JSON** - Structured results for further processing

## Troubleshooting

### No Documents in Period

- Check document publication dates
- Verify period boundaries
- Upload additional documents for sparse periods

### Processing Errors

- Ensure documents have text content
- Run LLM cleanup on problematic documents
- Check API keys for external services

### Missing Analysis Results

- Verify all processing steps completed
- Check anchor term associations
- Review experiment status

## Related Guides

- [Upload Documents](upload-documents.md)
- [Process Documents](document-processing.md)
- [Create Anchor Terms](create-anchor-terms.md)
