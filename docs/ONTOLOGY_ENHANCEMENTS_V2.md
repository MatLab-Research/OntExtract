# Semantic Change Ontology V2.0 - Literature-Backed Enhancements

**Date**: 2025-11-22
**Based on**: Comprehensive review of 12 academic papers
**Documentation**: [LITERATURE_REVIEW_PROGRESS.md](LITERATURE_REVIEW_PROGRESS.md)

## Summary

Version 2.0 adds **23 new classes**, **10 new object properties**, and **6 new datatype properties** based on findings from lexical semantic change and ontology drift literature. All additions have explicit academic citations.

---

## New Classes Added (23 total)

### 1. Sentiment Change Types (Jatowt & Duh 2014)

**Academic Backing**: Jatowt & Duh (2014). Framework for analyzing semantic change. JCDL '14. Bloomfield (1933) nine classes.

| Class | Definition | Example |
|-------|------------|---------|
| `sco:Pejoration` | Semantic change toward negative sentiment | "propaganda" acquired negative connotations |
| `sco:Amelioration` | Semantic change toward positive sentiment | "aggressive" positive in business context |

**Why Added**: Paper demonstrates three-level framework (lexical, contrastive-pair, **sentiment orientation**). Pejoration/amelioration are well-established linguistic categories with empirical backing.

---

### 2. Linguistic vs Cultural Change (Kutuzov 2018)

**Academic Backing**: Kutuzov et al. (2018). Diachronic word embeddings and semantic shifts: a survey. COLING.

| Class | Definition | Example |
|-------|------------|---------|
| `sco:LinguisticDrift` | Language-internal, slow core meaning change | Subclass of SemanticDrift |
| `sco:CulturalShift` | External cultural/social associations change | Iraq/Syria → war associations |

**Why Added**: Paper establishes critical distinction: linguistic drifts are "slow and regular changes in core meaning" while cultural shifts are "culturally determined changes in associations." Different detection methods work better for each type (global vs. local measures).

---

### 3. Ontology Drift Types (Gulla 2010, Stavropoulos 2019, Capobianco 2020)

**Academic Backing**:
- Gulla et al. (2010). Semantic Drift in Ontologies. WEBIST.
- Stavropoulos et al. (2019). SemaDrift. Journal of Web Semantics.
- Capobianco et al. (2020). OntoDrift. MEPDaW@ISWC.
- Wang et al. (2009, 2011). Framework cited by above papers.

#### Intrinsic vs Extrinsic (Gulla 2010)

| Class | Definition | Key Insight |
|-------|------------|-------------|
| `sco:IntrinsicDrift` | Change relative to other ontology concepts | Reflected in relationship modifications |
| `sco:ExtrinsicDrift` | Change relative to real-world phenomena | May not require ontology changes |
| `sco:CollectiveDrift` | Whole ontology drifts together | Domain evolved but ontology consistent |

**Why Added**: **PIONEERING DISTINCTION**. First formal separation of concept-relative vs. reality-relative drift. Critical for distinguishing "concept changed" from "domain understanding changed."

#### Three-Aspect Framework (Wang 2009/2011, Stavropoulos 2019)

| Class | Definition | Measurement |
|-------|------------|-------------|
| `sco:LabelDrift` | Changes in rdfs:label (naming) | Monge-Elkan string similarity |
| `sco:IntensionalDrift` | Changes in properties (characteristics) | Jaccard similarity (property sets) |
| `sco:ExtensionalDrift` | Changes in instances (things extended to) | Jaccard similarity (instance sets) |

**Why Added**: **WIDELY ADOPTED FRAMEWORK**. Wang et al. (2009, 2011) introduced three aspects, Stavropoulos (2019) operationalized with metrics. Empirically validated on Tate Galleries (2003-2013) and OWL-S Web Services ontologies.

#### Structural Drift (Capobianco 2020)

| Class | Definition | OWL Element |
|-------|------------|-------------|
| `sco:StructuralDrift` | Changes to ontology structure | Parent class |
| `sco:URIDrift` | Identifier changes | URI modifications |
| `sco:SubclassDrift` | Taxonomic children changes | rdfs:subClassOf (below) |
| `sco:SuperclassDrift` | Taxonomic parent changes | rdfs:subClassOf (above) |
| `sco:EquivalentClassDrift` | Equivalence mapping changes | owl:equivalentClass |

**Why Added**: **EXTENDS SEMADRIFT**. Capobianco (2020) adds 4 OWL-specific metrics to the 3 Wang metrics. Creates comprehensive **7-metric drift assessment framework**. Critical for RDF/OWL ontology evolution tracking.

---

### 4. Lexical Lifecycle (Tahmasebi 2021)

**Academic Backing**: Tahmasebi et al. (2021). Survey of computational approaches to lexical semantic change detection. Language Science Press.

