# OntExtract Claude Agents

This directory contains specialized Claude Code agents for OntExtract development and maintenance tasks.

---

## Available Agents

### 1. documentation-writer

**Purpose:** Create and update user documentation following academic writing standards

**Use when:**
- New features need documentation
- Existing features changed (UI updates, workflow modifications)
- Screenshots need updating
- Regular documentation maintenance

**Invocation:**
```
I need to document [feature/workflow]. Please use the documentation-writer agent to create the documentation.
```

**Example:**
```
I need to document the new Quick Add Reference feature in the experiment creation workflow.
Please use the documentation-writer agent to create the documentation.
```

**What it does:**
- Creates/updates documentation pages from templates
- Captures screenshots with Flameshot
- Validates academic writing style compliance
- Builds and tests documentation
- Commits changes to git

**References:**
- [documentation-writer.md](documentation-writer.md) - Complete agent specification
- [docs/WRITING_STYLE_CHECKLIST.md](../../docs/WRITING_STYLE_CHECKLIST.md) - Style guide
- [docs/CONTENT_TEMPLATES.md](../../docs/CONTENT_TEMPLATES.md) - Page templates

---

### 2. temporal-evolution-experiment

**Purpose:** Create repeatable temporal evolution experiments for demos and testing

**Use when:**
- Creating demo experiments for conferences
- Testing temporal analysis workflows
- Preparing example experiments for documentation

**Invocation:**
```
Please use the temporal-evolution-experiment agent to create a temporal evolution experiment for [term] from [start year] to [end year].
```

**What it does:**
- Guides through 8-phase experiment creation
- Analyzes documents and creates periods
- Adds semantic events with ontology citations
- Generates timeline visualizations
- Exports provenance metadata

**References:**
- [temporal-evolution-experiment.md](temporal-evolution-experiment.md) - Complete agent specification

---

### 3. upload-agent-documents

**Purpose:** Upload document collections with metadata for temporal experiments

**Use when:**
- Preparing source documents for temporal evolution experiments
- Batch uploading historical documents
- Setting up demo experiment data

**Invocation:**
```
Please use the upload-agent-documents agent to upload documents for [experiment topic].
```

**What it does:**
- Uploads PDFs with full metadata
- Sets publication dates and author information
- Handles book chapters vs full books
- Creates reproducible upload scripts

**References:**
- [upload-agent-documents.md](upload-agent-documents.md) - Complete agent specification

---

## How to Use Agents

### Method 1: Direct Invocation

Simply ask Claude Code to use the agent in your message:

```
Please use the [agent-name] agent to [task description].
```

### Method 2: Reference Agent File

If you need to customize the workflow:

```
Follow the [agent-name] agent workflow, but skip Phase 3 and focus on Phase 5.
```

### Method 3: Provide Context

Give Claude Code context before invoking:

```
I've just added a new timeline export feature to OntExtract.
The feature allows users to export timelines as PDF or PNG files.
The UI has a new "Export" button in the timeline view.

Please use the documentation-writer agent to document this feature.
```

---

## Agent Workflow Pattern

All OntExtract agents follow a similar structure:

1. **Prerequisites:** What must be in place before running
2. **Phase 1: Assessment** - Understand scope and requirements
3. **Phase 2-N: Execution** - Perform the work in structured phases
4. **Final Phase: Review & Commit** - Verify quality and version control
5. **Troubleshooting:** Common issues and solutions
6. **References:** Related documentation and resources

---

## Creating New Agents

To create a new agent for OntExtract:

1. **Copy template structure** from existing agent
2. **Define clear purpose** and use cases
3. **Break work into phases** (3-7 phases typical)
4. **Include verification steps** in each phase
5. **Add troubleshooting section** for common issues
6. **Reference related documentation**
7. **Update this README** with agent description

**Template Structure:**
```markdown
# [Agent Name]

**Purpose:** [One-line description]

## Agent Overview
[What the agent does, when to use it]

## Prerequisites
[What must be ready before running]

## Agent Workflow

### Phase 1: [Phase Name]
#### Task 1.1: [Task Name]
[Instructions]
**Output:** [Deliverable]

### Phase N: Review and Finalize
[Quality checks and commit]

## Common [Agent-Specific] Tasks
[Frequent use cases]

## Troubleshooting
[Common issues and solutions]

## References
[Related docs]

## Agent Invocation
[How to call this agent]
```

---

## Tips for Working with Agents

### Provide Context

Agents work better when you provide relevant context:

**Good:**
```
I've modified the timeline view to show period colors differently.
The START cards now have a green left border and END cards have a red right border.
The screenshots in docs/user-guide/experiments/temporal-evolution/timeline-view.md
are now outdated.

Please use the documentation-writer agent to update this documentation.
```

**Less Good:**
```
Update the timeline docs.
```

### Specify Scope

Tell the agent what level of detail you need:

**Good:**
```
Please use the documentation-writer agent to create a quick reference guide
for the timeline view. Focus on the visual elements and hover interactions.
Keep it to 1-2 pages maximum.
```

**Less Good:**
```
Document the timeline.
```

### Ask for Specific Outputs

Be clear about deliverables:

**Good:**
```
Please use the documentation-writer agent to:
1. Update the timeline-view.md page with new screenshots
2. Add a troubleshooting section for the "Timeline not rendering" issue
3. Update the how-to guide to reference the new export feature

I need these for the JCDL demo next week.
```

---

## Agent Maintenance

### When to Update Agents

Update agent files when:
- OntExtract architecture changes significantly
- Agent workflow proves inefficient or incomplete
- New tools or processes become available
- User feedback reveals missing steps

### How to Update Agents

1. **Read agent file** to understand current workflow
2. **Identify gaps or issues** based on experience
3. **Update relevant sections** (usually phases or troubleshooting)
4. **Test updated workflow** by running agent
5. **Update version number** at bottom of file
6. **Commit changes** with "docs: update [agent-name] agent for [reason]"

---

## Directory Structure

```
.claude/agents/
├── README.md                              # This file
├── documentation-writer.md                # Documentation maintenance agent
├── temporal-evolution-experiment.md       # Demo experiment creation agent
└── upload-agent-documents.md             # Document upload agent
```

---

## Related Documentation

**OntExtract Documentation Planning:**
- [docs/DOCUMENTATION_PLAN.md](../../docs/DOCUMENTATION_PLAN.md)
- [docs/DOCUMENTATION_QUICK_START.md](../../docs/DOCUMENTATION_QUICK_START.md)
- [docs/CONTENT_TEMPLATES.md](../../docs/CONTENT_TEMPLATES.md)
- [docs/WRITING_STYLE_CHECKLIST.md](../../docs/WRITING_STYLE_CHECKLIST.md)

**OntExtract Development:**
- [PROGRESS.md](../../PROGRESS.md) - Session history and current status
- [QUICK_REFERENCE.md](../../QUICK_REFERENCE.md) - Commands and API endpoints

**Claude Code:**
- Claude Code Agents SDK documentation
- .claude/agents/ pattern best practices

---

**Last Updated:** 2025-11-23
