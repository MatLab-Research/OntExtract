#!/usr/bin/env python3
"""
Test SPARQL queries against the Semantic Change Ontology in OntServe.
"""

import sys
import os
from pathlib import Path

# Add OntServe to path
sys.path.insert(0, '/home/chris/onto/OntServe')

from web.app import create_app
from web.models import db, Ontology, OntologyVersion
from rdflib import Graph, Namespace

def test_sparql_queries():
    """Test various SPARQL queries against the semantic change ontology"""

    app = create_app('development')

    with app.app_context():
        # Get the ontology
        ontology = db.session.query(Ontology).filter_by(
            name='semantic-change-ontology'
        ).first()

        if not ontology:
            print("❌ ERROR: semantic-change-ontology not found in database")
            return False

        print(f"✅ Found ontology: {ontology.name} (ID: {ontology.id})")
        print(f"   Base URI: {ontology.base_uri}")
        print(f"   Description: {ontology.description[:80]}...")

        # Get current version
        version = db.session.query(OntologyVersion).filter_by(
            ontology_id=ontology.id,
            is_current=True
        ).first()

        if not version:
            print("❌ ERROR: No current version found")
            return False

        print(f"\n✅ Found version: {version.version_tag}")

        # Parse RDF content
        graph = Graph()
        graph.parse(data=version.content, format='turtle')
        print(f"✅ Parsed ontology: {len(graph)} triples\n")

        # Define namespaces
        SCO = Namespace("http://ontextract.org/sco#")
        RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
        SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

        # Test Query 1: Get all semantic event types
        print("=" * 70)
        print("Query 1: List all semantic event type classes")
        print("=" * 70)

        query1 = """
        PREFIX sco: <http://ontextract.org/sco#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?eventType ?label ?comment
        WHERE {
            ?eventType rdfs:subClassOf* sco:SemanticChangeEvent .
            ?eventType rdfs:label ?label .
            OPTIONAL { ?eventType rdfs:comment ?comment }
        }
        ORDER BY ?label
        """

        results1 = graph.query(query1)
        print(f"\nFound {len(results1)} event types:\n")

        for row in results1:
            event_name = str(row.eventType).split('#')[-1]
            label = str(row.label)
            comment = str(row.comment) if row.comment else 'No description'
            print(f"  • {label} ({event_name})")
            print(f"    {comment[:80]}...")
            print()

        # Test Query 2: Get all properties
        print("=" * 70)
        print("Query 2: List all object and datatype properties")
        print("=" * 70)

        query2 = """
        PREFIX sco: <http://ontextract.org/sco#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT ?property ?label ?type ?comment
        WHERE {
            VALUES ?type { owl:ObjectProperty owl:DatatypeProperty }
            ?property a ?type .
            ?property rdfs:label ?label .
            OPTIONAL { ?property rdfs:comment ?comment }
            FILTER(STRSTARTS(STR(?property), "http://ontextract.org/sco#"))
        }
        ORDER BY ?type ?label
        """

        results2 = graph.query(query2)
        print(f"\nFound {len(results2)} properties:\n")

        current_type = None
        for row in results2:
            prop_type = str(row.type).split('#')[-1]
            if prop_type != current_type:
                current_type = prop_type
                print(f"\n{current_type}:")

            prop_name = str(row.property).split('#')[-1]
            label = str(row.label)
            print(f"  • {prop_name}: {label}")
            if row.comment:
                print(f"    {str(row.comment)[:80]}...")

        # Test Query 3: Get examples
        print("\n" + "=" * 70)
        print("Query 3: Extract examples from SKOS annotations")
        print("=" * 70)

        query3 = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?class ?label ?example
        WHERE {
            ?class skos:example ?example .
            ?class rdfs:label ?label .
        }
        ORDER BY ?label
        """

        results3 = graph.query(query3)
        print(f"\nFound {len(results3)} examples:\n")

        for row in results3:
            label = str(row.label)
            example = str(row.example)
            print(f"  • {label}:")
            print(f"    {example}")
            print()

        # Verify structure
        print("=" * 70)
        print("Ontology Structure Verification")
        print("=" * 70)

        # Count classes
        classes_query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT (COUNT(?class) as ?count)
        WHERE {
            ?class a owl:Class .
        }
        """
        class_count = list(graph.query(classes_query))[0][0]

        # Count properties
        props_query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT (COUNT(?prop) as ?count)
        WHERE {
            { ?prop a owl:ObjectProperty }
            UNION
            { ?prop a owl:DatatypeProperty }
        }
        """
        prop_count = list(graph.query(props_query))[0][0]

        print(f"\n✅ Classes: {class_count}")
        print(f"✅ Properties: {prop_count}")
        print(f"✅ Total triples: {len(graph)}")

        print("\n✅ All SPARQL tests completed successfully!")
        return True

if __name__ == '__main__':
    try:
        success = test_sparql_queries()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
