#!/usr/bin/env python3
"""
Test script for the Temporal Analysis Service.
This script demonstrates the capabilities of the temporal analysis service
including term evolution tracking, semantic drift analysis, and narrative generation.
"""

import json
from datetime import datetime
from shared_services.temporal import TemporalAnalysisService
from shared_services.ontology.ontology_importer import OntologyImporter

# Mock document class for testing
class MockDocument:
    def __init__(self, content, year, name="Test Document"):
        self.content = content
        self.metadata = json.dumps({"year": year, "title": name})
        self.name = name
        
    def get_display_name(self):
        return self.name

def create_test_documents():
    """Create test documents with temporal evolution of terms."""
    
    documents = [
        # Early period (2000-2005)
        MockDocument(
            content="""
            An agent is defined as a person or entity that acts on behalf of another.
            In computing, an agent refers to a software program that performs tasks autonomously.
            The concept of agency involves the capacity to act independently and make choices.
            Agents interact with their environment through sensors and actuators.
            """,
            year=2000,
            name="Computing Fundamentals 2000"
        ),
        MockDocument(
            content="""
            The term agent has evolved in artificial intelligence research.
            An intelligent agent is an autonomous entity which observes and acts upon an environment.
            Agent-based systems are becoming more prevalent in distributed computing.
            Multi-agent systems involve multiple interacting intelligent agents.
            """,
            year=2003,
            name="AI Research Papers 2003"
        ),
        
        # Middle period (2006-2010)
        MockDocument(
            content="""
            Software agents are now commonly used in web services and cloud computing.
            An agent means a program that acts for a user or other program in a relationship of agency.
            Autonomous agents can learn from their environment and adapt their behavior.
            The concept of agent has expanded to include virtual assistants and chatbots.
            """,
            year=2008,
            name="Web Services Guide 2008"
        ),
        MockDocument(
            content="""
            Intelligent agents are fundamental to modern AI systems.
            An agent is characterized by autonomy, social ability, reactivity, and pro-activeness.
            Agent architectures have evolved from simple reactive systems to complex cognitive models.
            The agent paradigm is central to understanding distributed artificial intelligence.
            """,
            year=2010,
            name="AI Textbook 2010"
        ),
        
        # Recent period (2011-2020)
        MockDocument(
            content="""
            AI agents are now integrated into everyday applications and services.
            An agent refers to any system that can perceive its environment and take actions.
            Machine learning agents can improve their performance through experience.
            Conversational agents and virtual assistants have become mainstream technology.
            """,
            year=2015,
            name="Modern AI Applications 2015"
        ),
        MockDocument(
            content="""
            The concept of agent has expanded to include large language models and AI assistants.
            Agents in modern AI are characterized by their ability to understand natural language.
            Autonomous agents are now capable of complex reasoning and decision-making.
            The agent paradigm continues to evolve with advances in deep learning.
            """,
            year=2020,
            name="AI Trends 2020"
        )
    ]
    
    return documents

def test_temporal_analysis():
    """Test the temporal analysis service with sample documents."""
    
    print("=" * 80)
    print("TEMPORAL ANALYSIS SERVICE TEST")
    print("=" * 80)
    
    # Create test documents
    documents = create_test_documents()
    print(f"\nCreated {len(documents)} test documents spanning 2000-2020")
    
    # Initialize services
    ontology_importer = OntologyImporter()
    temporal_service = TemporalAnalysisService(ontology_importer)
    
    # Define time periods for analysis
    time_periods = [2000, 2005, 2010, 2015, 2020]
    print(f"Time periods for analysis: {time_periods}")
    
    # Test term: "agent"
    term = "agent"
    print(f"\nAnalyzing term: '{term}'")
    print("-" * 40)
    
    # Extract temporal data
    print("\n1. EXTRACTING TEMPORAL DATA...")
    temporal_data = temporal_service.extract_temporal_data(documents, term, time_periods)
    
    for period in time_periods:
        period_data = temporal_data.get(str(period), {})
        print(f"\n{period}:")
        print(f"  - Evolution Status: {period_data.get('evolution', 'N/A')}")
        print(f"  - Frequency: {period_data.get('frequency', 0)}")
        print(f"  - Document Count: {period_data.get('document_count', 0)}")
        print(f"  - Definition Count: {period_data.get('definition_count', 0)}")
        
        if period_data.get('definition'):
            print(f"  - Definition: {period_data['definition'][:100]}...")
        
        if period_data.get('semantic_field'):
            print(f"  - Related Terms: {', '.join(period_data['semantic_field'][:5])}")
    
    # Analyze semantic drift
    print("\n2. ANALYZING SEMANTIC DRIFT...")
    drift_analysis = temporal_service.analyze_semantic_drift(documents, term, time_periods)
    
    print(f"\nAverage Drift: {drift_analysis.get('average_drift', 0):.2%}")
    print(f"Total Drift: {drift_analysis.get('total_drift', 0):.2f}")
    
    if drift_analysis.get('stable_terms'):
        print(f"Stable Terms Throughout: {', '.join(drift_analysis['stable_terms'][:5])}")
    
    # Show period-by-period changes
    if drift_analysis.get('periods'):
        print("\nPeriod-by-Period Changes:")
        for period_range, data in drift_analysis['periods'].items():
            print(f"\n  {period_range}:")
            print(f"    - Drift Score: {data['drift_score']:.2%}")
            print(f"    - Similarity: {data['similarity']:.2%}")
            if data.get('new_terms'):
                print(f"    - New Terms: {', '.join(data['new_terms'][:3])}")
            if data.get('lost_terms'):
                print(f"    - Lost Terms: {', '.join(data['lost_terms'][:3])}")
    
    # Generate evolution narrative
    print("\n3. GENERATING EVOLUTION NARRATIVE...")
    narrative = temporal_service.generate_evolution_narrative(temporal_data, term, time_periods)
    print("\n" + narrative)
    
    # Test with another term
    print("\n" + "=" * 80)
    print("TESTING ANOTHER TERM: 'intelligence'")
    print("=" * 80)
    
    term2 = "intelligence"
    temporal_data2 = temporal_service.extract_temporal_data(documents, term2, time_periods)
    
    for period in time_periods:
        period_data = temporal_data2.get(str(period), {})
        if period_data.get('frequency', 0) > 0:
            print(f"\n{period}: Found {period_data['frequency']} occurrences")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)

if __name__ == "__main__":
    try:
        test_temporal_analysis()
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()
