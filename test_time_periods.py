#!/usr/bin/env python3
"""Test script to verify time period generation logic"""

import json

def test_time_period_generation():
    """Test the time period generation logic from the route"""
    
    # Simulate empty configuration
    config = {}
    time_periods = config.get('time_periods', [])
    terms = config.get('target_terms', [])
    start_year = config.get('start_year', 2000)
    end_year = config.get('end_year', 2020)
    
    print(f"Initial state:")
    print(f"  time_periods: {time_periods}")
    print(f"  start_year: {start_year}")
    print(f"  end_year: {end_year}")
    print()
    
    # If no time periods specified, generate default
    if not time_periods or len(time_periods) == 0:
        # Generate periods with 5-year intervals
        time_periods = []
        current_year = start_year
        while current_year <= end_year:
            time_periods.append(current_year)
            current_year += 5
        # Ensure end year is included if not already
        if time_periods and time_periods[-1] < end_year:
            time_periods.append(end_year)
        # If still empty, create a basic set
        if not time_periods:
            time_periods = [2000, 2005, 2010, 2015, 2020]
    
    print(f"Generated time_periods: {time_periods}")
    print(f"Number of periods: {len(time_periods)}")
    
    # Test with different configurations
    print("\n" + "="*50)
    print("Testing with different year ranges:")
    print("="*50)
    
    test_cases = [
        (1990, 2020),
        (2000, 2024),
        (1800, 1900),
        (2010, 2015),
    ]
    
    for start, end in test_cases:
        periods = []
        current = start
        while current <= end:
            periods.append(current)
            current += 5
        if periods and periods[-1] < end:
            periods.append(end)
        if not periods:
            periods = [2000, 2005, 2010, 2015, 2020]
        
        print(f"\nRange {start}-{end}: {periods}")

if __name__ == "__main__":
    test_time_period_generation()
