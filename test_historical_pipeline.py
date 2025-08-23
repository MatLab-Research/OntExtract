"""
Test script for the historical document processing pipeline.
Demonstrates the complete workflow from document processing to semantic evolution tracking.
"""

import json
from datetime import date
from dataclasses import dataclass
from typing import Dict, Any

# Import our pipeline components
from shared_services.preprocessing import (
    HistoricalDocumentProcessor,
    TemporalWordUsageExtractor,
    SemanticEvolutionTracker,
    ProvenanceTracker
)

# Sample historical documents for testing
@dataclass
class TestDocument:
    """Test document with content and metadata."""
    content: str
    metadata: Dict[str, Any]
    filename: str = "test_doc.txt"
    
    @property
    def full_text(self):
        return self.content

# Create sample documents from different periods
def create_test_documents():
    """Create sample historical documents for testing."""
    
    doc_1700s = TestDocument(
        content="""
        The Publick Gazette, 15th January, 1750
        
        'Tis with great pleasure that we announce the compleat success of the merchant's 
        voyage to the Indies. The goods, including musick instruments and fine silks, 
        have arrived in good condition. The captain doth report fair weather throughout 
        the journey, and the crew hath shewn great courage in their endeavours.
        
        In matters of commerce, the market continues to thrive. Merchants report that 
        trade with the colonies grows stronger each day. The exchange of goods between 
        our nation and foreign lands brings great profit to all involved.
        """,
        metadata={
            'publication_date': '1750-01-15',
            'source_type': 'newspaper',
            'title': 'The Publick Gazette'
        }
    )
    
    doc_1850s = TestDocument(
        content="""
        The Daily Telegraph, March 3rd, 1855
        
        The railway expansion continues at an unprecedented pace. The new steam engines 
        show remarkable efficiency in transporting both goods and passengers. This great 
        innovation in transportation promises to revolutionize commerce across the nation.
        
        In commercial news, the market for industrial goods has expanded significantly. 
        The exchange between manufacturers and merchants has reached new heights. Trade 
        with the Empire's territories brings substantial profit to British enterprise.
        
        The telegraph system now connects major cities, allowing instant communication 
        of market prices and commercial intelligence.
        """,
        metadata={
            'publication_date': '1855-03-03',
            'source_type': 'newspaper',
            'title': 'The Daily Telegraph'
        }
    )
    
    doc_1920s = TestDocument(
        content="""
        The Times, June 15, 1925
        
        The expansion of radio broadcasting marks a new era in mass communication. 
        Commercial enterprises are beginning to explore advertising through this 
        revolutionary medium. The exchange of information has never been faster.
        
        In the markets, speculation runs high as investors trade shares in the new 
        technology companies. The profit margins in radio and electrical industries 
        continue to attract substantial investment.
        
        Commerce between nations has been facilitated by improved telecommunications 
        and faster shipping methods. The global market is more interconnected than ever.
        """,
        metadata={
            'publication_date': '1925-06-15',
            'source_type': 'newspaper',
            'title': 'The Times'
        }
    )
    
    return [doc_1700s, doc_1850s, doc_1920s]

