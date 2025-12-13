# How to Create Anchor Terms

This guide explains how to create and manage anchor terms for tracking semantic evolution.

## What Are Anchor Terms?

Anchor terms are key concepts to be tracked across historical periods. They serve as current/modern reference points or "mile markers" for semantic change analysis.

**Examples:**
- "agent" in AI/philosophy contexts
- "machine" in industrial/computing contexts
- "intelligence" across cognitive science literature

## Creating an Anchor Term

OntExtract offers two ways to create anchor terms: using **Connected Services** (recommended) or **Manual Entry**.

### Method 1: Connected Services (Recommended)

Use authoritative lexicographic sources to establish well-documented anchor terms.

![Add Term - Connected Services](../assets/images/screenshots/term-add-connected-services-content.png)

1. Navigate to **Library → Terms** and click **Add New Anchor Term**
2. Select a service to search:

| Service | Description |
|---------|-------------|
| **Merriam-Webster Dictionary** | Authoritative American English definitions |
| **Merriam-Webster Thesaurus** | Synonyms and antonyms for context anchoring |
| **Oxford English Dictionary** | Authoritative English language definitions |
| **WordNet** | Lexical database with semantic relationships |

3. Enter the search term when prompted
4. Browse the results and click **Use This Definition**
5. The form auto-populates with:
   - Term text
   - Meaning description
   - Context anchors (related terms)
   - Source citation
6. Add a **Research Domain** if desired
7. Click **Create Term**

### Method 2: Manual Entry

For terms not found in dictionaries or from custom sources:

1. Click the **Manual Entry** tab
2. Fill in the term details:

| Field | Description | Example |
|-------|-------------|---------|
| **Term Text** | The word or phrase to track | "agent" |
| **Source Type** | Type of reference source | Corpus, Dictionary, Standard |
| **Meaning Description** | Current baseline meaning | "An entity that acts autonomously..." |
| **Context Anchors** | Related terms (comma-separated) | "autonomous, actor, entity" |
| **Corpus Source** | Lexicographic source name | "Merriam-Webster" |
| **Source Citation** | Full citation for provenance | "Merriam-Webster Dictionary, 2024" |
| **Research Domain** | Subject area | "Artificial Intelligence" |
| **Notes** | Additional context | "Focus on autonomous agent concept" |

3. Click **Create Term**

### Context Anchors

Context anchors are related terms that help define the semantic space around an anchor term. Options include:

- Letting services auto-populate them from definitions
- Clicking the **Thesaurus** button to find synonyms
- Entering them manually (comma-separated)

## Term Versions

Anchor terms support temporal versioning to capture meaning changes over time. Versions are created through:

- **OED Timeline** - Select historical waypoints showing when new senses emerged
- **Manual versioning** - Add versions with different temporal periods

!!! info "Planned Feature"
    OED Timeline visualization for selecting historical waypoints is under consideration for a future release.

## Best Practices

### Choosing Terms

- **Specificity**: Choose terms specific enough to track meaningfully
- **Frequency**: Select terms that appear across the document corpus
- **Evolution potential**: Pick terms likely to show semantic change

### Term Naming

- Use the canonical/base form (e.g., "agent" not "agents")
- Be consistent with capitalization
- Include phrases if tracking multi-word concepts ("artificial intelligence")

### Domain Classification

Assign appropriate domains to help organize terms:
- Philosophy
- Computer Science
- Artificial Intelligence
- Cognitive Science
- (Custom domains as needed)

## Viewing Term Details

Click any term to see:

- **Basic Information** - Term text, meaning description, research domain
- **Source Information** - Corpus source and citation
- **Context Anchors** - Related terms for semantic anchoring
- **Temporal Versions** - Historical meaning snapshots (if created)
- **Associated Experiments** - Where the term is used

![Term Detail Page](../assets/images/screenshots/term-detail-content.png)

## Editing Terms

1. Navigate to the term detail page
2. Click **Edit Term**
3. Modify fields as needed
4. Click **Save Changes**

> Note: Editing a term affects all experiments using it.

## Deleting Terms

To delete a term:

1. Navigate to **Library → Terms**
2. Find the term in the list
3. Click the trash icon on the right side of the row
4. Confirm the deletion in the modal

> **Warning**: Deleting a term removes all temporal versions and associated data permanently.

## Term Search

Find existing terms using:

- **Search box** - Search by term text
- **Domain filter** - Filter by research domain

## Related Guides

- [Upload Documents](upload-documents.md)
- [Process Documents](document-processing.md)
- [Create Temporal Experiment](create-temporal-experiment.md)
