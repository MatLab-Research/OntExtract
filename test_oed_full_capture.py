#!/usr/bin/env python3
"""
Test OED parser to ensure it captures full PDF content
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.oed_parser import OEDParser

def test_full_capture():
    """Test OED parser with ontology.pdf"""
    
    pdf_path = "app/docs/ontology.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found")
        return
    
    print(f"Testing OED parser with: {pdf_path}")
    print("-" * 50)
    
    try:
        parser = OEDParser()
        result = parser.parse_pdf(pdf_path)
        
        # Show what we captured
        print(f"✓ Headword: {result.get('headword', 'Not found')}")
        print(f"✓ First recorded use: {result.get('first_recorded_use', 'Not found')}")
        
        # Most importantly - check full text capture
        full_text = result.get('full_text', '')
        print(f"\n✓ Full text captured: {len(full_text)} characters")
        
        if full_text:
            print(f"  First 200 chars: {full_text[:200]}...")
            print(f"  Last 200 chars: ...{full_text[-200:]}")
        
        # Check historical quotations
        quotations = result.get('historical_quotations', [])
        print(f"\n✓ Historical quotations found: {len(quotations)}")
        if quotations:
            print("  Sample quotations:")
            for i, quote in enumerate(quotations[:3]):
                print(f"    [{quote.get('year', 'No year')}] {quote.get('text', '')[:100]}...")
        
        # Check temporal data
        temporal = result.get('temporal_data', {})
        if temporal.get('century_distribution'):
            print(f"\n✓ Century distribution:")
            for century, count in temporal['century_distribution'].items():
                print(f"    {century}: {count} usages")
        
        # Save full text to file for inspection
        output_file = "oed_capture_test.txt"
        with open(output_file, 'w') as f:
            f.write(f"FULL TEXT CAPTURED ({len(full_text)} characters):\n")
            f.write("=" * 50 + "\n")
            f.write(full_text)
            f.write("\n" + "=" * 50 + "\n")
            f.write("\nHISTORICAL QUOTATIONS:\n")
            for quote in quotations:
                f.write(f"[{quote.get('year', 'No year')}] {quote.get('text', '')}\n\n")
        
        print(f"\n✓ Full output saved to: {output_file}")
        
    except Exception as e:
        print(f"✗ Error parsing PDF: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_capture()
