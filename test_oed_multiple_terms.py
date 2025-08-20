#!/usr/bin/env python3
"""
Test script to verify that multiple terms get their own separate OED time periods.
"""

import os
import sys
import json
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and database
from app import create_app, db
from app.models import User, Experiment
from app.services.oed_service import OEDService

def test_multiple_terms_oed_periods():
    """Test that each term gets its own OED time periods."""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Testing Multiple Terms OED Period Generation")
        print("=" * 60)
        
        # Get a test user (use the first user or create one)
        user = User.query.first()
        if not user:
            print("No users found. Please create a user first.")
            return
        
        print(f"\nUsing user: {user.username}")
        
        # Test terms with different historical ranges
        test_terms = ["computer", "algorithm"]  # These should have different date ranges
        
        # Create a test experiment
        experiment_config = {
            "target_terms": test_terms,
            "use_oed_periods": True,
            "start_year": 2000,
            "end_year": 2020
        }
        
        experiment = Experiment(
            name=f"Test OED Multiple Terms - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description="Testing separate OED periods for multiple terms",
            experiment_type="temporal_evolution",
            user_id=user.id,
            configuration=json.dumps(experiment_config)
        )
        
        db.session.add(experiment)
        db.session.commit()
        
        print(f"\nCreated test experiment: {experiment.name}")
        print(f"Experiment ID: {experiment.id}")
        
        # Initialize OED service
        oed_service = OEDService()
        
        # Fetch OED data for each term
        oed_period_data = {}
        term_periods = {}
        overall_min_year = None
        overall_max_year = None
        
        for term in test_terms:
            print(f"\n--- Fetching OED data for '{term}' ---")
            
            try:
                # Get OED quotations for the term
                suggestions = oed_service.suggest_ids(term, limit=3)
                
                if not suggestions or not suggestions.get('success'):
                    print(f"  Failed to get suggestions for '{term}'")
                    term_periods[term] = []
                    continue
                    
                suggestion_list = suggestions.get('suggestions', [])
                if not suggestion_list:
                    print(f"  No suggestions found for '{term}'")
                    term_periods[term] = []
                    continue
                
                # Use first match
                entry_id = suggestion_list[0].get('entry_id')
                if not entry_id:
                    print(f"  No entry_id found for '{term}'")
                    term_periods[term] = []
                    continue
                
                print(f"  Found entry_id: {entry_id}")
                
                # Get quotations
                quotations_result = oed_service.get_quotations(entry_id, limit=100)
                
                if not quotations_result or not quotations_result.get('success'):
                    print(f"  Failed to get quotations for '{term}'")
                    term_periods[term] = []
                    continue
                
                quotations_data = quotations_result.get('data', {})
                results = quotations_data.get('data', [])
                
                # Extract years
                term_years = []
                for quotation in results:
                    year_value = quotation.get('year')
                    if year_value:
                        try:
                            term_years.append(int(year_value))
                        except (ValueError, TypeError):
                            pass
                
                if term_years:
                    min_year = min(term_years)
                    max_year = max(term_years)
                    
                    print(f"  Found {len(term_years)} quotation years")
                    print(f"  Date range: {min_year} - {max_year}")
                    
                    # Generate periods for this term
                    from app.routes.experiments import generate_time_periods
                    periods_for_term = generate_time_periods(min_year, max_year)
                    term_periods[term] = periods_for_term
                    
                    print(f"  Generated periods: {periods_for_term[:5]}{'...' if len(periods_for_term) > 5 else ''}")
                    
                    # Track overall range
                    if overall_min_year is None or min_year < overall_min_year:
                        overall_min_year = min_year
                    if overall_max_year is None or max_year > overall_max_year:
                        overall_max_year = max_year
                    
                    oed_period_data[term] = {
                        'min_year': min_year,
                        'max_year': max_year,
                        'quotation_years': sorted(list(set(term_years))),
                        'periods': periods_for_term
                    }
                else:
                    print(f"  No years found in quotations for '{term}'")
                    term_periods[term] = []
                    
            except Exception as e:
                print(f"  Error fetching OED data for '{term}': {str(e)}")
                term_periods[term] = []
        
        # Summary
        print("\n" + "=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)
        
        if overall_min_year and overall_max_year:
            print(f"\nOverall date range: {overall_min_year} - {overall_max_year}")
            
            print("\nTerm-specific periods:")
            for term, periods in term_periods.items():
                if periods:
                    print(f"\n  {term}:")
                    print(f"    Range: {oed_period_data[term]['min_year']} - {oed_period_data[term]['max_year']}")
                    print(f"    Number of periods: {len(periods)}")
                    print(f"    Sample periods: {periods[:3]}{'...' if len(periods) > 3 else ''}")
                else:
                    print(f"\n  {term}: No OED data available")
            
            # Check if periods are different
            if len(test_terms) > 1:
                periods_are_different = False
                first_term_periods = term_periods[test_terms[0]]
                for term in test_terms[1:]:
                    if term_periods[term] != first_term_periods:
                        periods_are_different = True
                        break
                
                print("\n" + "-" * 40)
                if periods_are_different:
                    print("✓ SUCCESS: Each term has its own unique time periods!")
                else:
                    print("✗ ISSUE: All terms have the same time periods (they should be different)")
        else:
            print("\n✗ No OED data found for any terms")
        
        # Clean up test experiment
        db.session.delete(experiment)
        db.session.commit()
        print("\nTest experiment cleaned up.")

if __name__ == "__main__":
    test_multiple_terms_oed_periods()
