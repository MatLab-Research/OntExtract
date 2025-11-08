"""Quick test script for processing tools."""

from app.services.processing_tools import DocumentProcessor

test_text = """This is the first paragraph. It has multiple sentences.

This is the second paragraph. It also has some content.

Final paragraph with more text."""

print("Testing paragraph segmentation...")
processor = DocumentProcessor()
result = processor.segment_paragraph(test_text)

print(f"Status: {result.status}")
print(f"Count: {result.metadata['count']}")
print(f"Paragraphs: {result.data}")
print()

print("Testing sentence segmentation...")
result2 = processor.segment_sentence(test_text)
print(f"Status: {result2.status}")
print(f"Count: {result2.metadata['count']}")
print(f"Sentences (first 3): {result2.data[:3]}")
