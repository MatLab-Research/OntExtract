#!/usr/bin/env python3
"""
Generate a clear, high-quality PROV-O provenance diagram for OntExtract
Based on the workflow described in the OntExtract Short Paper
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
from matplotlib.patches import ConnectionPatch
import matplotlib.lines as mlines

# Create figure with high DPI for clarity
fig, ax = plt.subplots(1, 1, figsize=(16, 22), dpi=150)
ax.set_xlim(0, 10)
ax.set_ylim(0, 14)
ax.axis('off')

# Define colors for different PROV-O elements
colors = {
    'agent': '#FFE6CC',      # Light orange for agents
    'activity': '#E6F3FF',   # Light blue for activities  
    'entity': '#E6FFE6',     # Light green for entities
    'arrow': '#666666',      # Gray for arrows
}

# Helper function to draw rounded rectangles
def draw_rounded_box(ax, x, y, width, height, text, color, style='solid'):
    """Draw a rounded rectangle with text"""
    box = FancyBboxPatch(
        (x - width/2, y - height/2), width, height,
        boxstyle="round,pad=0.05",
        facecolor=color,
        edgecolor='black',
        linewidth=2,
        linestyle=style
    )
    ax.add_patch(box)
    
    # Add text with better formatting
    ax.text(x, y, text, 
            ha='center', va='center',
            fontsize=11, fontweight='bold',
            wrap=True)
    return box

# Helper function to draw ellipses
def draw_ellipse(ax, x, y, width, height, text, color):
    """Draw an ellipse with text"""
    from matplotlib.patches import Ellipse
    ellipse = Ellipse((x, y), width, height,
                      facecolor=color,
                      edgecolor='black',
                      linewidth=2)
    ax.add_patch(ellipse)
    
    ax.text(x, y, text,
            ha='center', va='center',
            fontsize=11, fontweight='bold')
    return ellipse

# Helper function to draw arrows with labels
def draw_arrow(ax, x1, y1, x2, y2, label='', curve=0):
    """Draw an arrow with optional label"""
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        connectionstyle=f"arc3,rad={curve}",
        arrowstyle='->,head_width=0.3,head_length=0.4',
        color=colors['arrow'],
        linewidth=1.5,
        zorder=1
    )
    ax.add_patch(arrow)
    
    if label:
        # Calculate midpoint for label
        mid_x = (x1 + x2) / 2 + curve * 0.5
        mid_y = (y1 + y2) / 2
        ax.text(mid_x, mid_y, label,
                ha='center', va='bottom',
                fontsize=9, style='italic',
                bbox=dict(boxstyle="round,pad=0.2", 
                         facecolor='white', 
                         edgecolor='none',
                         alpha=0.8))
    return arrow

# === TOP SECTION: AGENTS ===
ax.text(5, 13.5, 'PROV-O Provenance Workflow for OntExtract', 
        ha='center', va='center',
        fontsize=16, fontweight='bold')

# Draw agents
draw_ellipse(ax, 2, 12, 1.8, 0.8, 'Human\nResearcher', colors['agent'])
draw_ellipse(ax, 5, 12, 1.8, 0.8, 'LLM\nOrchestrator', colors['agent'])
draw_ellipse(ax, 8, 12, 1.8, 0.8, 'Analysis\nTools', colors['agent'])

# Label for agents section
ax.text(0.5, 12, 'prov:Agent', 
        ha='center', va='center',
        fontsize=10, style='italic', fontweight='bold')

# === MIDDLE SECTION: ACTIVITIES ===

# Document Upload Activity
draw_rounded_box(ax, 2, 10, 1.8, 0.8, 'Document\nUpload', colors['activity'])

# Tool Selection Activity (central)
draw_rounded_box(ax, 5, 10, 1.8, 0.8, 'Tool Selection\nDecision', colors['activity'])

# Processing Activities
draw_rounded_box(ax, 8, 10.5, 1.6, 0.7, 'Segmentation', colors['activity'])
draw_rounded_box(ax, 8, 9.5, 1.6, 0.7, 'Entity\nExtraction', colors['activity'])
draw_rounded_box(ax, 8, 8.5, 1.6, 0.7, 'Embedding\nGeneration', colors['activity'])

# Label for activities section
ax.text(0.5, 9.5, 'prov:Activity', 
        ha='center', va='center',
        fontsize=10, style='italic', fontweight='bold')

# === BOTTOM SECTION: ENTITIES ===

# Original Document
draw_rounded_box(ax, 2, 7, 1.8, 0.8, 'Original\nDocument', colors['entity'])

# Document Versions
draw_rounded_box(ax, 2, 5.5, 1.8, 0.8, 'Document\nVersion 1', colors['entity'])
draw_rounded_box(ax, 2, 4, 1.8, 0.8, 'Document\nVersion 2', colors['entity'])

# Processing Outputs
draw_rounded_box(ax, 5, 6.5, 1.8, 0.8, 'Text\nSegments', colors['entity'])
draw_rounded_box(ax, 5, 5, 1.8, 0.8, 'Extracted\nEntities', colors['entity'])
draw_rounded_box(ax, 5, 3.5, 1.8, 0.8, 'Embeddings', colors['entity'])

# Analytical Results
draw_rounded_box(ax, 8, 5.5, 1.8, 0.8, 'Semantic\nMeasurements', colors['entity'])
draw_rounded_box(ax, 8, 4, 1.8, 0.8, 'Drift Analysis\nResults', colors['entity'])

# Label for entities section
ax.text(0.5, 5, 'prov:Entity', 
        ha='center', va='center',
        fontsize=10, style='italic', fontweight='bold')

# === DRAW RELATIONSHIPS ===

# wasAssociatedWith relationships
draw_arrow(ax, 2, 11.5, 2, 10.5, 'wasAssociatedWith', 0)
draw_arrow(ax, 5, 11.5, 5, 10.5, 'wasAssociatedWith', 0)
draw_arrow(ax, 8, 11.5, 8, 11, 'wasAssociatedWith', 0)

# LLM orchestrates tool selection
draw_arrow(ax, 5, 9.5, 7.2, 10.5, 'selects', 0.2)
draw_arrow(ax, 5, 9.5, 7.2, 9.5, 'selects', 0.2)
draw_arrow(ax, 5, 9.5, 7.2, 8.5, 'selects', 0.2)

# Document upload generates original
draw_arrow(ax, 2, 9.5, 2, 7.5, 'wasGeneratedBy', 0)

# Original derives versions
draw_arrow(ax, 2, 6.5, 2, 6, 'wasDerivedFrom', 0)
draw_arrow(ax, 2, 5, 2, 4.5, 'wasDerivedFrom', 0)

# Processing activities generate outputs
draw_arrow(ax, 7.2, 10.3, 5.8, 6.8, 'wasGeneratedBy', -0.3)
draw_arrow(ax, 7.2, 9.3, 5.8, 5.3, 'wasGeneratedBy', -0.3)
draw_arrow(ax, 7.2, 8.3, 5.8, 3.8, 'wasGeneratedBy', -0.3)

# Outputs derive analytical results
draw_arrow(ax, 5.8, 6.3, 7.2, 5.7, 'wasDerivedFrom', 0.2)
draw_arrow(ax, 5.8, 4.8, 7.2, 4.2, 'wasDerivedFrom', 0.2)

# Human feedback loop
draw_arrow(ax, 2.8, 5.5, 3.5, 10, 'feedback', -0.8)

# === ADD LEGEND ===
legend_y = 2
legend_items = [
    ('Agent', colors['agent'], 'ellipse'),
    ('Activity', colors['activity'], 'box'),
    ('Entity', colors['entity'], 'box'),
]

ax.text(5, 2.5, 'PROV-O Elements', 
        ha='center', va='center',
        fontsize=12, fontweight='bold')

legend_x = 3
for item, color, shape in legend_items:
    if shape == 'ellipse':
        draw_ellipse(ax, legend_x, legend_y, 0.8, 0.4, '', color)
    else:
        draw_rounded_box(ax, legend_x, legend_y, 0.8, 0.4, '', color)
    ax.text(legend_x + 0.6, legend_y, item,
            ha='left', va='center',
            fontsize=10)
    legend_x += 1.5

# Add relationship legend
ax.text(5, 1.3, 'Relationships:', 
        ha='center', va='center',
        fontsize=11, fontweight='bold')
ax.text(5, 0.9, 'wasAssociatedWith, wasGeneratedBy, wasDerivedFrom', 
        ha='center', va='center',
        fontsize=10, style='italic')

# === ADD DESCRIPTIONS ===
descriptions = [
    "• LLM Orchestrator coordinates tool selection based on document characteristics",
    "• Every processing operation creates versioned outputs with provenance records",
    "• Human feedback influences analytical decisions through the workflow",
    "• All relationships implement PROV-O vocabulary for reproducibility"
]

desc_y = 0.4
for desc in descriptions:
    ax.text(5, desc_y, desc,
            ha='center', va='center',
            fontsize=9.5)
    desc_y -= 0.25

# Save the figure
output_path = '/home/chris/onto/OntExtract/docs/prov_o_clear.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight', 
            facecolor='white', edgecolor='none')
plt.close()

print(f"High-quality PROV-O diagram saved to: {output_path}")
print(f"Image dimensions preserved with improved clarity")
