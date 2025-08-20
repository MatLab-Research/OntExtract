#!/usr/bin/env python3
"""
Test script to verify the OED periods functionality in temporal experiments.
This simulates the request that happens when clicking "Use OED Periods" button.
"""

import json
import requests
from typing import Dict, Any

def test_oed_periods():
    """Test the OED periods functionality."""
    
    # Configuration for test
    BASE_URL = "http://localhost:8765"
    EXPERIMENT_ID = 21  # Adjust to your experiment ID
    
    # Simulate the request that happens when clicking "Use OED Periods"
    test_data = {
        "term": "ontology",
        "periods": [2000, 2005, 2010, 2015, 2020],  # Initial periods
        "use_oed": True  # This triggers OED integration
    }
    
    print("Testing OED Periods functionality...")
    print(f"Term: {test_data['term']}")
    print(f"Initial periods: {test_data['periods']}")
    print(f"Use OED: {test_data['use_oed']}")
    print("-" * 50)
    
    # Make the request
    url = f"{BASE_URL}/experiments/{EXPERIMENT_ID}/fetch_temporal_data"
    
    try:
        # Note: You'll need to be logged in for this to work
        # You might need to add session cookies or authentication
        response = requests.post(url, json=test_data)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print("✓ Request successful!")
                
                # Check OED data
                if 'oed_data' in data:
                    oed_data = data['oed_data']
                    print(f"\n✓ OED Data Found:")
                    print(f"  - Year range: {oed_data.get('min_year')}-{oed_data.get('max_year')}")
                    print(f"  - Quotation years: {len(oed_data.get('quotation_years', []))} total")
                    print(f"  - Suggested periods: {oed_data.get('suggested_periods')}")
                else:
                    print("\n✗ No OED data in response")
                
                # Check temporal data
                if 'temporal_data' in data:
                    temporal_data = data['temporal_data']
                    print(f"\n✓ Temporal Data:")
                    for period, period_data in temporal_data.items():
                        is_oed = period_data.get('is_oed_data', False)
                        source = 'OED' if is_oed else 'Documents'
                        freq = period_data.get('frequency', 0)
                        evolution = period_data.get('evolution', 'unknown')
                        print(f"  - {period}: freq={freq}, evolution={evolution}, source={source}")
                else:
                    print("\n✗ No temporal data in response")
                
                # Check periods used
                if 'periods_used' in data:
                    print(f"\n✓ Periods actually used: {data['periods_used']}")
                
            else:
                print(f"✗ Request failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"✗ HTTP Error {response.status_code}: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Request error: {e}")
    except json.JSONDecodeError as e:
        print(f"✗ JSON decode error: {e}")
        print(f"Response text: {response.text[:500]}")

def test_without_oed():
    """Test without OED to compare."""
    
    BASE_URL = "http://localhost:8765"
    EXPERIMENT_ID = 21
    
    test_data = {
        "term": "ontology",
        "periods": [2000, 2005, 2010, 2015, 2020],
        "use_oed": False  # No OED integration
    }
    
    print("\n" + "=" * 50)
    print("Testing WITHOUT OED for comparison...")
    print("-" * 50)
    
    url = f"{BASE_URL}/experiments/{EXPERIMENT_ID}/fetch_temporal_data"
    
    try:
        response = requests.post(url, json=test_data)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print("✓ Request successful!")
                
                # Should not have OED data
                if 'oed_data' in data:
                    print("✗ Unexpected OED data in non-OED request")
                else:
                    print("✓ No OED data (as expected)")
                
                # Check temporal data
                if 'temporal_data' in data:
                    temporal_data = data['temporal_data']
                    print(f"\n✓ Document-based Temporal Data:")
                    for period, period_data in temporal_data.items():
                        freq = period_data.get('frequency', 0)
                        evolution = period_data.get('evolution', 'unknown')
                        print(f"  - {period}: freq={freq}, evolution={evolution}")
                        
            else:
                print(f"✗ Request failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"✗ HTTP Error {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    print("OED Periods Test Script")
    print("=" * 50)
    
    # Test with OED
    test_oed_periods()
    
    # Test without OED for comparison
    test_without_oed()
    
    print("\n" + "=" * 50)
    print("Test complete!")
    print("\nNote: This test requires:")
    print("1. The Flask app running on localhost:8765")
    print("2. An active login session")
    print("3. Experiment ID 21 to exist with some documents")
    print("4. Valid OED API credentials configured")