| Class | Definition | Direct Quote |
|-------|------------|--------------|
| `sco:LexicalEmergence` | New word coined/borrowed | "new words are coined or borrowed from other languages" |
| `sco:LexicalObsolescence` | Word becomes archaic | "obsolete words slide into obscurity" |
| `sco:LexicalReplacement` | One word supplants another | Vocabulary turnover patterns |

**Why Added**: **COMPREHENSIVE SURVEY** (91 pages). Synthesizes field consensus on lexical lifecycle events. Distinguishes emergence/decline of **words** from emergence/decline of **meanings**.

---

### 5. Granularity Levels (Montariol 2021)

**Academic Backing**: Montariol et al. (2021). Scalable and Interpretable Semantic Change Detection. NAACL.

| Class | Definition | Approach |
|-------|------------|----------|
| `sco:WordLevelChange` | Aggregate across all senses | Traditional approach |
| `sco:SenseLevelChange` | Specific word usage/sense | Cluster-based, fine-grained |

**Why Added**: **SCALABILITY BREAKTHROUGH**. Enables sense-level analysis across full vocabulary (not pre-selected words). Validated on COHA, SEMEVAL, COVID-19 corpus. Addresses critical limitation of prior cluster-based methods.

---

### 6. Detection Method Classes (Multiple Papers)

**Academic Backing**: Integration of methodological approaches from Papers 1-10.

| Class | Definition | Key Reference |
|-------|------------|---------------|
| `sco:DetectionMethod` | Parent class for methods | Methodology taxonomy |
| `sco:TemporalReferencingMethod` | Single vector space, temporal tags | Dubossarsky et al. (2019) |
| `sco:AlignmentBasedMethod` | Align embeddings across time | Hamilton et al. (2016), artifacts noted |
| `sco:ClusterBasedMethod` | Cluster contextual embeddings | Montariol et al. (2021) |
| `sco:SignatureBasedMethod` | Usage pattern signatures | Gulla et al. (2010) |
| `sco:HybridMethod` | Combines multiple approaches | Stavropoulos et al. (2019) |

**Why Added**: **METHODOLOGY TRACKING**. Different methods detect different types of changes. Critical for:
- Reproducibility (what method was used?)
- Method comparison (which works best for what?)
- Artifact awareness (alignment vs. temporal referencing)

---

## New Object Properties (10 total)

### Causation (Tahmasebi 2021)

| Property | Definition | Reference |
|----------|------------|-----------|
| `sco:hasCause` | Parent property for causes | Tahmasebi survey |
| `sco:hasExternalCause` | Cultural, societal, technological | "external factors such as..." |
| `sco:hasInternalCause` | Linguistic motivations | "only partially understood internal motivations" |

**Why Added**: Survey identifies external/internal distinction as fundamental. External = cultural/societal/technological. Internal = linguistic patterns.

### Sense-Level Analysis (Montariol 2021)

| Property | Definition | Use Case |
|----------|------------|----------|
| `sco:hasSenseCluster` | Links to embedding cluster | Sense-level changes |

**Why Added**: Enables linking semantic change events to specific sense clusters identified via contextual embedding clustering.

### Methodology Validation (Dubossarsky 2017/2019)

| Property | Definition | Critical Insight |
|----------|------------|------------------|
| `sco:usesDetectionMethod` | Method used for detection | Track which method |
| `sco:hasControlCondition` | Reference to null condition | Validate genuine vs. artifact |

**Why Added**: **ARTIFACT AWARENESS**. Dubossarsky (2017) showed Hamilton's "laws" are largely artifacts. Control conditions required to distinguish genuine patterns from model biases.

### Multi-Source Integration (Maree & Belkhatir 2015)

| Property | Definition | Approach |
|----------|------------|----------|
| `sco:usesExternalKnowledgeBase` | External source consulted | Aggregated decisions |

**Why Added**: Multi-source aggregation more robust than single-source. Relevant for OntServe integration (multiple ontologies).

### D-PROV Integration (Missier 2013)

| Property | Definition | Provenance Type |
|----------|------------|-----------------|
| `sco:hasWorkflowStructure` | Links to process design | Prospective |
| `sco:hasProcessSpecification` | HOW change should be detected | Prospective |
| `sco:hasExecutionTrace` | WHAT was actually detected | Retrospective |

**Why Added**: **DIRECTLY APPLICABLE TO ONTEXTRACT**. OntExtract already uses PROV-O for LLM orchestration. D-PROV extends with workflow structure. Enables:
- Reproducibility (replay workflows)
- Method comparison (different process specifications)
- Long-term preservation (DataONE model)

---

## New Datatype Properties (6 total)

