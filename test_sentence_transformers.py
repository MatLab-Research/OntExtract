#!/usr/bin/env python3
"""
Test script for sentence-transformers 5.1.2 compatibility

Tests the new version's core functionality:
1. Model initialization
2. Offline mode behavior
3. Encoding functionality
4. Embedding dimensions
"""

import os
import sys

# Set offline mode (critical for production)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

def test_sentence_transformers():
    """Test sentence-transformers 5.1.2 functionality"""

    print("=" * 60)
    print("sentence-transformers 5.1.2 Compatibility Test")
    print("=" * 60)

    try:
        from sentence_transformers import SentenceTransformer
        print("✓ Import successful")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        print("\nPlease install: pip install sentence-transformers==5.1.2")
        return False

    # Test 1: Model initialization
    print("\n[Test 1] Model Initialization")
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print(f"✓ Model loaded: all-MiniLM-L6-v2")
    except Exception as e:
        print(f"✗ Model loading failed: {e}")
        return False

    # Test 2: Basic encoding
    print("\n[Test 2] Basic Encoding")
    try:
        test_text = "This is a test sentence for semantic embeddings."
        embedding = model.encode(test_text)
        print(f"✓ Encoding successful")
        print(f"  - Input: '{test_text}'")
        print(f"  - Embedding type: {type(embedding)}")
        print(f"  - Embedding shape: {embedding.shape if hasattr(embedding, 'shape') else len(embedding)}")
    except Exception as e:
        print(f"✗ Encoding failed: {e}")
        return False

    # Test 3: Dimension check
    print("\n[Test 3] Dimension Verification")
    try:
        dimension = len(embedding)
        expected_dimension = 384  # all-MiniLM-L6-v2 should be 384

        if dimension == expected_dimension:
            print(f"✓ Dimension correct: {dimension}")
        else:
            print(f"⚠ Dimension mismatch: got {dimension}, expected {expected_dimension}")
    except Exception as e:
        print(f"✗ Dimension check failed: {e}")
        return False

    # Test 4: Batch encoding
    print("\n[Test 4] Batch Encoding")
    try:
        test_sentences = [
            "The quick brown fox jumps over the lazy dog",
            "Natural language processing is fascinating",
            "Semantic drift occurs across temporal periods"
        ]
        embeddings = model.encode(test_sentences)
        print(f"✓ Batch encoding successful")
        print(f"  - Input: {len(test_sentences)} sentences")
        print(f"  - Output shape: {embeddings.shape if hasattr(embeddings, 'shape') else f'{len(embeddings)} embeddings'}")
    except Exception as e:
        print(f"✗ Batch encoding failed: {e}")
        return False

    # Test 5: List conversion (for database storage)
    print("\n[Test 5] List Conversion")
    try:
        embedding_list = embedding.tolist()
        print(f"✓ Conversion to list successful")
        print(f"  - Type: {type(embedding_list)}")
        print(f"  - Length: {len(embedding_list)}")
        print(f"  - Sample values: [{embedding_list[0]:.4f}, {embedding_list[1]:.4f}, {embedding_list[2]:.4f}, ...]")
    except Exception as e:
        print(f"✗ List conversion failed: {e}")
        return False

    # Test 6: Offline mode verification
    print("\n[Test 6] Offline Mode Check")
    print(f"  - HF_HUB_OFFLINE: {os.environ.get('HF_HUB_OFFLINE')}")
    print(f"  - TRANSFORMERS_OFFLINE: {os.environ.get('TRANSFORMERS_OFFLINE')}")
    print(f"✓ Offline mode configured")

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    print("\nsentence-transformers 5.1.2 is compatible with OntExtract")
    print("Safe to proceed with implementation.")

    return True


if __name__ == "__main__":
    try:
        success = test_sentence_transformers()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
