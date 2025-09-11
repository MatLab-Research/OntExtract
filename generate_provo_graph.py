#!/usr/bin/env python3
"""
Generate PROV-O Graph Visualization for OntExtract Paper
Creates a provenance graph showing document processing workflow
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import matplotlib.lines as mlines
import networkx as nx
from datetime import datetime

def create_provo_graph():
    """Create a PROV-O compliant provenance graph for OntExtract"""
    
    # Create figure and axis
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')
    
    # Define colors for different PROV-O types
    entity_color = '#FFE5B4'  # Peach for entities
    activity_color = '#B4D7FF'  # Light blue for activities  
    agent_color = '#D4F1D4'  # Light green for agents
    
    # === ENTITIES (Document Versions) ===
    # Original document
    doc_orig = FancyBboxPatch((0.5, 3), 1.8, 0.8,
                              boxstyle="round,pad=0.05",
                              facecolor=entity_color,
                              edgecolor='black',
                              linewidth=2)
    ax.add_patch(doc_orig)
    ax.text(1.4, 3.4, 'Original Document\n(PDF Upload)', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    # Processed Version 1 - LangExtract
    doc_v1 = FancyBboxPatch((3.5, 4.5), 1.8, 0.8,
                            boxstyle="round,pad=0.05",
                            facecolor=entity_color,
                            edgecolor='black',
                            linewidth=1.5)
    ax.add_patch(doc_v1)
    ax.text(4.4, 4.9, 'Version 1\n(LangExtract)', 
            ha='center', va='center', fontsize=9)
    
    # Processed Version 2 - Semantic Segmentation
    doc_v2 = FancyBboxPatch((3.5, 3), 1.8, 0.8,
                            boxstyle="round,pad=0.05",
                            facecolor=entity_color,
                            edgecolor='black',
                            linewidth=1.5)
    ax.add_patch(doc_v2)
    ax.text(4.4, 3.4, 'Version 2\n(Semantic Segments)', 
            ha='center', va='center', fontsize=9)
    
    # Processed Version 3 - Entity Extraction
    doc_v3 = FancyBboxPatch((3.5, 1.5), 1.8, 0.8,
                            boxstyle="round,pad=0.05",
                            facecolor=entity_color,
                            edgecolor='black',
                            linewidth=1.5)
    ax.add_patch(doc_v3)
    ax.text(4.4, 1.9, 'Version 3\n(Named Entities)', 
            ha='center', va='center', fontsize=9)
    
    # Final Analysis Output
    doc_final = FancyBboxPatch((7.5, 3), 1.8, 0.8,
                               boxstyle="round,pad=0.05",
                               facecolor=entity_color,
                               edgecolor='black',
                               linewidth=2)
    ax.add_patch(doc_final)
    ax.text(8.4, 3.4, 'Drift Analysis\n(Synthesized)', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    # === ACTIVITIES ===
    # Activity 1: Two-stage extraction
    act1 = Circle((2.5, 4.9), 0.3, facecolor=activity_color, edgecolor='black')
    ax.add_patch(act1)
    ax.text(2.5, 4.9, 'Extract', ha='center', va='center', fontsize=8)
    
    # Activity 2: Segmentation
    act2 = Circle((2.5, 3.4), 0.3, facecolor=activity_color, edgecolor='black')
    ax.add_patch(act2)
    ax.text(2.5, 3.4, 'Segment', ha='center', va='center', fontsize=8)
    
    # Activity 3: NER
    act3 = Circle((2.5, 1.9), 0.3, facecolor=activity_color, edgecolor='black')
    ax.add_patch(act3)
    ax.text(2.5, 1.9, 'NER', ha='center', va='center', fontsize=8)
    
    # Activity 4: Synthesis
    act4 = Circle((6.2, 3.4), 0.3, facecolor=activity_color, edgecolor='black')
    ax.add_patch(act4)
    ax.text(6.2, 3.4, 'Synthesize', ha='center', va='center', fontsize=8)
    
    # === AGENTS ===
    # Agent 1: Gemini LLM
    agent1 = FancyBboxPatch((1.8, 5.3), 1.3, 0.5,
                            boxstyle="round,pad=0.03",
                            facecolor=agent_color,
                            edgecolor='black',
                            linewidth=1)
    ax.add_patch(agent1)
    ax.text(2.45, 5.55, 'Gemini LLM', ha='center', va='center', fontsize=8)
    
    # Agent 2: spaCy
    agent2 = FancyBboxPatch((1.8, 1.2), 1.3, 0.5,
                            boxstyle="round,pad=0.03",
                            facecolor=agent_color,
                            edgecolor='black',
                            linewidth=1)
    ax.add_patch(agent2)
    ax.text(2.45, 1.45, 'spaCy NLP', ha='center', va='center', fontsize=8)
    
    # Agent 3: Orchestrator
    agent3 = FancyBboxPatch((5.5, 4.7), 1.3, 0.5,
                            boxstyle="round,pad=0.03",
                            facecolor=agent_color,
                            edgecolor='black',
                            linewidth=1)
    ax.add_patch(agent3)
    ax.text(6.15, 4.95, 'LLM Orchestrator', ha='center', va='center', fontsize=8)
    
    # === RELATIONSHIPS (Arrows) ===
    # wasDerivedFrom relationships
    arrow1 = FancyArrowPatch((2.3, 3.4), (3.5, 4.7),
                            connectionstyle="arc3,rad=.2",
                            arrowstyle='->,head_width=0.15,head_length=0.15',
                            color='blue', linewidth=1.5)
    ax.add_patch(arrow1)
    
    arrow2 = FancyArrowPatch((2.3, 3.4), (3.5, 3.4),
                            connectionstyle="arc3,rad=0",
                            arrowstyle='->,head_width=0.15,head_length=0.15',
                            color='blue', linewidth=1.5)
    ax.add_patch(arrow2)
    
    arrow3 = FancyArrowPatch((2.3, 3.4), (3.5, 2.1),
                            connectionstyle="arc3,rad=-.2",
                            arrowstyle='->,head_width=0.15,head_length=0.15',
                            color='blue', linewidth=1.5)
    ax.add_patch(arrow3)
    
    # wasGeneratedBy relationships
    arrow4 = FancyArrowPatch((2.8, 4.9), (3.5, 4.9),
                            connectionstyle="arc3,rad=0",
                            arrowstyle='->,head_width=0.15,head_length=0.15',
                            color='red', linewidth=1.2)
    ax.add_patch(arrow4)
    
    arrow5 = FancyArrowPatch((2.8, 3.4), (3.5, 3.4),
                            connectionstyle="arc3,rad=0",
                            arrowstyle='->,head_width=0.15,head_length=0.15',
                            color='red', linewidth=1.2)
    ax.add_patch(arrow5)
    
    arrow6 = FancyArrowPatch((2.8, 1.9), (3.5, 1.9),
                            connectionstyle="arc3,rad=0",
                            arrowstyle='->,head_width=0.15,head_length=0.15',
                            color='red', linewidth=1.2)
    ax.add_patch(arrow6)
    
    # wasAssociatedWith relationships (agents to activities)
    arrow7 = FancyArrowPatch((2.45, 5.3), (2.5, 5.2),
                            connectionstyle="arc3,rad=0",
                            arrowstyle='->,head_width=0.1,head_length=0.1',
                            color='green', linewidth=1, linestyle='dashed')
    ax.add_patch(arrow7)
    
    arrow8 = FancyArrowPatch((2.45, 1.7), (2.5, 1.6),
                            connectionstyle="arc3,rad=0",
                            arrowstyle='->,head_width=0.1,head_length=0.1',
                            color='green', linewidth=1, linestyle='dashed')
    ax.add_patch(arrow8)
    
    # Multi-source synthesis
    arrow9 = FancyArrowPatch((5.3, 4.7), (5.9, 3.5),
                            connectionstyle="arc3,rad=.3",
                            arrowstyle='->,head_width=0.15,head_length=0.15',
                            color='blue', linewidth=1.5)
    ax.add_patch(arrow9)
    
    arrow10 = FancyArrowPatch((5.3, 3.4), (5.9, 3.4),
                             connectionstyle="arc3,rad=0",
                             arrowstyle='->,head_width=0.15,head_length=0.15',
                             color='blue', linewidth=1.5)
    ax.add_patch(arrow10)
    
    arrow11 = FancyArrowPatch((5.3, 2.1), (5.9, 3.3),
                             connectionstyle="arc3,rad=-.3",
                             arrowstyle='->,head_width=0.15,head_length=0.15',
                             color='blue', linewidth=1.5)
    ax.add_patch(arrow11)
    
    arrow12 = FancyArrowPatch((6.5, 3.4), (7.5, 3.4),
                             connectionstyle="arc3,rad=0",
                             arrowstyle='->,head_width=0.15,head_length=0.15',
                             color='red', linewidth=1.2)
    ax.add_patch(arrow12)
    
    arrow13 = FancyArrowPatch((6.15, 4.7), (6.2, 3.7),
                             connectionstyle="arc3,rad=0",
                             arrowstyle='->,head_width=0.1,head_length=0.1',
                             color='green', linewidth=1, linestyle='dashed')
    ax.add_patch(arrow13)
    
    # Add legend
    entity_patch = mpatches.Patch(color=entity_color, label='prov:Entity')
    activity_patch = mpatches.Patch(color=activity_color, label='prov:Activity')
    agent_patch = mpatches.Patch(color=agent_color, label='prov:Agent')
    
    derived_line = mlines.Line2D([], [], color='blue', linewidth=1.5,
                                label='wasDerivedFrom', marker='>', markersize=5)
    generated_line = mlines.Line2D([], [], color='red', linewidth=1.2,
                                  label='wasGeneratedBy', marker='>', markersize=5)
    associated_line = mlines.Line2D([], [], color='green', linewidth=1,
                                   label='wasAssociatedWith', marker='>', markersize=5,
                                   linestyle='dashed')
    
    ax.legend(handles=[entity_patch, activity_patch, agent_patch,
                      derived_line, generated_line, associated_line],
             loc='lower center', ncol=3, frameon=True, 
             bbox_to_anchor=(0.5, -0.05), fontsize=9)
    
    # Add title
    ax.text(5, 5.7, 'PROV-O Provenance Graph: OntExtract Document Processing Workflow',
           ha='center', va='center', fontsize=11, fontweight='bold')
    
    # Add annotations
    ax.text(1.4, 2.5, 'Upload', ha='center', va='center', fontsize=7, style='italic')
    ax.text(4.4, 0.9, 'Multiple processing\npathways', ha='center', va='center', 
           fontsize=7, style='italic')
    ax.text(8.4, 2.5, 'Synthesized\noutput', ha='center', va='center', 
           fontsize=7, style='italic')
    
    plt.tight_layout()
    return fig

def main():
    """Generate and save the PROV-O graph"""
    print("Generating PROV-O provenance graph...")
    
    fig = create_provo_graph()
    
    # Save in multiple formats
    fig.savefig('OntExtract/provo_graph.png', dpi=300, bbox_inches='tight')
    fig.savefig('OntExtract/provo_graph.pdf', bbox_inches='tight')
    fig.savefig('OntExtract/provo_graph.svg', bbox_inches='tight')
    
    print("✅ PROV-O graph saved as:")
    print("   - OntExtract/provo_graph.png (for viewing)")
    print("   - OntExtract/provo_graph.pdf (for paper inclusion)")
    print("   - OntExtract/provo_graph.svg (for editing)")
    
    # Close the plot to free memory (don't try to show in headless environment)
    plt.close()

if __name__ == "__main__":
    main()
