#!/usr/bin/env python3
"""
Simple test of LangExtract for OED parsing
Following the LangExtract documentation approach
"""

import os
import sys
import json
from dotenv import load_dotenv
import pypdf

# Load environment variables
load_dotenv('.env.local')

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import langextract as lx

def extract_pdf_text(pdf_path: str) -> str:
    """Extract text from PDF using pypdf"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
        
        # Clean null characters that break storage
        text = text.replace('\x00', '')
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        raise

def test_langextract_simple():
    """Test LangExtract with OED text"""
    
    print("Simple LangExtract Test for OED Parsing")
    print("=" * 50)
    
    # Step 1: Extract text from PDF
    pdf_path = "app/docs/ontology.pdf"
    print(f"\n1. Extracting text from: {pdf_path}")
    text = extract_pdf_text(pdf_path)
    print(f"   ✓ Extracted {len(text)} characters")
    
    # Step 2: Define what we want to extract
    prompt_description = """
    Extract dictionary entries from this Oxford English Dictionary text.
    
    For each entry, extract the main word and its attributes including:
    - headword: The main word being defined
    - etymology: The word's origin
    - first_year: The earliest recorded year
    - definitions: JSON array of definitions with number and text
    - quotations: JSON array of historical quotations with year, author, and text
    
    Extract ALL historical quotations with their dates.
    """
    
    # Step 3: Provide examples to guide extraction
    # For LangExtract, we'll use a simpler extraction format
    examples = [
        lx.data.ExampleData(
            text="ontology (n.) Etymology: From Latin ontologia. 1. The study of being. 1663 Harvey: 'Metaphysics is called Ontology'",
            extractions=[
                lx.data.Extraction(
                    extraction_class="dictionary_entry",
                    extraction_text="ontology",
                    attributes={
                        "headword": "ontology",
                        "etymology": "From Latin ontologia",
                        "first_year": "1663",
                        "definitions": "[{\"number\": \"1\", \"text\": \"The study of being\"}]",
                        "quotations": "[{\"year\": \"1663\", \"author\": \"Harvey\", \"text\": \"Metaphysics is called Ontology\"}]"
                    }
                )
            ]
        )
    ]
    
    print("\n2. Configuring LangExtract:")
    print("   - Using examples to guide extraction")
    print("   - Focusing on structured dictionary data")
    
    # Step 4: Check which API key is available
    api_key = None
    model_id = None
    
    if os.environ.get('GOOGLE_GEMINI_API_KEY'):
        api_key = os.environ.get('GOOGLE_GEMINI_API_KEY')
        model_id = "gemini-2.0-flash-exp"
        print(f"   - Using Gemini model: {model_id}")
    elif os.environ.get('ANTHROPIC_API_KEY'):
        # Note: LangExtract primarily supports Gemini, but we can try
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        model_id = "claude-3-5-sonnet-20241022"
        print(f"   - Attempting with Anthropic (may need Gemini for best results)")
    elif os.environ.get('LANGEXTRACT_API_KEY'):
        api_key = os.environ.get('LANGEXTRACT_API_KEY')
        model_id = "gemini-2.0-flash-exp"
        print(f"   - Using LANGEXTRACT_API_KEY with {model_id}")
    else:
        print("   ✗ No API key found!")
        print("   Set one of: GOOGLE_GEMINI_API_KEY, LANGEXTRACT_API_KEY")
        return None
    
    # Step 5: Extract using LangExtract
    print("\n3. Extracting with LangExtract...")
    print("-" * 50)
    
    try:
        # Use LangExtract to extract structured data
        result = lx.extract(
            text_or_documents=text[:15000],  # Use first 15k chars for testing
            prompt_description=prompt_description,
            examples=examples,
            model_id=model_id,
            api_key=api_key,
            format_type=lx.data.FormatType.JSON,
            temperature=0.1,  # Low for consistency
            max_char_buffer=2000,  # Process in chunks
            fence_output=False,
            use_schema_constraints=True,
            extraction_passes=1  # Can increase for better recall
        )
        
        print("   ✓ Extraction complete!")
        
        # Step 6: Process results
        print("\n4. Results:")
        print("-" * 50)
        
        extractions = getattr(result, 'extractions', None)
        if extractions:
            for i, extraction in enumerate(extractions):
                print(f"\n   Extraction {i+1}:")
                print(f"   - Class: {extraction.extraction_class}")
                print(f"   - Text: {extraction.extraction_text}")
                
                # Check attributes
                if extraction.attributes:
                    attrs = extraction.attributes
                    print(f"   - Headword: {attrs.get('headword', 'Not found')}")
                    print(f"   - Etymology: {attrs.get('etymology', 'Not found')[:100]}...")
                    print(f"   - First year: {attrs.get('first_year', 'Not found')}")
                    
                    # Parse definitions if they're JSON
                    defs_str = attrs.get('definitions', '[]')
                    try:
                        defs = json.loads(defs_str) if isinstance(defs_str, str) else defs_str
                        print(f"   - Definitions: {len(defs)} found")
                        for d in defs[:2]:
                            if isinstance(d, dict):
                                print(f"     • {d.get('number', '')}. {d.get('text', '')[:80]}...")
                    except:
                        print(f"   - Definitions: {defs_str[:100]}...")
                    
                    # Parse quotations if they're JSON
                    quotes_str = attrs.get('quotations', '[]')
                    try:
                        quotes = json.loads(quotes_str) if isinstance(quotes_str, str) else quotes_str
                        print(f"   - Historical quotations: {len(quotes)} found")
                        for q in quotes[:3]:
                            if isinstance(q, dict):
                                year = q.get('year', 'No year')
                                text = q.get('text', '')[:60]
                                author = q.get('author', '')
                                if author:
                                    print(f"     • [{year}] {author}: {text}...")
                                else:
                                    print(f"     • [{year}] {text}...")
                    except:
                        print(f"   - Quotations: {quotes_str[:100]}...")
                
                # Show the grounding (where in text it was found)
                if extraction.char_interval:
                    print(f"\n   Grounding: Found at chars {extraction.char_interval.start_pos}-{extraction.char_interval.end_pos}")
        
        print("\n" + "=" * 50)
        print("✓ LangExtract test completed successfully!")
        
        # Save results for inspection
        output_file = "langextract_test_output.json"
        if extractions:
            output_data = []
            for extraction in extractions:
                entry = {
                    "extraction_class": extraction.extraction_class,
                    "extraction_text": extraction.extraction_text,
                    "attributes": extraction.attributes
                }
                output_data.append(entry)
            
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\n✓ Results saved to: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"\n✗ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_langextract_simple()
    
    if not result:
        print("\n" + "=" * 50)
        print("Note: LangExtract works best with Google Gemini API.")
        print("To get a Gemini API key:")
        print("1. Visit: https://makersuite.google.com/app/apikey")
        print("2. Create a new API key")
        print("3. Add to .env.local: GOOGLE_GEMINI_API_KEY=your-key-here")
        print("4. Or set: LANGEXTRACT_API_KEY=your-gemini-key")
