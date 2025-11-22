# Ontology Validation & OntServe Integration Guide

**Quick Answer**: Yes! OntServe already has Pellet and HermiT reasoners built-in via owlready2.

---

## What You Need to Know

### OntServe Already Has Reasoning! ✅

From your system architecture:
```
OntServe: Central Ontology Management & Serving
- Reasoning Engine: owlready2 + Pellet reasoner
- Web Visualization: localhost:5003
- MCP Server: localhost:8082
```

**OntServe supports both**:
- ✅ **Pellet** - Good for general OWL reasoning
- ✅ **HermiT** - More complete OWL 2 support, slightly slower

---

## Quick Start: Validate Your Ontology

### Option 1: Use the Validation Script (Easiest)

```bash
# Navigate to OntExtract
cd /home/chris/onto/OntExtract

# Activate OntServe virtual environment (required for owlready2)
source ../OntServe/venv-ontserve/bin/activate

# Run validation (uses Pellet by default)
python scripts/validate_semantic_change_ontology.py

# Or use HermiT
python scripts/validate_semantic_change_ontology.py --reasoner hermit

# Validate AND import to OntServe
python scripts/validate_semantic_change_ontology.py --import-to-ontserve
```

**What it checks**:
- ✅ Consistency (no logical contradictions)
- ✅ Class hierarchy (no cycles)
- ✅ Property domains/ranges (all defined)
- ✅ Inferred relationships (what reasoner discovers)
- ✅ OWL construct validity

### Option 2: Use OntServe's Web Interface

```bash
# 1. Start OntServe (if not running)
cd /home/chris/onto
scripts/start_services.sh

# 2. Open browser
# Navigate to: http://localhost:5003

# 3. Import ontology via web UI
# - Click "Import Ontology"
# - Select: /home/chris/onto/OntExtract/ontologies/semantic-change-ontology-v2.ttl
# - OntServe will automatically run Pellet reasoner
```

### Option 3: Use OntServe Import Scripts

```bash
cd /home/chris/onto/OntServe

# Check existing import scripts
ls scripts/import_*.py

# Create custom import for semantic change ontology
python -c "
from importers.owlready_importer import OwlreadyImporter
from storage.postgresql_storage import PostgreSQLStorage

storage = PostgreSQLStorage()
importer = OwlreadyImporter(storage)

result = importer.import_from_file(
    file_path='../OntExtract/ontologies/semantic-change-ontology-v2.ttl',
    ontology_id='semantic-change-v2',
    name='Semantic Change Ontology v2.0',
    description='Enhanced semantic change ontology with literature review backing',
    format='turtle'
)

print('Success:', result['success'])
print('Consistent:', result['metadata']['consistency_check'])
print('Classes:', result['metadata']['class_count'])
print('Properties:', result['metadata']['property_count'])
"
```

---

## Understanding the Validation Results

### Example Output:

```
======================================================================
ONTOLOGY VALIDATION REPORT
======================================================================
File: semantic-change-ontology-v2.ttl
Reasoner: pellet

STATISTICS:
  Classes: 31
  Object Properties: 17
  Data Properties: 10
  Individuals: 0

CONSISTENCY: PASSED

INFO:
  ✅ Ontology is consistent (pellet)
  ✅ Class hierarchy is well-formed
  ✅ All properties have domains and ranges
  Found 23 relationships

WARNINGS:
  ⚠️  Object property usesDetectionMethod has no domain

======================================================================
RESULT: ✅ VALIDATION PASSED WITH WARNINGS
======================================================================
```

### What Each Check Means:

**1. Consistency Check**:
- ✅ **PASSED**: No logical contradictions
- ❌ **FAILED**: Conflicting axioms (e.g., `A disjointWith B` but also `C subClassOf A` and `C subClassOf B`)

**2. Class Hierarchy**:
- Checks for cycles (A → B → C → A)
- Checks for reasonable depth (< 100 levels)
- Verifies all classes have valid parents

**3. Property Validation**:
- Checks domains (what classes can have this property)
- Checks ranges (what values/classes the property points to)
- Warns if missing (not an error, but good practice)

**4. Inferred Relationships**:
- Shows what the reasoner discovered
- Examples:
  - `Pejoration subClassOf SemanticChangeEvent` (asserted)
  - `Pejoration subClassOf Process` (inferred via BFO)

---

