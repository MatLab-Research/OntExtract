"""
Quick test script for processing tools.

Run this to verify tools work before wiring to UI/MCP.
"""

from app.services.processing_tools import DocumentProcessor

# Test document
TEST_DOC = """
This is the first paragraph of the test document. It contains multiple sentences.
Each sentence should be properly tokenized.

This is the second paragraph. It is separated by a double newline.
The paragraph segmentation should work correctly.

Finally, this is the third paragraph. It demonstrates the segmentation capabilities of our processing tools.
"""

def test_segment_paragraph():
    """Test paragraph segmentation"""
    print("\n" + "="*60)
    print("Testing: segment_paragraph")
    print("="*60)

    processor = DocumentProcessor(user_id=1, experiment_id=10)
    result = processor.segment_paragraph(TEST_DOC)

    print(f"Status: {result.status}")
    print(f"Paragraphs found: {result.metadata['count']}")
    print(f"Average length: {result.metadata['avg_length']:.1f} chars")
    print(f"\nProvenance ID: {result.provenance['activity_id']}")

    print(f"\nParagraphs:")
    for i, para in enumerate(result.data, 1):
        print(f"  {i}. {para[:100]}...")

    return result.status == "success"


def test_segment_sentence():
    """Test sentence segmentation"""
    print("\n" + "="*60)
    print("Testing: segment_sentence")
    print("="*60)

    processor = DocumentProcessor(user_id=1, experiment_id=10)
    result = processor.segment_sentence(TEST_DOC)

    print(f"Status: {result.status}")

    if result.status == "success":
        print(f"Sentences found: {result.metadata['count']}")
        print(f"Average length: {result.metadata['avg_length']:.1f} chars")
        print(f"\nSentences:")
        for i, sent in enumerate(result.data[:5], 1):  # Show first 5
            print(f"  {i}. {sent}")
    else:
        print(f"Error: {result.metadata.get('error')}")

    return result.status == "success"


def test_result_serialization():
    """Test that results can be serialized to JSON"""
    print("\n" + "="*60)
    print("Testing: JSON serialization")
    print("="*60)

    processor = DocumentProcessor()
    result = processor.segment_paragraph("Test\n\nParagraph")

    import json
    json_str = json.dumps(result.to_dict(), indent=2)
    print(json_str[:500])
    print("\nSerialization: SUCCESS")

    return True


if __name__ == "__main__":
    print("\n" + "#"*60)
    print("# OntExtract Tool Testing")
    print("#"*60)

    tests = [
        test_segment_paragraph,
        test_segment_sentence,
        test_result_serialization
    ]

    results = []
    for test_func in tests:
        try:
            results.append(test_func())
        except Exception as e:
            print(f"\nERROR in {test_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for test_func, passed in zip(tests, results):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_func.__name__}")

    if all(results):
        print("\n🎉 All tests passed! Tools are ready for UI integration.")
    else:
        print(f"\n⚠️  {sum(not r for r in results)} test(s) failed.")
