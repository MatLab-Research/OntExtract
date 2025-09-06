#!/usr/bin/env python3
"""
Test script to verify period matching for OED definitions
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.period_matching_service import PeriodMatchingService

def test_period_matching():
    """Test that OED definitions are correctly matched to relevant periods"""
    
    # Create service instance
    matching_service = PeriodMatchingService()
    
    # Sample OED definitions with different date ranges
    definitions = [
        {
            'definition_number': '1',
            'definition_text': 'Early philosophical definition of agent',
            'first_cited_year': 1600,
            'last_cited_year': 1800,
            'status': 'historical'
        },
        {
            'definition_number': '2', 
            'definition_text': 'Mid-20th century economics definition',
            'first_cited_year': 1940,
            'last_cited_year': 1980,
            'status': 'historical'
        },
        {
            'definition_number': '3',
            'definition_text': 'Modern computer science definition',
            'first_cited_year': 1990,
            'last_cited_year': None,  # Still current
            'status': 'current'
        },
        {
            'definition_number': '4',
            'definition_text': 'Contemporary AI/ML definition',
            'first_cited_year': 2010,
            'last_cited_year': None,  # Still current
            'status': 'current'
        }
    ]
    
    # Target years from academic anchors
    target_years = [1957, 1976, 1995, 2018]
    
    print("Testing Period Matching Service")
    print("=" * 60)
    print(f"Target years: {target_years}")
    print()
    
    # Match definitions to periods
    matched_definitions = matching_service.enhance_definitions_with_period_matching(
        definitions, target_years, 'agent'
    )
    
    # Display results
    for definition in matched_definitions:
        print(f"Definition {definition['definition_number']}:")
        print(f"  Period: {definition.get('first_cited_year', '?')}-{definition.get('last_cited_year', 'present')}")
        print(f"  Status: {definition.get('status', 'unknown')}")
        print(f"  Relevant to years: {definition.get('relevant_periods', [])}")
        print(f"  Relevance note: {definition.get('excerpt_relevance', 'N/A')}")
        print()
    
    # Verify expected matches
    print("Verification:")
    print("-" * 40)
    
    # Definition 1 (1600-1800) should not match any modern years
    def1_periods = matched_definitions[0].get('relevant_periods', [])
    if not def1_periods:
        print("✓ Definition 1 (1600-1800): Correctly has no matching modern years")
    else:
        print(f"✗ Definition 1 (1600-1800): Incorrectly matched to {def1_periods}")
    
    # Definition 2 (1940-1980) should match 1957 and 1976
    def2_periods = matched_definitions[1].get('relevant_periods', [])
    if 1957 in def2_periods and 1976 in def2_periods and 1995 not in def2_periods:
        print("✓ Definition 2 (1940-1980): Correctly matched to 1957 and 1976")
    else:
        print(f"✗ Definition 2 (1940-1980): Incorrectly matched to {def2_periods}")
    
    # Definition 3 (1990-present) should match 1995 and 2018
    def3_periods = matched_definitions[2].get('relevant_periods', [])
    if 1995 in def3_periods and 2018 in def3_periods and 1957 not in def3_periods:
        print("✓ Definition 3 (1990-present): Correctly matched to 1995 and 2018")
    else:
        print(f"✗ Definition 3 (1990-present): Incorrectly matched to {def3_periods}")
    
    # Definition 4 (2010-present) should only match 2018
    def4_periods = matched_definitions[3].get('relevant_periods', [])
    if 2018 in def4_periods and len(def4_periods) == 1:
        print("✓ Definition 4 (2010-present): Correctly matched to 2018 only")
    else:
        print(f"✗ Definition 4 (2010-present): Incorrectly matched to {def4_periods}")
    
    print()
    print("Test completed!")

if __name__ == '__main__':
    test_period_matching()
