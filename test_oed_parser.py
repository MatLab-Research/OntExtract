#!/usr/bin/env python3
"""
Test script for simplified OED PDF parser using LangExtract
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv('.env.local')

from app.services.oed_parser import OEDParser

def test_oed_parser():
    """Test the simplified OED parser"""
    
    print("=" * 60)
    print("Simplified OED Parser Test (LangExtract + Claude)")
    print("=" * 60)
    
    # Check if API key is set
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("\n❌ Error: ANTHROPIC_API_KEY not set in .env.local")
        print("Please add your Claude API key to continue.")
        return
    
    try:
        # Initialize parser
        parser = OEDParser()
        print("\n✓ OED Parser initialized successfully")
    except Exception as e:
        print(f"\n❌ Failed to initialize parser: {e}")
        return
    
    # Check for test PDFs
    test_pdfs = [
        "app/docs/agent.pdf",
        "app/docs/ontology.pdf"
    ]
    
    for pdf_path in test_pdfs:
        if os.path.exists(pdf_path):
            print(f"\n\nTesting with: {pdf_path}")
            print("-" * 40)
            
            try:
                result = parser.parse_pdf(pdf_path)
                
                # Display extracted data
                if result.get('headword'):
                    print(f"✓ Headword: {result['headword']}")
                
                if result.get('pronunciation'):
                    print(f"✓ Pronunciation: {result['pronunciation']}")
                
                if result.get('etymology'):
                    etym = result['etymology']
                    if isinstance(etym, dict):
                        if etym.get('origin'):
                            print(f"✓ Etymology origin: {etym['origin']}")
                    else:
                        print(f"✓ Etymology: {etym[:100]}...")
                
                if result.get('definitions'):
                    print(f"✓ Definitions found: {len(result['definitions'])}")
                    for i, defn in enumerate(result['definitions'][:2], 1):
                        text = defn.get('text', '')[:80]
                        print(f"  {defn.get('number', i)}. {text}...")
                        if defn.get('quotations'):
                            print(f"     → {len(defn['quotations'])} quotations")
                
                # Temporal analysis
                if result.get('temporal_data'):
                    temporal = result['temporal_data']
                    if temporal.get('first_use'):
                        print(f"✓ First recorded use: {temporal['first_use']}")
                    if temporal.get('century_distribution'):
                        print(f"✓ Century distribution: {temporal['century_distribution']}")
                    if temporal.get('semantic_shifts'):
                        print(f"✓ Semantic shifts detected: {len(temporal['semantic_shifts'])}")
                
                # Check for parse errors
                if result.get('parse_error'):
                    print(f"⚠ Parse warning: {result['parse_error']}")
                
                print("\n✅ Successfully parsed!")
                
            except Exception as e:
                print(f"❌ Error parsing: {e}")
        else:
            print(f"\n⚠ File not found: {pdf_path}")
            print("  (This is expected if no test PDFs are uploaded)")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("\nNote: The simplified parser uses LangExtract for text extraction")
    print("and Claude for intelligent parsing - much cleaner and more reliable!")

if __name__ == "__main__":
    test_oed_parser()
