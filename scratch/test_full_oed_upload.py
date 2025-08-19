#!/usr/bin/env python3
"""
Test full OED upload process to check text storage
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Flask app context
from app import create_app, db
from app.models.document import Document
from app.models.user import User
from app.services.oed_parser import OEDParser

def test_full_upload_process():
    """Test the complete OED upload process"""
    
    app = create_app()
    
    with app.app_context():
        print("Testing OED Upload Process")
        print("=" * 50)
        
        # Get or create test user
        test_user = User.query.filter_by(username='test_user').first()
        if not test_user:
            test_user = User(username='test_user', email='test@example.com', password='test123')
            db.session.add(test_user)
            db.session.commit()
            print(f"Created test user: {test_user.username}")
        else:
            print(f"Using existing test user: {test_user.username}")
        
        # Parse the OED PDF
        pdf_path = "app/docs/ontology.pdf"
        parser = OEDParser()
        result = parser.parse_pdf(pdf_path)
        
        print(f"\n1. Parsed PDF:")
        print(f"   - Headword: {result.get('headword')}")
        print(f"   - Full text length: {len(result.get('full_text', ''))} chars")
        
        # Simulate what happens when form is submitted
        title = result.get('headword', 'ontology')
        content = result.get('full_text', '')  # This is what goes in the form field
        
        # Create source metadata (as done in the route)
        source_metadata = {
            'examples': '',  # Would contain temporal quotations
            'first_use': result.get('first_recorded_use'),
            'journal': 'Oxford English Dictionary',
            'pdf_link': 'ontology.pdf'
        }
        
        # Add temporal quotations to examples
        if result.get('historical_quotations'):
            examples_text = ''
            for quote in result['historical_quotations']:
                if quote.get('text'):
                    year_prefix = f"[{quote.get('year', 'No year')}] "
                    examples_text += f"{year_prefix}{quote['text']}\n\n"
            source_metadata['examples'] = examples_text.strip()
        
        print(f"\n2. Preparing to save:")
        print(f"   - Title: {title}")
        print(f"   - Content length to save: {len(content)} chars")
        print(f"   - Examples length: {len(source_metadata.get('examples', ''))} chars")
        
        # Create document (as done in upload_dictionary route)
        document = Document(
            title=title,
            content_type='text',
            document_type='reference',
            reference_subtype='dictionary_oed',
            content=content,  # Full text stored here
            content_preview=content[:500] + ('...' if len(content) > 500 else ''),
            source_metadata=source_metadata,
            user_id=test_user.id,
            status='completed',
            word_count=len(content.split()),
            character_count=len(content)
        )
        
        # Save to database
        db.session.add(document)
        db.session.commit()
        
        print(f"\n3. Saved to database:")
        print(f"   - Document ID: {document.id}")
        print(f"   - Title: {document.title}")
        print(f"   - Character count: {document.character_count}")
        
        # Retrieve from database to check storage
        retrieved = Document.query.get(document.id)
        
        print(f"\n4. Retrieved from database:")
        print(f"   - Content length: {len(retrieved.content) if retrieved.content else 0} chars")
        print(f"   - Word count: {retrieved.word_count}")
        print(f"   - Status: {retrieved.status}")
        
        # Check if full text was stored
        if retrieved.content:
            print(f"\n5. Content verification:")
            print(f"   - First 100 chars: {retrieved.content[:100]}...")
            print(f"   - Last 100 chars: ...{retrieved.content[-100:]}")
            
            # Compare lengths
            if len(retrieved.content) == len(content):
                print(f"   ✓ Full content stored successfully ({len(content)} chars)")
            else:
                print(f"   ✗ Content truncated: stored {len(retrieved.content)}, expected {len(content)}")
        
        # Check metadata
        if retrieved.source_metadata:
            print(f"\n6. Metadata stored:")
            for key, value in retrieved.source_metadata.items():
                if value:
                    value_preview = str(value)[:50] + '...' if len(str(value)) > 50 else str(value)
                    print(f"   - {key}: {value_preview}")
        
        print("\n" + "=" * 50)
        print(f"Test complete! Document saved as ID: {document.id}")
        print(f"View at: http://localhost:8080/references/{document.id}")
        
        return document.id

if __name__ == "__main__":
    doc_id = test_full_upload_process()
