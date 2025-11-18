#!/usr/bin/env python3
"""
Test script for all implemented processing tools.

Tests each tool with sample document text to verify functionality.
"""

from app.services.processing_tools import DocumentProcessor


def test_all_tools():
    """Test all processing tools with sample text"""

    # Sample document text for testing
    sample_text = """
    Natural Language Processing (NLP) is defined as a field of artificial intelligence
    that focuses on the interaction between computers and human language. In the 1950s,
    early researchers like Alan Turing explored machine understanding of language.

    Machine learning has revolutionized NLP because it enables computers to learn patterns
    from data. This development led to significant improvements in language understanding.
    If we can process natural language effectively, then we can build better AI systems.

    The field evolved rapidly during the late 20th century and continues to advance today.
    Modern NLP systems use neural networks, also known as deep learning models, to achieve
    state-of-the-art performance. These systems can now understand context and meaning
    with remarkable accuracy.
    """

    print("=" * 80)
    print("TESTING ALL PROCESSING TOOLS")
    print("=" * 80)

    # Initialize processor
    processor = DocumentProcessor(user_id=1, experiment_id=1)

    # Test 1: Segment Paragraph
    print("\n1. Testing segment_paragraph...")
    result = processor.segment_paragraph(sample_text)
    print(f"   Status: {result.status}")
    print(f"   Paragraphs found: {result.metadata.get('count', 0)}")
    if result.status == "success":
        print(f"   ✅ PASS - Found {len(result.data)} paragraphs")
    else:
        print(f"   ❌ FAIL - {result.metadata.get('error', 'Unknown error')}")

    # Test 2: Segment Sentence
    print("\n2. Testing segment_sentence...")
    result = processor.segment_sentence(sample_text)
    print(f"   Status: {result.status}")
    print(f"   Sentences found: {result.metadata.get('count', 0)}")
    if result.status == "success":
        print(f"   ✅ PASS - Found {len(result.data)} sentences")
    else:
        print(f"   ❌ FAIL - {result.metadata.get('error', 'Unknown error')}")

    # Test 3: Extract Entities (spaCy)
    print("\n3. Testing extract_entities_spacy...")
    result = processor.extract_entities_spacy(sample_text)
    print(f"   Status: {result.status}")
    if result.status == "success":
        entity_types = result.metadata.get('entity_types', {})
        print(f"   ✅ PASS - Found {result.metadata.get('total_entities', 0)} entities")
        print(f"   Entity types: {entity_types}")
        # Show first 5 entities
        if result.data:
            print(f"   Sample entities:")
            for entity in result.data[:5]:
                print(f"     - {entity['entity']} ({entity['type']})")
    else:
        print(f"   ❌ FAIL - {result.metadata.get('error', 'Unknown error')}")

    # Test 4: Extract Temporal
    print("\n4. Testing extract_temporal...")
    result = processor.extract_temporal(sample_text)
    print(f"   Status: {result.status}")
    if result.status == "success":
        print(f"   ✅ PASS - Found {result.metadata.get('total_expressions', 0)} temporal expressions")
        expression_types = result.metadata.get('expression_types', {})
        print(f"   Expression types: {expression_types}")
        # Show first 5 expressions
        if result.data:
            print(f"   Sample expressions:")
            for expr in result.data[:5]:
                print(f"     - {expr['text']} ({expr['type']}) -> {expr.get('normalized', 'N/A')}")
    else:
        print(f"   ❌ FAIL - {result.metadata.get('error', 'Unknown error')}")

    # Test 5: Extract Causal
    print("\n5. Testing extract_causal...")
    result = processor.extract_causal(sample_text)
    print(f"   Status: {result.status}")
    if result.status == "success":
        print(f"   ✅ PASS - Found {result.metadata.get('total_relations', 0)} causal relations")
        relation_types = result.metadata.get('relation_types', {})
        print(f"   Relation types: {relation_types}")
        # Show first 3 relations
        if result.data:
            print(f"   Sample relations:")
            for rel in result.data[:3]:
                print(f"     - Cause: {rel['cause'][:50]}...")
                print(f"       Effect: {rel['effect'][:50]}...")
                print(f"       Marker: {rel['marker']} ({rel['type']})")
    else:
        print(f"   ❌ FAIL - {result.metadata.get('error', 'Unknown error')}")

    # Test 6: Extract Definitions
    print("\n6. Testing extract_definitions...")
    result = processor.extract_definitions(sample_text)
    print(f"   Status: {result.status}")
    if result.status == "success":
        print(f"   ✅ PASS - Found {result.metadata.get('total_definitions', 0)} definitions")
        pattern_types = result.metadata.get('pattern_types', {})
        print(f"   Pattern types: {pattern_types}")
        # Show first 3 definitions
        if result.data:
            print(f"   Sample definitions:")
            for defn in result.data[:3]:
                print(f"     - Term: {defn['term']}")
                print(f"       Definition: {defn['definition'][:60]}...")
                print(f"       Pattern: {defn['pattern']}")
    else:
        print(f"   ⚠️  WARNING - {result.metadata.get('error', result.metadata.get('warning', 'Unknown'))}")

    # Test 7: Period-Aware Embedding
    print("\n7. Testing period_aware_embedding...")
    result = processor.period_aware_embedding(sample_text)
    print(f"   Status: {result.status}")
    if result.status == "success":
        print(f"   ✅ PASS - Generated embedding")
        print(f"   Period detected: {result.metadata.get('period', 'N/A')}")
        print(f"   Period confidence: {result.metadata.get('period_confidence', 0):.2f}")
        print(f"   Model: {result.metadata.get('model', 'N/A')}")
        print(f"   Dimensions: {result.metadata.get('dimensions', 0)}")
        if result.data and 'embedding' in result.data:
            print(f"   Embedding vector length: {len(result.data['embedding'])}")
            print(f"   First 5 values: {result.data['embedding'][:5]}")
    else:
        print(f"   ❌ FAIL - {result.metadata.get('error', 'Unknown error')}")

    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_all_tools()
