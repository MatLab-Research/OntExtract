#!/usr/bin/env python3
"""
Test the LangExtract-based OED parser
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.oed_parser_langextract import OEDParserLangExtract

def test_langextract_parser():
    """Test the LangExtract-based OED parser"""
    
    print("Testing LangExtract-based OED Parser")
    print("=" * 50)
    
    # Initialize parser
    try:
        parser = OEDParserLangExtract()
        print("✓ Parser initialized successfully")
        
        # Check which model will be used
        if hasattr(parser, 'use_anthropic_fallback'):
            print("  Using: Anthropic Claude (via fallback)")
        else:
            print(f"  Using: {parser.model_id} via LangExtract")
    except Exception as e:
        print(f"✗ Failed to initialize parser: {e}")
        return
    
    # Parse the OED PDF
    pdf_path = "app/docs/ontology.pdf"
    print(f"\nParsing: {pdf_path}")
    print("-" * 50)
    
    try:
        result = parser.parse_pdf(pdf_path)
        
        # Display results
        print(f"✓ Headword: {result.get('headword')}")
        print(f"✓ Etymology: {result.get('etymology', 'Not extracted')[:100]}...")
        print(f"✓ First recorded use: {result.get('first_recorded_use')}")
        
        # Check definitions
        definitions = result.get('definitions', [])
        print(f"\n✓ Definitions found: {len(definitions)}")
        for i, defn in enumerate(definitions[:3]):
            if isinstance(defn, dict):
                text = defn.get('text', '')
            else:
                text = str(defn)
            print(f"  {i+1}. {text[:80]}...")
        
        # Check historical quotations
        quotations = result.get('historical_quotations', [])
        print(f"\n✓ Historical quotations found: {len(quotations)}")
        
        # Display sample quotations
        if quotations:
            print("\n  Sample quotations:")
            for quote in quotations[:5]:
                year = quote.get('year', 'No year')
                text = quote.get('text', '')[:80]
                author = quote.get('author', '')
                if author:
                    print(f"    [{year}] {author}: {text}...")
                else:
                    print(f"    [{year}] {text}...")
        
        # Check temporal data
        temporal = result.get('temporal_data', {})
        if temporal:
            print(f"\n✓ Temporal analysis:")
            print(f"  First use: {temporal.get('first_use')}")
            print(f"  Timeline entries: {len(temporal.get('usage_timeline', []))}")
            
            # Century distribution
            distribution = temporal.get('century_distribution', {})
            if distribution:
                print("\n  Century distribution:")
                for century, count in sorted(distribution.items()):
                    print(f"    {century}: {count} usages")
        
        # Check full text
        full_text = result.get('full_text', '')
        print(f"\n✓ Full text captured: {len(full_text)} characters")
        
        # Check for website boilerplate (should be removed)
        bad_patterns = [
            "Oxford University Press uses cookies",
            "Cookie Policy",
            "Google Books Ngrams"
        ]
        
        clean = True
        for pattern in bad_patterns:
            if pattern in full_text:
                print(f"  ✗ Found unwanted pattern: '{pattern}'")
                clean = False
        
        if clean:
            print("  ✓ Text properly cleaned (no website boilerplate found)")
        
        # Show text preview
        if full_text:
            print(f"\n  Text preview (first 200 chars):")
            print(f"  {full_text[:200]}...")
        
        print("\n" + "=" * 50)
        print("✓ LangExtract parser test completed successfully!")
        
        # Return the result for further testing
        return result
        
    except Exception as e:
        print(f"\n✗ Error parsing PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_with_original():
    """Compare LangExtract results with the original parser"""
    print("\n" + "=" * 50)
    print("Comparing LangExtract vs Original Parser")
    print("=" * 50)
    
    # Test LangExtract parser
    print("\n1. LangExtract Parser:")
    result_new = test_langextract_parser()
    
    if result_new:
        # Import and test original parser
        print("\n2. Original Parser:")
        print("-" * 50)
        
        from app.services.oed_parser import OEDParser
        
        try:
            parser_old = OEDParser()
            result_old = parser_old.parse_pdf("app/docs/ontology.pdf")
            
            print(f"✓ Original parser quotations: {len(result_old.get('historical_quotations', []))}")
            print(f"✓ Original parser full text: {len(result_old.get('full_text', ''))} chars")
            
            # Compare results
            print("\n3. Comparison:")
            print("-" * 50)
            
            new_quotes = len(result_new.get('historical_quotations', []))
            old_quotes = len(result_old.get('historical_quotations', []))
            
            if new_quotes >= old_quotes:
                print(f"✓ LangExtract found {new_quotes - old_quotes} more quotations")
            else:
                print(f"✗ LangExtract found {old_quotes - new_quotes} fewer quotations")
            
            new_text_len = len(result_new.get('full_text', ''))
            old_text_len = len(result_old.get('full_text', ''))
            
            print(f"  Text length: {new_text_len} vs {old_text_len} chars")
            
        except Exception as e:
            print(f"✗ Could not compare with original: {e}")

if __name__ == "__main__":
    # Run the test
    test_langextract_parser()
    
    # Optionally compare with original
    # compare_with_original()
