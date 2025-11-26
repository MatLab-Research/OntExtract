#!/usr/bin/env python3
"""
Test OntServe Client Integration

Verifies that the MCP integration layer and OntServe client
can successfully fetch semantic change event types from the ontology.
"""

import sys
sys.path.insert(0, '/home/chris/onto/OntExtract')

from app.services.ontserve_client import get_ontserve_client
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

def test_ontserve_client():
    """Test fetching event types from semantic change ontology"""

    print("=" * 70)
    print("Testing OntServe Client Integration")
    print("=" * 70)

    # Get client instance
    client = get_ontserve_client()
    print(f"\n✅ OntServe client initialized")
    print(f"   Namespace: {client.namespace}")
    print(f"   Ontology: {client.ontology_name}")

    # Test 1: Fetch event types
    print("\n" + "=" * 70)
    print("Test 1: Fetch Semantic Event Types")
    print("=" * 70)

    try:
        event_types = client.get_event_types()
        print(f"\n✅ Fetched {len(event_types)} event types:\n")

        for event in event_types:
            print(f"  • {event['label']} ({event['name']})")
            print(f"    URI: {event['uri']}")
            print(f"    Color: {event['color']}")
            print(f"    Icon: {event['icon']}")
            print(f"    Description: {event['description'][:80]}...")

            if event.get('examples'):
                print(f"    Examples:")
                for example in event['examples'][:2]:
                    print(f"      - {example[:80]}...")
            print()

    except Exception as e:
        print(f"❌ ERROR: Failed to fetch event types: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Validate URIs
    print("=" * 70)
    print("Test 2: Validate Event URIs")
    print("=" * 70)

    test_uris = [
        f"{client.namespace}InflectionPoint",
        f"{client.namespace}StablePolysemy",
        f"{client.namespace}InvalidEvent"
    ]

    for uri in test_uris:
        try:
            is_valid = client.validate_event_uri(uri)
            status = "✅ VALID" if is_valid else "❌ INVALID"
            print(f"  {status}: {uri}")
        except Exception as e:
            print(f"  ❌ ERROR validating {uri}: {e}")

    # Test 3: Fetch properties
    print("\n" + "=" * 70)
    print("Test 3: Fetch SCO Properties")
    print("=" * 70)

    try:
        properties = client.get_properties()
        print(f"\n✅ Fetched {len(properties)} properties:\n")

        # Group by type
        object_props = [p for p in properties if p['type'] == 'ObjectProperty']
        datatype_props = [p for p in properties if p['type'] == 'DatatypeProperty']

        print(f"Object Properties ({len(object_props)}):")
        for prop in object_props[:5]:  # Show first 5
            print(f"  • {prop['name']}: {prop['label']}")

        print(f"\nDatatype Properties ({len(datatype_props)}):")
        for prop in datatype_props:
            print(f"  • {prop['name']}: {prop['label']}")
            print(f"    Range: {prop.get('range', 'N/A')}")

    except Exception as e:
        print(f"❌ ERROR: Failed to fetch properties: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)

    return True


if __name__ == '__main__':
    try:
        success = test_ontserve_client()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
