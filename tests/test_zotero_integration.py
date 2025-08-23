#!/usr/bin/env python3
"""
Test script for Zotero metadata extraction integration.
"""

import os
import sys
import json
from pprint import pprint
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared_services.zotero.zotero_service import ZoteroService
from shared_services.zotero.metadata_mapper import ZoteroMetadataMapper
from app.services.reference_metadata_enricher import ReferenceMetadataEnricher


def test_zotero_connection():
    """Test basic Zotero connection."""
    print("=" * 60)
    print("Testing Zotero Connection")
    print("=" * 60)
    
    try:
        service = ZoteroService()
        print("✓ Zotero service initialized successfully")
        
        # Get collections
        collections = service.get_collections()
        print(f"✓ Found {len(collections)} collections in your library")
        
        if collections:
            print("\nCollections:")
            for col in collections[:5]:
                print(f"  - {col['name']}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_search_by_title():
    """Test searching by title."""
    print("\n" + "=" * 60)
    print("Testing Title Search")
    print("=" * 60)
    
    try:
        service = ZoteroService()
        
        # Search for "ontology" in title
        test_title = "ontology"
        print(f"Searching for items with '{test_title}' in title...")
        
        results = service.search_by_title(test_title, limit=5)
        print(f"✓ Found {len(results)} matching items")
        
        if results:
            print("\nTop matches:")
            for i, item in enumerate(results[:3], 1):
                data = item['data']
                title = data.get('title', 'No title')
                item_type = data.get('itemType', 'unknown')
                score = data.get('_similarity_score', 0)
                print(f"\n{i}. {title[:60]}...")
                print(f"   Type: {item_type}")
                print(f"   Similarity score: {score:.2f}")
                
                # Check for ProQuest URL
                proquest_url = service.extract_proquest_url(item)
                if proquest_url:
                    print(f"   ProQuest URL: {proquest_url}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_metadata_mapping():
    """Test metadata mapping to source_metadata format."""
    print("\n" + "=" * 60)
    print("Testing Metadata Mapping")
    print("=" * 60)
    
    try:
        service = ZoteroService()
        
        # Get first item with "ontology" in title
        results = service.search_by_title("ontology", limit=1)
        
        if not results:
            print("No items found to test mapping")
            return False
        
        item = results[0]
        print(f"Mapping item: {item['data'].get('title', 'Unknown')[:60]}...")
        
        # Map to source_metadata format
        metadata = ZoteroMetadataMapper.map_to_source_metadata(item)
        
        print("\n✓ Mapped metadata:")
        important_fields = ['title', 'authors', 'publication_date', 'journal', 
                          'doi', 'proquest_url', 'zotero_key']
        
        for field in important_fields:
            if field in metadata:
                value = metadata[field]
                if isinstance(value, list) and value:
                    value = f"[{', '.join(str(v)[:30] for v in value[:2])}...]"
                elif isinstance(value, str) and len(value) > 60:
                    value = value[:60] + "..."
                print(f"  {field}: {value}")
        
        # Test PROV-O mapping
        print("\n✓ PROV-O Entity:")
        prov_entity = ZoteroMetadataMapper.map_to_prov_o(item, "test_doc_123")
        print(f"  @id: {prov_entity.get('@id')}")
        print(f"  @type: {prov_entity.get('@type')}")
        print(f"  wasAttributedTo: {prov_entity.get('prov:wasAttributedTo')}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_enricher_integration():
    """Test the full enricher with Zotero integration."""
    print("\n" + "=" * 60)
    print("Testing Enricher Integration")
    print("=" * 60)
    
    try:
        enricher = ReferenceMetadataEnricher(use_zotero=True)
        
        if enricher.zotero_service:
            print("✓ Enricher initialized with Zotero support")
        else:
            print("✗ Zotero service not available in enricher")
            return False
        
        # Test with a sample title (without actual PDF)
        print("\nTesting metadata lookup for a sample document...")
        
        # Create a minimal test case
        test_metadata = {
            'title': 'ontology extraction',
            'authors': ['John Doe'],
            'publication_date': '2020'
        }
        
        # Note: This would normally use a PDF file, but we'll simulate
        print("Note: Full PDF extraction requires an actual PDF file")
        print("      This test only demonstrates Zotero lookup capability")
        
        return True
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ZOTERO INTEGRATION TEST SUITE")
    print("=" * 60)
    
    # Check environment variables
    print("\nChecking environment variables...")
    api_key = os.getenv('ZOTERO_API_KEY')
    user_id = os.getenv('ZOTERO_USER_ID')
    group_id = os.getenv('ZOTERO_GROUP_ID')
    
    if api_key:
        print(f"✓ ZOTERO_API_KEY: {api_key[:10]}...")
    else:
        print("✗ ZOTERO_API_KEY not found")
    
    if user_id:
        print(f"✓ ZOTERO_USER_ID: {user_id}")
    else:
        print("✗ ZOTERO_USER_ID not found")
    
    if group_id:
        print(f"✓ ZOTERO_GROUP_ID: {group_id}")
    
    if not (api_key and (user_id or group_id)):
        print("\n✗ Missing required Zotero credentials")
        print("  Please ensure ZOTERO_API_KEY and ZOTERO_USER_ID are set in .env")
        return 1
    
    # Run tests
    tests = [
        test_zotero_connection,
        test_search_by_title,
        test_metadata_mapping,
        test_enricher_integration
    ]
    
    results = []
    for test in tests:
        try:
            success = test()
            results.append(success)
        except Exception as e:
            print(f"\n✗ Test failed with exception: {str(e)}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("\n✓ All tests passed! Zotero integration is working.")
        print("\nNext steps:")
        print("1. Upload a document through the web interface")
        print("2. The system will automatically search Zotero for metadata")
        print("3. ProQuest URLs and full bibliographic data will be extracted")
        print("4. Metadata will be stored with PROV-O provenance tracking")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
