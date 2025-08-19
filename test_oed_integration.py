#!/usr/bin/env python3
"""Test OED integration to diagnose the NoneType error"""

import os
import sys
import json
from pprint import pprint

# Add the project root to the path
sys.path.insert(0, '/home/chris/onto/OntExtract')

# Set up Flask app context
from app import create_app
app = create_app()

with app.app_context():
    try:
        from app.services.oed_service import OEDService
        
        # Initialize OED service
        oed_service = OEDService()
        
        # Test term
        test_term = "technology"
        
        print(f"Testing OED integration for term: '{test_term}'")
        print("=" * 60)
        
        # Step 1: Get suggestions
        print("\n1. Getting suggestions...")
        suggestions = oed_service.suggest_ids(test_term, limit=3)
        
        if not suggestions:
            print("   ERROR: No suggestions object returned")
        elif not suggestions.get('success'):
            print(f"   ERROR: {suggestions.get('error', 'Unknown error')}")
        else:
            print(f"   SUCCESS: Found {len(suggestions.get('suggestions', []))} suggestions")
            for i, sugg in enumerate(suggestions.get('suggestions', [])[:3]):
                print(f"   {i+1}. {sugg}")
            
            # Step 2: Get quotations for first suggestion
            if suggestions.get('suggestions'):
                first_suggestion = suggestions['suggestions'][0]
                entry_id = first_suggestion.get('entry_id')
                
                if entry_id:
                    print(f"\n2. Getting quotations for entry_id: {entry_id}")
                    quotations_result = oed_service.get_quotations(entry_id, limit=10)
                    
                    if not quotations_result:
                        print("   ERROR: No quotations result returned")
                    elif not quotations_result.get('success'):
                        print(f"   ERROR: {quotations_result.get('error', 'Unknown error')}")
                    else:
                        print("   SUCCESS: Got quotations data")
                        data = quotations_result.get('data')
                        
                        if data:
                            print(f"   Data type: {type(data)}")
                            print(f"   Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                            
                            # Try to find quotations in the data
                            if isinstance(data, dict):
                                for key in ['results', 'quotations', 'data', 'items']:
                                    if key in data:
                                        items = data[key]
                                        print(f"   Found items under key '{key}': {type(items)}")
                                        if isinstance(items, list):
                                            print(f"   Number of items: {len(items)}")
                                            if items:
                                                print(f"   First item type: {type(items[0])}")
                                                if isinstance(items[0], dict):
                                                    print(f"   First item keys: {list(items[0].keys())[:10]}")
                                                    # Try to extract a date
                                                    for date_key in ['date', 'year', 'dateString', 'quotation_date']:
                                                        if date_key in items[0]:
                                                            print(f"   Found date under key '{date_key}': {items[0][date_key]}")
                                                            break
                        else:
                            print("   ERROR: No data in quotations result")
                else:
                    print("   ERROR: No entry_id in first suggestion")
            else:
                print("   ERROR: No suggestions to test quotations with")
                
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure the Flask app is properly configured")
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")
        print("\nTraceback:")
        traceback.print_exc()
