"""
Test script for OED temporal extraction.

Usage:
    python test_oed_extraction.py
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.services.oed_temporal_extractor import extract_oed_timeline

def main():
    """Test OED extraction for agent term"""
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("OED TEMPORAL EXTRACTION TEST")
        print("=" * 80)

        # Path to OED PDF
        oed_pdf_path = "/home/chris/onto/OntExtract/docs/sources/agent, n.¹ & adj. meanings, etymology and more _ Oxford English Dictionary.pdf"

        print(f"\nExtracting timeline from: {oed_pdf_path}")
        print(f"Term: agent\n")

        try:
            # Run extraction
            result = extract_oed_timeline("agent", oed_pdf_path)

            print(f"Status: {result['status']}")
            print(f"\nStatistics:")
            stats = result['statistics']
            for key, value in stats.items():
                print(f"  {key}: {value}")

            print(f"\nExtracted {len(result['markers'])} timeline markers:")
            print("-" * 80)

            for i, marker in enumerate(result['markers'], 1):
                print(f"\n{i}. Year: {marker['year']} | Period: {marker['period']}")
                print(f"   Sense: {marker['sense']} | Category: {marker['category']}")
                print(f"   Definition: {marker['definition_short']}")

            print("\n" + "=" * 80)
            print("EXTRACTION COMPLETE!")
            print("=" * 80)

        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main()
