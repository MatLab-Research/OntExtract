# OntExtract Experiments & References Guide

## Overview
The new experiment interface allows you to create, manage, and run ontology-based text analysis experiments with support for reference documents.

## Features Implemented

### 1. Experiments Management (`/experiments/`)
- **Create Experiments**: Name your experiments and select documents to analyze
- **Experiment Types**:
  - **Temporal Evolution**: Analyze how concepts change over time across documents
  - **Domain Comparison**: Compare terminology usage across different domains
- **Status Tracking**: Draft, Running, Completed, Error states
- **Document Selection**: Choose multiple documents for combined analysis

### 2. References Management (`/references/`)
- **Upload Reference Documents**: Academic papers and authoritative sources
- **Metadata Support**:
  - Authors
  - Publication date
  - Journal/Publisher
  - DOI, ISBN, URL
  - Abstract
  - Full citation
- **Link to Experiments**: Include/exclude references from analysis

## How to Use

### Creating an Experiment
1. **Login** to the application at http://localhost:8080
2. Navigate to **Experiments** from the navigation menu
3. Click **"New Experiment"**
4. Enter experiment details:
   - Name your experiment
   - Select experiment type (temporal evolution or domain comparison)
   - Add configuration parameters
   - Select documents to analyze
   - Choose reference documents (optional)
5. Click **"Create Experiment"**

### Managing References
1. Navigate to **References** from the navigation menu
2. Click **"Upload Reference"**
3. Upload your reference document (PDF, DOCX, etc.)
4. Fill in metadata:
   - Authors (comma-separated)
   - Publication date
   - Journal or publisher
   - DOI/ISBN/URL
   - Abstract
   - Citation format
5. Click **"Upload"**

### Running Experiments
1. Go to your experiment from the experiments list
2. Review selected documents and references
3. Click **"Run Experiment"**
4. View results once processing is complete

### Example Use Cases

#### Temporal Evolution Analysis
- Upload documents from different time periods
- Create an experiment to track concept evolution
- Add canonical references for baseline definitions
- Run analysis to see how terminology has changed

#### Domain Comparison
- Upload documents from different fields
- Create an experiment to compare terminology
- Add authoritative references for each domain
- Run analysis to identify domain-specific language patterns

## Database Schema

### Experiments Table
- `id`: Primary key
- `name`: Experiment name
- `experiment_type`: temporal_evolution or domain_comparison
- `description`: Optional description
- `config`: JSON configuration parameters
- `status`: draft, running, completed, error
- `created_at`, `updated_at`: Timestamps
- `user_id`: Owner reference

### Document Extensions
- `document_type`: 'document' or 'reference'
- `source_metadata`: JSON field for reference metadata

### Association Tables
- `experiment_documents`: Links experiments to documents
- `experiment_references`: Links experiments to references with inclusion flags

## API Endpoints

### Experiments
- `GET /experiments/` - List all experiments
- `GET /experiments/new` - New experiment form
- `POST /experiments/create` - Create experiment
- `GET /experiments/<id>` - View experiment
- `GET /experiments/<id>/edit` - Edit form
- `POST /experiments/<id>/update` - Update experiment
- `POST /experiments/<id>/delete` - Delete experiment
- `POST /experiments/<id>/run` - Run experiment
- `GET /experiments/<id>/results` - View results

### References
- `GET /references/` - List all references
- `GET /references/upload` - Upload form
- `POST /references/upload` - Upload reference
- `GET /references/<id>` - View reference
- `GET /references/<id>/edit` - Edit form
- `POST /references/<id>/update` - Update reference
- `POST /references/<id>/delete` - Delete reference

## Navigation Links
The main navigation bar now includes:
- **Experiments** - Access experiment management
- **References** - Access reference document management
- Documents (existing)
- Processing (existing)
- Results (existing)

## Next Steps
1. Login to the application
2. Upload some documents for analysis
3. Upload reference documents for canonical definitions
4. Create your first experiment
5. Run the analysis to extract ontological insights

## Technical Notes
- PostgreSQL database with proper indexes
- Bootstrap-based responsive UI
- Dark theme for better readability
- SQLAlchemy ORM for database operations
- Flask blueprints for modular architecture
