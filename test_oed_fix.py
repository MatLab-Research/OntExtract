#!/usr/bin/env python3
"""Test the OED integration fix for temporal experiments"""

import os
import sys
import json

# Add the project root to the path
sys.path.insert(0, '/home/chris/onto/OntExtract')

# Set up Flask app context
from app import create_app
app = create_app()

def test_oed_periods():
    """Test that OED periods are correctly extracted"""
    with app.app_context():
        try:
            from app.services.oed_service import OEDService
            
            # Initialize OED service
            oed_service = OEDService()
            
            # Test term
            test_term = "technology"
            
            print(f"Testing OED period extraction for: '{test_term}'")
            print("=" * 60)
            
            # Get suggestions
            suggestions = oed_service.suggest_ids(test_term, limit=1)
            
            if suggestions and suggestions.get('success') and suggestions.get('suggestions'):
                entry_id = suggestions['suggestions'][0].get('entry_id')
                print(f"✓ Found entry_id: {entry_id}")
                
                # Get quotations
                quotations_result = oed_service.get_quotations(entry_id, limit=100)
                
                if quotations_result and quotations_result.get('success'):
                    data = quotations_result.get('data', {})
                    
                    # Extract years using the correct 'data' key
                    quotations = data.get('data', [])
                    years = []
                    
                    for q in quotations:
                        if q and isinstance(q, dict):
                            year = q.get('year')
                            if year:
                                try:
                                    years.append(int(year))
                                except (ValueError, TypeError):
                                    pass
                    
                    if years:
                        min_year = min(years)
                        max_year = max(years)
                        print(f"✓ Found {len(years)} quotation years")
                        print(f"✓ Year range: {min_year} - {max_year}")
                        
                        # Generate periods
                        from app.routes.experiments import generate_time_periods
                        periods = generate_time_periods(min_year, max_year)
                        print(f"✓ Generated periods: {periods}")
                        
                        print("\n✅ OED integration is working correctly!")
                        return True
                    else:
                        print("✗ No years found in quotations")
                else:
                    print(f"✗ Failed to get quotations: {quotations_result.get('error', 'Unknown')}")
            else:
                print(f"✗ Failed to get suggestions: {suggestions.get('error', 'Unknown')}")
                
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    return False

if __name__ == "__main__":
    success = test_oed_periods()
    sys.exit(0 if success else 1)