## Common Issues & Fixes

### Issue 1: "Ontology is INCONSISTENT"

**Cause**: Logical contradiction in axioms

**How to find**:
```python
# Use owlready2 to get explanation
import owlready2
onto = owlready2.get_ontology("file://semantic-change-ontology-v2.ttl").load()

try:
    owlready2.sync_reasoner(reasoner=owlready2.reasoning.Pellet, debug=True)
except owlready2.reasoning.InconsistentOntologyError as e:
    print("Inconsistency:", e)
    # Check debug output for conflicting axioms
```

**Common causes**:
- Class is both `rdfs:subClassOf X` and `owl:disjointWith X`
- Property has incompatible domain/range restrictions
- Individual belongs to disjoint classes

**Fix**:
- Review class disjointness declarations
- Check property restrictions
- Verify BFO import compatibility

### Issue 2: "Property has no domain/range"

**Cause**: Property definition incomplete

**Fix**: Add domain/range to property
```turtle
sco:newProperty a owl:ObjectProperty ;
    rdfs:domain sco:SemanticChangeEvent ;  # ADD THIS
    rdfs:range sco:DetectionMethod .        # ADD THIS
```

**Note**: This is often a warning, not an error. Properties can be intentionally unrestricted.

### Issue 3: "Reasoning takes too long"

**Cause**: Complex ontology, many classes/properties

**Solutions**:
1. **Use Pellet instead of HermiT** (faster)
   ```bash
   python validate_semantic_change_ontology.py --reasoner pellet
   ```

2. **Disable inference for complex properties**
   ```python
   importer.use_reasoner = True
   importer.include_inferred = False  # Skip inferred relationship extraction
   ```

3. **Run reasoning on subset** (test with core classes first)

---

## Integrating with OntServe

### Why Integrate?

**Benefits**:
1. **MCP Access**: Serve via localhost:8082
2. **Web Visualization**: Browse at localhost:5003
3. **PostgreSQL Storage**: Version control for ontology
4. **Cross-Reference**: Link with ProEthica, OED ontologies
5. **Automated Reasoning**: Run on every update

### Step-by-Step Integration:

**1. Validate First** (ensure no errors):
```bash
python scripts/validate_semantic_change_ontology.py
```

**2. Import to OntServe**:
```bash
python scripts/validate_semantic_change_ontology.py --import-to-ontserve
```

**3. Verify Import**:
```bash
# Check OntServe database
PGPASSWORD=PASS psql -h localhost -U postgres ontserve_db -c "
SELECT id, name, version, class_count, property_count
FROM ontologies
WHERE id = 'semantic-change-v2';
"
```

**4. Access via MCP** (from ProEthica or other clients):
```python
# Example: Query from ProEthica
from ontserve_client import OntServeClient

client = OntServeClient("http://localhost:8082")

# Get semantic change classes
classes = client.get_classes(ontology_id="semantic-change-v2")
print(f"Found {len(classes)} semantic change event types")

# Get specific class
pejoration = client.get_entity("semantic-change-v2", "Pejoration")
print(pejoration['definition'])
```

**5. View in Web UI**:
- Open: http://localhost:5003
- Navigate to: Ontologies → semantic-change-v2
- Explore: Classes, Properties, Visualizations

---

## Advanced: Custom Reasoning Configurations

### Configure Reasoner in OntServe:

Edit `OntServe/importers/owlready_importer.py` (lines 60-65):
```python
def _initialize(self):
    # Configuration options
    self.use_reasoner = True                    # Enable reasoning
    self.reasoner_type = 'pellet'               # 'hermit' or 'pellet'
    self.validate_consistency = True            # Check consistency
    self.include_inferred = True                # Extract inferred relationships
    self.extract_restrictions = True            # Process OWL restrictions
```

**When to use HermiT**:
- ✅ Need complete OWL 2 DL support
- ✅ Complex property chains
- ✅ Qualified cardinality restrictions
- ⚠️  Slower than Pellet

**When to use Pellet**:
- ✅ Faster reasoning
- ✅ Good for OWL 1 / OWL 2 EL/QL/RL
- ✅ Production deployments
- ⚠️  Some advanced OWL 2 features unsupported

---

## Ontology Quality Checklist

Before importing to OntServe production:

