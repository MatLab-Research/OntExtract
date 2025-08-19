#!/usr/bin/env python3
"""
Test script for the Ontology Import Service.

This script demonstrates how to use the OntologyImporter to:
1. Import the PROV-O ontology
2. Extract classes and properties
3. Get experiment-relevant concepts
4. Import local ontology files

Author: OntExtract Team
Date: 2025-01-19
"""

import sys
import os
import json
import logging
from pprint import pprint

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared_services.ontology.ontology_importer import OntologyImporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_prov_o_import():
    """Test importing the PROV-O ontology."""
    print("\n" + "="*60)
    print("Testing PROV-O Import")
    print("="*60)
    
    # Create importer instance
    importer = OntologyImporter(cache_dir='./ontology_cache')
    
    # Import PROV-O
    print("\nImporting PROV-O ontology...")
    result = importer.import_prov_o(force_refresh=False)
    
    if result and result.get('success'):
        print(f"✓ Successfully imported PROV-O")
        print(f"  - Ontology ID: {result['ontology_id']}")
        print(f"  - Triple count: {result['metadata'].get('triple_count', 'N/A')}")
        print(f"  - Classes: {result['metadata'].get('class_count', 'N/A')}")
        print(f"  - Properties: {result['metadata'].get('property_count', 'N/A')}")
        
        # Show experiment concepts
        if 'experiment_concepts' in result:
            print("\n  Experiment-relevant concepts:")
            for category, concepts in result['experiment_concepts'].items():
                print(f"    - {category}: {len(concepts)} concepts")
                # Show first 3 concepts in each category
                for concept in concepts[:3]:
                    label = concept.get('label', concept.get('uri', 'Unknown'))
                    print(f"      • {label}")
                if len(concepts) > 3:
                    print(f"      ... and {len(concepts) - 3} more")
    else:
        print(f"✗ Failed to import PROV-O")
        if result:
            print(f"  Error: {result.get('error', 'Unknown error')}")
    
    return result


def test_local_ontology_import():
    """Test importing a local ontology file."""
    print("\n" + "="*60)
    print("Testing Local Ontology Import")
    print("="*60)
    
    # Create importer instance
    importer = OntologyImporter(cache_dir='./ontology_cache')
    
    # Check if BFO ontology exists locally
    bfo_path = '/home/chris/onto/OntExtract/ontologies/bfo.ttl'
    if os.path.exists(bfo_path):
        print(f"\nImporting local BFO ontology from {bfo_path}...")
        result = importer.import_from_file(
            bfo_path,
            ontology_id='bfo',
            name='Basic Formal Ontology',
            description='BFO is a top-level ontology designed for use in supporting information retrieval, analysis and integration in scientific and other domains.'
        )
        
        if result.get('success'):
            print(f"✓ Successfully imported BFO")
            print(f"  - Ontology ID: {result['ontology_id']}")
            print(f"  - Triple count: {result['metadata'].get('triple_count', 'N/A')}")
            print(f"  - Classes: {result['metadata'].get('class_count', 'N/A')}")
            print(f"  - Properties: {result['metadata'].get('property_count', 'N/A')}")
            
            # Extract some classes
            classes = importer.extract_classes('bfo')
            if classes:
                print(f"\n  Sample BFO classes (showing first 5):")
                for cls in classes[:5]:
                    label = cls.get('label', cls.get('uri', 'Unknown'))
                    print(f"    • {label}")
                if len(classes) > 5:
                    print(f"    ... and {len(classes) - 5} more")
        else:
            print(f"✗ Failed to import BFO")
            print(f"  Error: {result.get('error', 'Unknown error')}")
    else:
        print(f"  BFO ontology file not found at {bfo_path}")
        print("  Skipping local import test")
    
    return result if 'result' in locals() else None


def test_list_ontologies():
    """Test listing imported ontologies."""
    print("\n" + "="*60)
    print("Listing Imported Ontologies")
    print("="*60)
    
    importer = OntologyImporter(cache_dir='./ontology_cache')
    ontologies = importer.list_imported_ontologies()
    
    if ontologies:
        print(f"\nFound {len(ontologies)} imported ontologies:")
        for ont in ontologies:
            print(f"  • {ont.get('name', 'Unnamed')} (ID: {ont.get('ontology_id', 'N/A')})")
            if ont.get('description'):
                # Show first 100 chars of description
                desc = ont['description'][:100] + '...' if len(ont['description']) > 100 else ont['description']
                print(f"    {desc}")
    else:
        print("\nNo imported ontologies found in cache")


def test_extract_prov_classes():
    """Test extracting classes from PROV-O."""
    print("\n" + "="*60)
    print("Extracting PROV-O Classes and Properties")
    print("="*60)
    
    importer = OntologyImporter(cache_dir='./ontology_cache')
    
    # Make sure PROV-O is imported
    ont_data = importer.get_imported_ontology('prov-o')
    if not ont_data:
        print("PROV-O not found in cache, importing...")
        result = importer.import_prov_o()
        if not result or not result.get('success'):
            print("Failed to import PROV-O")
            return
    
    # Extract classes
    classes = importer.extract_classes('prov-o')
    print(f"\nFound {len(classes)} classes in PROV-O")
    
    # Show some important classes
    important_classes = ['Activity', 'Entity', 'Agent', 'Plan', 'Bundle', 'Collection']
    print("\nImportant PROV-O classes:")
    for cls in classes:
        label = cls.get('label')
        if label in important_classes:
            print(f"  • {label}")
            if cls.get('comment'):
                comment = cls['comment'][:150] + '...' if len(cls['comment']) > 150 else cls['comment']
                print(f"    {comment}")
    
    # Extract properties
    properties = importer.extract_properties('prov-o')
    print(f"\nFound {len(properties)} properties in PROV-O")
    
    # Show some important properties
    important_props = ['wasGeneratedBy', 'used', 'wasAssociatedWith', 'wasAttributedTo', 'wasDerivedFrom']
    print("\nImportant PROV-O properties:")
    for prop in properties:
        label = prop.get('label')
        if label and any(imp in label for imp in important_props):
            print(f"  • {label} ({prop['type']})")
            if prop.get('comment'):
                comment = prop['comment'][:150] + '...' if len(prop['comment']) > 150 else prop['comment']
                print(f"    {comment}")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Ontology Import Service Test Suite")
    print("="*60)
    
    try:
        # Test PROV-O import
        prov_result = test_prov_o_import()
        
        # Test local ontology import
        local_result = test_local_ontology_import()
        
        # List all imported ontologies
        test_list_ontologies()
        
        # Extract PROV-O classes and properties
        test_extract_prov_classes()
        
        print("\n" + "="*60)
        print("Test Suite Complete")
        print("="*60)
        
        # Summary
        print("\nSummary:")
        if prov_result and prov_result.get('success'):
            print("  ✓ PROV-O import successful")
        else:
            print("  ✗ PROV-O import failed")
        
        if local_result and local_result.get('success'):
            print("  ✓ Local ontology import successful")
        else:
            print("  ✗ Local ontology import failed or skipped")
        
        print("\nOntology cache directory: ./ontology_cache")
        print("You can now use these imported ontologies in your experiments!")
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