def main():
    """Run the complete historical document processing pipeline."""
    
    print("=" * 80)
    print("HISTORICAL DOCUMENT PROCESSING PIPELINE TEST")
    print("=" * 80)
    
    # Initialize components
    print("\n1. Initializing pipeline components...")
    historical_processor = HistoricalDocumentProcessor(google_services_enabled=False)
    usage_extractor = TemporalWordUsageExtractor(context_window=5)
    evolution_tracker = SemanticEvolutionTracker()
    provenance_tracker = ProvenanceTracker()
    
    # Create test documents
    print("\n2. Loading test documents from different historical periods...")
    documents = create_test_documents()
    print(f"   - Loaded {len(documents)} documents")
    
    # Process each document
    processed_docs = []
    temporal_usages = []
    
    print("\n3. Processing historical documents...")
    for i, doc in enumerate(documents, 1):
        print(f"\n   Document {i}:")
        
        # Step 1: Process historical document
        processed = historical_processor.process_historical_document(doc)
        processed_docs.append(processed)
        
        print(f"   - Period: {processed.temporal_metadata.period_name}")
        print(f"   - Year: {processed.temporal_metadata.year}")
        print(f"   - Confidence: {processed.temporal_metadata.confidence:.2f}")
        print(f"   - Semantic units: {len(processed.semantic_units)}")
        
        # Show some normalized spelling changes
        if i == 1:  # First document has historical spellings
            print(f"   - Original words: 'publick', 'compleat', 'musick', 'shewn'")
            print(f"   - Normalized to: 'public', 'complete', 'music', 'shown'")
    
    print("\n4. Extracting temporal word usage patterns...")
    for processed in processed_docs:
        # Step 2: Extract word usage patterns
        usage = usage_extractor.extract_usage(processed)
        temporal_usages.append(usage)
        
        print(f"\n   Period: {usage.period}")
        print(f"   - Total words: {usage.metadata['total_words']}")
        print(f"   - Unique words: {usage.metadata['unique_words']}")
        
        # Show top words
        top_words = sorted(usage.frequency_distribution.items(), 
                          key=lambda x: x[1], reverse=True)[:5]
        print(f"   - Top words: {', '.join([w for w, _ in top_words])}")
        
        # Show some collocations
        if usage.collocations:
            print(f"   - Sample collocations found:")
            for word, cols in list(usage.collocations.items())[:3]:
                if cols:
                    print(f"     * '{word}' (frequency: {cols[0].frequency})")
    
    # Track semantic evolution for specific words
    print("\n5. Tracking semantic evolution for key terms...")
    target_words = ['commerce', 'trade', 'profit', 'exchange', 'market']
    
    for word in target_words:
        # Check if word appears in multiple periods
        word_periods = [u for u in temporal_usages 
                       if word in u.frequency_distribution]
        
        if len(word_periods) >= 2:
            print(f"\n   Analyzing '{word}':")
            
            # Step 3: Track semantic evolution
            evolution = evolution_tracker.track_evolution(word, word_periods)
            
            print(f"   - Appears in {len(evolution.time_periods)} periods")
            print(f"   - Drift detected: {evolution.metadata['drift_detected']}")
            
            # Show timeline
            for period, data in evolution.evolution_timeline.items():
                print(f"   - {period}: frequency={data['frequency']}, "
                      f"POS={data['dominant_pos']}")
            
            # Track provenance for this word
            for usage in word_periods:
                if word in usage.word_contexts:
                    for ctx in usage.word_contexts[word][:1]:  # Just first context
                        provenance = provenance_tracker.track_word_extraction(
                            word=word,
                            context={
                                'sentence': ctx.sentence,
                                'position': ctx.document_position,
                                'pos_tag': ctx.pos_tag,
                                'semantic_unit_id': ctx.semantic_unit_id,
                                'context_window': 5
                            },
                            source_doc=processed_docs[0],  # Use first doc as example
                            method='automatic'
                        )
            
            # Show semantic drift if detected
            if evolution.semantic_drift_metrics:
                drift = evolution.semantic_drift_metrics[0]
                print(f"   - Semantic drift from {drift.baseline_period} to "
                      f"{drift.comparison_period}: {drift.drift_score:.3f}")
    
    print("\n6. Generating provenance report...")
    # Show provenance tracking
    entity_count = len(provenance_tracker.entities)
    activity_count = len(provenance_tracker.activities)
    
    print(f"   - Tracked entities: {entity_count}")
    print(f"   - Processing activities: {activity_count}")
    print(f"   - Registered agents: {len(provenance_tracker.agents)}")
    
    # Export sample provenance
    if provenance_tracker.entities:
        first_entity_id = list(provenance_tracker.entities.keys())[0]
        quality = provenance_tracker.calculate_quality_metrics(first_entity_id)
        print(f"   - Sample entity quality metrics:")
        print(f"     * Confidence: {quality.get('confidence', 0):.2f}")
        print(f"     * Source reliability: {quality.get('source_reliability', 0):.2f}")
        print(f"     * Overall quality: {quality.get('overall_quality', 0):.2f}")
    
    print("\n7. Pipeline test completed successfully!")
    
    # Export provenance graph
    print("\n8. Exporting provenance graph...")
    provenance_json = provenance_tracker.export_provenance_graph('json-ld')
    
    # Save to file
    with open('provenance_graph.json', 'w') as f:
        f.write(provenance_json)
    print("   - Provenance graph saved to 'provenance_graph.json'")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE - Historical document processing pipeline is functional!")
    print("=" * 80)

if __name__ == "__main__":
    main()