| Property | Type | Definition | Reference |
|----------|------|------------|-----------|
| `sco:hasSentimentDirection` | string | pejoration, amelioration, neutral | Jatowt & Duh (2014) |
| `sco:hasTemporalScale` | string | centuries, decades, years, months | Montariol (2021) COVID vs COHA |
| `sco:passesControlTest` | boolean | Observed in genuine but not control | Dubossarsky (2017) |
| `sco:controlledForArtifacts` | boolean | Frequency/polysemy controlled | Dubossarsky (2019) |
| `sco:hasURIStability` | float | Identifier consistency (0.0-1.0) | Capobianco (2020) |
| `sco:isSynthetic` | boolean | Simulated vs. authentic change | Dubossarsky (2019) |

**Why Added**: Capture critical metadata for semantic change events. Essential for quality assessment and method validation.

---

## Enhanced Annotation Guidelines

Version 2.0 guidelines now include:

1. **27 Event Types** (up from 7):
   - Original 7 types (v1.0)
   - 2 sentiment types
   - 2 linguistic types
   - 11 ontology drift types
   - 3 lexical lifecycle types
   - 2 granularity types

2. **Evidence Requirements**:
   - Added: Control condition testing (Dubossarsky)
   - Enhanced: Statistical significance levels

3. **Detection Method Tracking** (NEW):
   - REQUIRED for reproducibility
   - Method class specification
   - Artifact control documentation
   - Synthetic vs. authentic distinction

4. **Provenance Tracking** (NEW - D-PROV):
   - Prospective: HOW change should be detected
   - Retrospective: WHAT was actually detected
   - Enables method comparison and reproducibility

5. **Cause Attribution** (NEW):
   - External vs. internal causes
   - Evidence requirements for causal claims

6. **Academic References** (REQUIRED):
   - Cite supporting literature in dcterms:bibliographicCitation
   - Include DOI/permanent URL
   - Page numbers for direct quotes

---

## Backward Compatibility

**FULLY BACKWARD COMPATIBLE**: All v1.0 classes and properties retained. New additions are:
- Subclasses of existing classes
- New sibling classes
- New properties (don't conflict with existing)

**Migration**: No changes needed to existing annotations. They remain valid v2.0 annotations.

---

## Academic Rigor Summary

### Papers Integrated

**Semantic Change (Lexical):**
1. ✅ Hamilton et al. (2016) - Statistical laws
2. ✅ Kutuzov et al. (2018) - Survey
3. ⚠️ Jatowt & Duh (2014) - Three-level framework
4. ✅ Dubossarsky et al. (2019) - Temporal referencing
5. ⚠️ Montariol et al. (2021) - Scalable clustering
6. ✅ Tahmasebi et al. (2021) - Comprehensive survey

**Ontology Drift:**
7. ✅ Stavropoulos et al. (2019) - SemaDrift
8. ⚠️ Gulla et al. (2010) - Intrinsic/extrinsic
9. ⚠️ Capobianco et al. (2020) - OntoDrift
10. ⚠️ Stavropoulos et al. (2016) - Framework predecessor

**Related:**
11. ⚠️ Maree & Belkhatir (2015) - Semantic heterogeneity
12. ✅ Missier et al. (2013) - D-PROV

### Citation Coverage

- **23 new classes**: ALL have dcterms:bibliographicCitation
- **10 new properties**: ALL have citations in comments
- **Annotation guidelines**: Reference specific papers and sections

### Validation

**Empirical Backing**:
- Tate Galleries ontology (Stavropoulos 2019)
- OWL-S Web Services (Stavropoulos 2019)
- COHA, SEMEVAL, DURel datasets (Montariol 2021)
- COVID-19 corpus (Montariol 2021)
- DataONE scientific workflows (Missier 2013)

**Methodological Validation**:
- Control conditions (Dubossarsky 2017/2019)
- Synthetic tasks (Dubossarsky 2019)
- Manual test sets (multiple papers)
- Cross-lingual validation (Kutuzov 2018)

---

## Next Steps

1. **Testing**: Validate v2.0 ontology with reasoning (Pellet, HermiT)
2. **Example Annotations**: Create sample instances using new classes
3. **Integration**: Connect to OntExtract PROV-O implementation
4. **Documentation**: Add usage examples to each new class
5. **OntServe**: Import v2.0 into OntServe for serving via MCP

---

## Files

- **Ontology**: [semantic-change-ontology-v2.ttl](ontologies/semantic-change-ontology-v2.ttl)
- **Literature Review**: [LITERATURE_REVIEW_PROGRESS.md](LITERATURE_REVIEW_PROGRESS.md)
- **This Document**: [ONTOLOGY_ENHANCEMENTS_V2.md](ONTOLOGY_ENHANCEMENTS_V2.md)

---

**Status**: ✅ COMPLETE - All literature review findings synthesized into ontology v2.0
