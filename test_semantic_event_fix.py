#!/usr/bin/env python3
"""
Test script to verify the semantic event JSON serialization fix.
Tests that period_documents are properly serialized when loading the temporal terms page.
"""

import sys
import os

# Add the OntExtract directory to the path
sys.path.insert(0, '/home/chris/onto/OntExtract')

from app import create_app
from app.services.temporal_service import get_temporal_service
import json

def test_temporal_ui_data():
    """Test that get_temporal_ui_data returns JSON-serializable data"""

    app = create_app()

    with app.app_context():
        temporal_service = get_temporal_service()

        print("=" * 60)
        print("Testing Temporal UI Data Serialization")
        print("=" * 60)

        # Test with experiment 74
        experiment_id = 74
        print(f"\n📊 Testing experiment {experiment_id}...")

        try:
            # Get the UI data
            data = temporal_service.get_temporal_ui_data(experiment_id)

            print(f"✅ get_temporal_ui_data() completed successfully")

            # Check period_documents
            period_documents = data.get('period_documents', {})
            print(f"\n📁 Period Documents: {len(period_documents)} periods")

            # Try to JSON serialize period_documents
            try:
                json_str = json.dumps(period_documents)
                print(f"✅ period_documents is JSON serializable")
                print(f"   Size: {len(json_str)} characters")

                # Show sample
                for period_key, docs in list(period_documents.items())[:2]:
                    print(f"\n   Period {period_key}: {len(docs)} documents")
                    for doc in docs:
                        print(f"     - {doc.get('title', 'Untitled')}")
                        print(f"       Type: {type(doc).__name__}")
                        print(f"       Keys: {list(doc.keys())}")

            except TypeError as e:
                print(f"❌ ERROR: period_documents is NOT JSON serializable!")
                print(f"   Error: {e}")

                # Show problematic data
                for period_key, docs in period_documents.items():
                    print(f"\n   Period {period_key}:")
                    for i, doc in enumerate(docs):
                        print(f"     Document {i}: type={type(doc).__name__}")
                        if hasattr(doc, '__dict__'):
                            print(f"     Attributes: {list(doc.__dict__.keys())[:5]}")

                return False

            # Test other fields
            print(f"\n📋 Other data fields:")
            print(f"   time_periods: {data.get('time_periods')}")
            print(f"   terms: {data.get('terms')}")
            print(f"   start_year: {data.get('start_year')}")
            print(f"   end_year: {data.get('end_year')}")
            print(f"   period_metadata keys: {list(data.get('period_metadata', {}).keys())}")
            print(f"   semantic_events: {len(data.get('semantic_events', []))} events")

            print(f"\n✅ All tests passed! The fix is working correctly.")
            return True

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_temporal_ui_data()
    sys.exit(0 if success else 1)
