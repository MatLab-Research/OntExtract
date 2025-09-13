#!/usr/bin/env python3
"""
Generate a simplified, clear PROV-O provenance diagram for OntExtract
Focused on the core workflow with legend-based relationships
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Ellipse
import matplotlib.lines as mlines

# Create figure with high DPI for clarity
fig, ax = plt.subplots(1, 1, figsize=(14, 18), dpi=150)
ax.set_xlim(0, 10)
ax.set_ylim(0, 13)
ax.axis('off')

# Define colors for different PROV-O elements
colors = {
    'agent': '#FFD4A3',      # Warm orange for agents
    'activity': '#B3D9FF',   # Light blue for activities  
    'entity': '#C8E6C9',     # Light green for entities
    'arrow1': '#2196F3',     # Blue for wasAssociatedWith
    'arrow2': '#4CAF50',     # Green for wasGeneratedBy
    'arrow3': '#FF9800',     # Orange for wasDerivedFrom
}

# Helper function to draw rounded rectangles
def draw_rounded_box(ax, x, y, width, height, text, color, style='solid'):
    """Draw a rounded rectangle with text"""
    box = FancyBboxPatch(
        (x - width/2, y - height/2), width, height,
        boxstyle="round,pad=0.08",
        facecolor=color,
        edgecolor='#333333',
        linewidth=3,
        linestyle=style
    )
    ax.add_patch(box)
    
    # Add text with better formatting
    ax.text(x, y, text, 
            ha='center', va='center',
            fontsize=16, fontweight='normal',
            wrap=True)
    return box

# Helper function to draw ellipses
def draw_ellipse(ax, x, y, width, height, text, color):
    """Draw an ellipse with text"""
    ellipse = Ellipse((x, y), width, height,
                      facecolor=color,
                      edgecolor='#333333',
                      linewidth=2)
    ax.add_patch(ellipse)
    
    ax.text(x, y, text,
            ha='center', va='center',
            fontsize=16, fontweight='normal')
    return ellipse

# Helper function to draw arrows without labels
def draw_arrow(ax, x1, y1, x2, y2, color, style='solid'):
    """Draw a straight arrow with specific color and visible head"""
    # Use matplotlib's annotate for better arrow heads
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', 
                               color=color, 
                               lw=4,
                               shrinkA=10, shrinkB=10,
                               mutation_scale=30))
    return None

# No title needed

# === MAIN WORKFLOW - SIMPLIFIED ===

# Top layer - Agents (moved up)
draw_ellipse(ax, 2.5, 11.5, 2, 0.9, 'Human\nResearcher', colors['agent'])
draw_ellipse(ax, 5, 11.5, 2, 0.9, 'LLM\nOrchestrator', colors['agent'])
draw_ellipse(ax, 7.5, 11.5, 2, 0.9, 'Analysis\nTools', colors['agent'])

# Middle layer - Core Activities
draw_rounded_box(ax, 3.5, 9, 2, 0.9, 'Document\nUpload', colors['activity'])
draw_rounded_box(ax, 6.5, 9, 2, 0.9, 'Processing\nActivities', colors['activity'])

# Bottom layer - Key Entities  
draw_rounded_box(ax, 2, 6.5, 1.8, 0.9, 'Original\nDocument', colors['entity'])
draw_rounded_box(ax, 5, 6.5, 1.8, 0.9, 'Document\nVersions', colors['entity'])
draw_rounded_box(ax, 8, 6.5, 1.8, 0.9, 'Analytical\nOutputs', colors['entity'])

# Additional processing outputs
draw_rounded_box(ax, 3.5, 4.5, 1.6, 0.8, 'Text\nSegments', colors['entity'])
draw_rounded_box(ax, 6.5, 4.5, 1.6, 0.8, 'Embeddings', colors['entity'])

# === SIMPLIFIED RELATIONSHIPS ===

# wasAssociatedWith (blue arrows) - connecting agents to activities
# Human Researcher -> Document Upload
draw_arrow(ax, 2.5, 11.0, 3.5, 9.45, colors['arrow1'])
# LLM Orchestrator -> Document Upload (for orchestration)
draw_arrow(ax, 4.8, 11.0, 3.7, 9.45, colors['arrow1'])
# LLM Orchestrator -> Processing Activities (tool selection)
draw_arrow(ax, 5.2, 11.0, 6.3, 9.45, colors['arrow1'])
# Analysis Tools -> Processing Activities
draw_arrow(ax, 7.5, 11.0, 6.5, 9.45, colors['arrow1'])

# wasGeneratedBy (green arrows) - activities generate entities
draw_arrow(ax, 3.5, 8.55, 2, 6.95, colors['arrow2'])
draw_arrow(ax, 6.5, 8.55, 5, 6.95, colors['arrow2'])
draw_arrow(ax, 6.5, 8.55, 8, 6.95, colors['arrow2'])

# wasDerivedFrom (orange arrows) - entities derive from other entities
draw_arrow(ax, 2.8, 6.05, 3.5, 4.9, colors['arrow3'])
draw_arrow(ax, 4.8, 6.05, 3.7, 4.9, colors['arrow3'])
draw_arrow(ax, 5.2, 6.05, 6.3, 4.9, colors['arrow3'])
draw_arrow(ax, 7.2, 6.05, 6.5, 4.9, colors['arrow3'])

# === LEGEND SECTION - CENTERED ===

# Title for legend
ax.text(5, 2.8, 'Legend', 
        ha='center', va='center',
        fontsize=18, fontweight='normal')

# PROV-O Elements
element_y = 2.3
ax.text(5, element_y, 'PROV-O Elements:', 
        ha='center', va='center',
        fontsize=16, fontweight='normal')

# Draw element examples - centered with more spacing
element_items = [
    ('prov:Agent', colors['agent'], 'ellipse'),
    ('prov:Activity', colors['activity'], 'box'),
    ('prov:Entity', colors['entity'], 'box'),
]

element_x_start = 2.5
element_y = 1.8
for i, (label, color, shape) in enumerate(element_items):
    element_x = element_x_start + i * 2.8  # Increased spacing
    if shape == 'ellipse':
        draw_ellipse(ax, element_x, element_y, 0.8, 0.4, '', color)
    else:
        draw_rounded_box(ax, element_x, element_y, 0.8, 0.4, '', color)
    ax.text(element_x + 0.9, element_y, label,  # Moved text further right
            ha='left', va='center',
            fontsize=14, fontweight='normal')

# Relationships - centered
rel_y = 1.2
ax.text(5, rel_y, 'Relationships:', 
        ha='center', va='center',
        fontsize=16, fontweight='normal')

# Draw relationship arrows with labels - centered with proper spacing
rel_items = [
    ('wasAssociatedWith', colors['arrow1']),
    ('wasGeneratedBy', colors['arrow2']),
    ('wasDerivedFrom', colors['arrow3']),
]

rel_x_start = 2.0
rel_y = 0.8
for i, (label, color) in enumerate(rel_items):
    rel_x = rel_x_start + i * 2.8  # Increased spacing to match elements above
    # Draw small arrow sample
    ax.arrow(rel_x - 0.3, rel_y, 0.5, 0, 
             head_width=0.08, head_length=0.08,
             fc=color, ec=color, linewidth=2)
    ax.text(rel_x + 0.35, rel_y, label,
            ha='left', va='center',
            fontsize=14, fontweight='normal')

# No bottom text needed

# Save the figure as both PDF and PNG
output_path_pdf = '/home/chris/onto/OntExtract/docs/prov_o_simple.pdf'
output_path_png = '/home/chris/onto/OntExtract/docs/prov_o_simple.png'

# Save as PDF (vector format - perfect at any size)
plt.savefig(output_path_pdf, format='pdf', bbox_inches='tight', 
            facecolor='white', edgecolor='none')

# Also save as PNG for preview
plt.savefig(output_path_png, dpi=150, bbox_inches='tight', 
            facecolor='white', edgecolor='none')

plt.close()

print(f"Simplified PROV-O diagram saved as PDF: {output_path_pdf}")
print(f"Also saved as PNG: {output_path_png}")
print(f"PDF version will scale perfectly at any size")