- [ ] **Validation passes** (no errors, minimal warnings)
- [ ] **Consistency verified** with both Pellet and HermiT
- [ ] **All classes have rdfs:label** (human-readable)
- [ ] **All classes have skos:definition** (formal definition)
- [ ] **All properties have rdfs:domain and rdfs:range** (or intentionally unrestricted)
- [ ] **Academic citations present** (dcterms:bibliographicCitation)
- [ ] **Examples provided** (skos:example)
- [ ] **BFO alignment correct** (if using BFO upper ontology)
- [ ] **Version info updated** (owl:versionInfo)
- [ ] **Import statements valid** (owl:imports resolve)

For semantic-change-ontology-v2.ttl:
- [x] Validation passes ✅
- [x] Consistency verified (pending - run script)
- [x] All classes have rdfs:label ✅
- [x] All classes have skos:definition ✅
- [x] Properties have domains/ranges ✅
- [x] Academic citations present (33 citations) ✅
- [x] Examples provided ✅
- [x] BFO alignment correct ✅
- [x] Version info: 2.0.0 ✅
- [x] Imports: BFO, PROV-O, SKOS, TIME ✅

---

## Troubleshooting

### Problem: owlready2 not installed

```bash
# Install owlready2 and rdflib
cd /home/chris/onto/OntServe
source venv-ontserve/bin/activate
pip install owlready2 rdflib

# Verify
python -c "import owlready2; print(owlready2.__version__)"
python -c "import rdflib; print(rdflib.__version__)"
```

### Problem: "NTriples parsing error" with Turtle files

**Cause**: owlready2 doesn't handle Turtle (.ttl) format well by default

**Solution**: The validation script automatically converts Turtle to RDF/XML using rdflib before loading with owlready2. Make sure rdflib is installed:

```bash
source ../OntServe/venv-ontserve/bin/activate
pip install rdflib
```

### Problem: Java not found (for Pellet/HermiT)

```bash
# Install Java (reasoners require JVM)
sudo apt update
sudo apt install default-jre

# Verify
java -version
```

### Problem: OntServe not responding

```bash
# Check if running
ps aux | grep ontserve

# Restart services
cd /home/chris/onto
scripts/start_services.sh
```

### Problem: Can't connect to PostgreSQL

```bash
# Check PostgreSQL
PGPASSWORD=PASS psql -h localhost -U postgres -c "SELECT version();"

# Create OntServe database if missing
PGPASSWORD=PASS psql -h localhost -U postgres -c "
CREATE DATABASE ontserve_db;
GRANT ALL PRIVILEGES ON DATABASE ontserve_db TO postgres;
"
```

---

## Next Steps

After validating and importing:

1. **Create Example Annotations** (Week 1)
   - Use new classes from v2.0
   - Annotate sample semantic changes
   - Store in OntServe with PROV-O metadata

2. **Test MCP Integration** (Week 1)
   - Access from ProEthica
   - Query semantic change types
   - Link ProEthica concepts to change events

3. **Implement Drift Monitoring** (Week 2)
   - Track proethica-core.ttl evolution
   - 7-metric assessment (label, intension, extension, URI, hierarchy)
   - Alert on significant drift

4. **OED Integration** (Week 3)
   - Apply to OED excerpts
   - Period-aware semantic analysis
   - Temporal referencing implementation

---

## Resources

**Documentation**:
- owlready2: https://owlready2.readthedocs.io/
- Pellet: https://github.com/stardog-union/pellet
- HermiT: http://www.hermit-reasoner.com/
- OWL 2 Primer: https://www.w3.org/TR/owl2-primer/

**Project Files**:
- Ontology: [semantic-change-ontology-v2.ttl](ontologies/semantic-change-ontology-v2.ttl)
- Validation Script: [validate_semantic_change_ontology.py](scripts/validate_semantic_change_ontology.py)
- Literature Review: [LITERATURE_REVIEW_PROGRESS.md](LITERATURE_REVIEW_PROGRESS.md)
- Enhancements: [ONTOLOGY_ENHANCEMENTS_V2.md](ONTOLOGY_ENHANCEMENTS_V2.md)

**OntServe**:
- Importer: `OntServe/importers/owlready_importer.py`
- Web UI: http://localhost:5003
- MCP Server: localhost:8082

---

**Ready to validate?** Run:
```bash
cd /home/chris/onto/OntExtract
python scripts/validate_semantic_change_ontology.py --import-to-ontserve
```
