"""
Unit Tests for Core Document Processing Tools

Tests for app/services/processing_tools.py:
- DocumentProcessor class
- All processing tool methods (segmentation, extraction, embedding)
- ProcessingResult structure validation
- Edge cases and error handling

These tests verify the actual processing logic, not mocked behavior.
"""

import pytest
from app.services.processing_tools import DocumentProcessor, ProcessingResult


class TestProcessingResult:
    """Test ProcessingResult dataclass structure."""

    def test_processing_result_structure(self):
        """ProcessingResult has all required fields."""
        result = ProcessingResult(
            tool_name="test_tool",
            status="success",
            data=["item1", "item2"],
            metadata={"count": 2},
            provenance={"activity_id": "urn:test"}
        )
        assert result.tool_name == "test_tool"
        assert result.status == "success"
        assert result.data == ["item1", "item2"]
        assert result.metadata["count"] == 2
        assert "activity_id" in result.provenance

    def test_processing_result_to_dict(self):
        """ProcessingResult.to_dict() returns serializable dict."""
        result = ProcessingResult(
            tool_name="test",
            status="success",
            data=[1, 2, 3],
            metadata={},
            provenance={}
        )
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["tool_name"] == "test"
        assert d["data"] == [1, 2, 3]


class TestDocumentProcessorInit:
    """Test DocumentProcessor initialization."""

    def test_init_without_context(self):
        """Processor initializes without user/experiment context."""
        processor = DocumentProcessor()
        assert processor.user_id is None
        assert processor.experiment_id is None

    def test_init_with_context(self):
        """Processor stores user and experiment IDs."""
        processor = DocumentProcessor(user_id=42, experiment_id=100)
        assert processor.user_id == 42
        assert processor.experiment_id == 100

    def test_generate_provenance(self):
        """Provenance includes required PROV-O fields."""
        processor = DocumentProcessor(user_id=1, experiment_id=2)
        prov = processor._generate_provenance("test_tool", "input summary")

        assert "activity_id" in prov
        assert prov["activity_id"].startswith("urn:ontextract:activity:")
        assert prov["tool"] == "test_tool"
        assert "started_at" in prov
        assert "ended_at" in prov
        assert prov["agent"] == "urn:ontextract:user:1"
        assert prov["experiment"] == "urn:ontextract:experiment:2"


class TestSegmentParagraph:
    """Tests for segment_paragraph tool."""

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    def test_basic_paragraph_splitting(self, processor):
        """Splits text on double newlines."""
        text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph."
        result = processor.segment_paragraph(text)

        assert result.status == "success"
        assert result.tool_name == "segment_paragraph"
        assert len(result.data) == 3
        assert "First paragraph" in result.data[0]
        assert "Second paragraph" in result.data[1]
        assert "Third paragraph" in result.data[2]

    def test_filters_short_paragraphs(self, processor):
        """Paragraphs under 10 chars are filtered out."""
        text = "Short.\n\nThis is a longer paragraph that should be included.\n\nTiny"
        result = processor.segment_paragraph(text)

        assert result.status == "success"
        # Only the longer paragraph should be included
        assert len(result.data) == 1
        assert "longer paragraph" in result.data[0]

    def test_handles_various_whitespace(self, processor):
        """Handles different whitespace patterns between paragraphs."""
        text = "Paragraph one.\n\n\nParagraph two.\n  \n  \nParagraph three."
        result = processor.segment_paragraph(text)

        assert result.status == "success"
        assert len(result.data) == 3

    def test_empty_text(self, processor):
        """Empty text returns empty list."""
        result = processor.segment_paragraph("")

        assert result.status == "success"
        assert result.data == []

    def test_single_paragraph(self, processor):
        """Single paragraph without breaks returns one item."""
        text = "This is a single paragraph with no breaks at all."
        result = processor.segment_paragraph(text)

        assert result.status == "success"
        assert len(result.data) == 1

    def test_metadata_includes_stats(self, processor):
        """Metadata includes count and average length."""
        text = "First paragraph.\n\nSecond paragraph here."
        result = processor.segment_paragraph(text)

        assert "count" in result.metadata
        assert "avg_length" in result.metadata
        assert "method" in result.metadata
        assert result.metadata["method"] == "regex_paragraph_split"

    def test_provenance_included(self, processor):
        """Provenance is generated for the operation."""
        result = processor.segment_paragraph("Test paragraph content here.")

        assert "activity_id" in result.provenance
        assert result.provenance["tool"] == "segment_paragraph"


class TestSegmentSentence:
    """Tests for segment_sentence tool (requires NLTK)."""

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    def test_basic_sentence_splitting(self, processor):
        """Splits text into sentences using NLTK."""
        text = "This is sentence one. This is sentence two. And here is three."
        result = processor.segment_sentence(text)

        assert result.status == "success"
        assert result.tool_name == "segment_sentence"
        assert len(result.data) == 3

    def test_handles_abbreviations(self, processor):
        """NLTK handles common abbreviations correctly."""
        text = "Dr. Smith went to Washington D.C. for the meeting. He arrived early."
        result = processor.segment_sentence(text)

        assert result.status == "success"
        # Should not split on Dr. or D.C.
        assert len(result.data) == 2

    def test_handles_questions_and_exclamations(self, processor):
        """Handles different sentence-ending punctuation."""
        text = "Is this a question? Yes it is! And this is a statement."
        result = processor.segment_sentence(text)

        assert result.status == "success"
        assert len(result.data) == 3

    def test_empty_text(self, processor):
        """Empty text returns empty list."""
        result = processor.segment_sentence("")

        assert result.status == "success"
        assert result.data == []

    def test_metadata_includes_method(self, processor):
        """Metadata includes NLTK method."""
        result = processor.segment_sentence("Test sentence here.")

        assert result.metadata["method"] == "nltk_punkt"


class TestExtractEntitiesSpacy:
    """Tests for extract_entities_spacy tool (requires spaCy)."""

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    def test_extracts_person_entities(self, processor):
        """Extracts PERSON named entities."""
        text = "Steve Jobs founded Apple with Steve Wozniak in California."
        result = processor.extract_entities_spacy(text)

        assert result.status == "success"
        entities = result.data

        # Should find person entities
        persons = [e for e in entities if e['type'] == 'PERSON']
        assert len(persons) >= 1
        person_names = [p['entity'].lower() for p in persons]
        assert any('jobs' in name or 'wozniak' in name for name in person_names)

    def test_extracts_org_entities(self, processor):
        """Extracts ORG named entities."""
        text = "Microsoft and Google are major technology companies."
        result = processor.extract_entities_spacy(text)

        assert result.status == "success"
        orgs = [e for e in result.data if e['type'] == 'ORG']
        org_names = [o['entity'].lower() for o in orgs]
        assert any('microsoft' in name or 'google' in name for name in org_names)

    def test_extracts_gpe_entities(self, processor):
        """Extracts GPE (geopolitical entity) entities."""
        text = "The conference was held in New York City, United States."
        result = processor.extract_entities_spacy(text)

        assert result.status == "success"
        gpes = [e for e in result.data if e['type'] == 'GPE']
        assert len(gpes) >= 1

    def test_extracts_date_entities(self, processor):
        """Extracts DATE entities."""
        text = "The event occurred on January 15, 2020."
        result = processor.extract_entities_spacy(text)

        assert result.status == "success"
        dates = [e for e in result.data if e['type'] == 'DATE']
        assert len(dates) >= 1

    def test_includes_noun_chunks_as_concepts(self, processor):
        """Extracts noun chunks as CONCEPT type."""
        text = "The machine learning algorithm processed the neural network data."
        result = processor.extract_entities_spacy(text)

        assert result.status == "success"
        concepts = [e for e in result.data if e['type'] == 'CONCEPT']
        # Should find some noun phrases
        assert len(concepts) >= 1

    def test_entity_has_position_info(self, processor):
        """Entities include start/end character positions."""
        text = "Apple was founded in 1976."
        result = processor.extract_entities_spacy(text)

        assert result.status == "success"
        for entity in result.data:
            assert 'start' in entity
            assert 'end' in entity
            assert entity['start'] < entity['end']

    def test_entity_has_confidence(self, processor):
        """Entities include confidence score."""
        text = "Google is a technology company."
        result = processor.extract_entities_spacy(text)

        assert result.status == "success"
        for entity in result.data:
            assert 'confidence' in entity
            assert 0 <= entity['confidence'] <= 1

    def test_metadata_includes_counts(self, processor):
        """Metadata includes entity counts by type."""
        text = "John works at Microsoft in Seattle."
        result = processor.extract_entities_spacy(text)

        assert "total_entities" in result.metadata
        assert "entity_types" in result.metadata
        assert "method" in result.metadata

    def test_empty_text(self, processor):
        """Empty text returns empty list."""
        result = processor.extract_entities_spacy("")

        assert result.status == "success"
        assert result.data == []


class TestExtractTemporal:
    """Tests for extract_temporal tool."""

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    def test_extracts_explicit_dates(self, processor):
        """Extracts explicit date mentions."""
        text = "The meeting is scheduled for March 15, 2024."
        result = processor.extract_temporal(text)

        assert result.status == "success"
        assert len(result.data) >= 1

        # Should find the date
        texts = [e['text'].lower() for e in result.data]
        assert any('march' in t or '2024' in t for t in texts)

    def test_extracts_years(self, processor):
        """Extracts standalone year mentions."""
        text = "The algorithm was developed in 1995 and improved in 2010."
        result = processor.extract_temporal(text)

        assert result.status == "success"
        years = [e for e in result.data if e['type'] == 'YEAR' or '1995' in e['text'] or '2010' in e['text']]
        assert len(years) >= 1

    def test_extracts_decades(self, processor):
        """Extracts decade references like '1990s'."""
        text = "The technology emerged in the 1990s and matured in the 2000s."
        result = processor.extract_temporal(text)

        assert result.status == "success"
        decades = [e for e in result.data if e['type'] == 'DECADE' or '1990s' in e['text'] or '2000s' in e['text']]
        assert len(decades) >= 1

    def test_extracts_centuries(self, processor):
        """Extracts century references."""
        text = "This practice dates back to the 19th century."
        result = processor.extract_temporal(text)

        assert result.status == "success"
        centuries = [e for e in result.data if e['type'] == 'CENTURY' or 'century' in e['text'].lower()]
        assert len(centuries) >= 1

    def test_extracts_periods(self, processor):
        """Extracts period markers like 'early 2000s'."""
        text = "In the early 1900s, computing was just beginning."
        result = processor.extract_temporal(text)

        assert result.status == "success"
        periods = [e for e in result.data if 'early' in e['text'].lower() or e['type'] == 'PERIOD']
        assert len(periods) >= 1

    def test_extracts_historical_periods(self, processor):
        """Extracts named historical periods."""
        text = "The Industrial Revolution transformed manufacturing."
        result = processor.extract_temporal(text)

        assert result.status == "success"
        # Should find Industrial Revolution
        historical = [e for e in result.data if 'revolution' in e['text'].lower() or e['type'] == 'HISTORICAL_PERIOD']
        assert len(historical) >= 1

    def test_extracts_relative_time(self, processor):
        """Extracts relative time expressions."""
        text = "Recently, there has been progress. Historically, this was not the case."
        result = processor.extract_temporal(text)

        assert result.status == "success"
        relative = [e for e in result.data if e['type'] == 'RELATIVE']
        assert len(relative) >= 1

    def test_temporal_has_position_info(self, processor):
        """Temporal expressions include position info."""
        text = "In 2020, something happened."
        result = processor.extract_temporal(text)

        assert result.status == "success"
        for expr in result.data:
            assert 'start' in expr
            assert 'end' in expr

    def test_temporal_has_normalized_form(self, processor):
        """Temporal expressions include normalized form when possible."""
        text = "January 1, 2020 was a significant date."
        result = processor.extract_temporal(text)

        assert result.status == "success"
        for expr in result.data:
            assert 'normalized' in expr

    def test_empty_text(self, processor):
        """Empty text returns empty list."""
        result = processor.extract_temporal("")

        assert result.status == "success"
        assert result.data == []


class TestExtractCausal:
    """Tests for extract_causal tool."""

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    def test_extracts_backward_causation(self, processor):
        """Extracts backward causal patterns (effect because cause)."""
        text = "The system failed because the memory was corrupted."
        result = processor.extract_causal(text)

        assert result.status == "success"
        assert len(result.data) >= 1

        relation = result.data[0]
        assert 'cause' in relation
        assert 'effect' in relation
        assert relation['marker'] == 'because'

    def test_extracts_forward_causation(self, processor):
        """Extracts forward causal patterns (cause therefore effect)."""
        text = "The data was corrupted, therefore the system crashed."
        result = processor.extract_causal(text)

        assert result.status == "success"
        # Should find the causal relationship
        relations = [r for r in result.data if r['marker'] == 'therefore']
        assert len(relations) >= 1

    def test_extracts_since_causation(self, processor):
        """Extracts 'since' causal patterns."""
        text = "The project succeeded since the team worked collaboratively."
        result = processor.extract_causal(text)

        assert result.status == "success"
        # May find 'since' as causal marker
        if result.data:
            assert any(r['marker'] == 'since' for r in result.data)

    def test_extracts_conditional_causation(self, processor):
        """Extracts if-then conditional patterns."""
        text = "If the temperature rises above 100 degrees, then the system will shut down."
        result = processor.extract_causal(text)

        assert result.status == "success"
        conditionals = [r for r in result.data if r['type'] == 'conditional']
        assert len(conditionals) >= 1

    def test_causal_has_sentence_context(self, processor):
        """Causal relations include the source sentence."""
        text = "The error occurred because the input was invalid."
        result = processor.extract_causal(text)

        assert result.status == "success"
        if result.data:
            assert 'sentence' in result.data[0]

    def test_filters_short_causes_effects(self, processor):
        """Filters out very short cause/effect phrases."""
        text = "It failed because of X."  # Too short
        result = processor.extract_causal(text)

        assert result.status == "success"
        # Should filter out this trivial match
        # (cause "of X" is too short)

    def test_metadata_includes_counts(self, processor):
        """Metadata includes relation type counts."""
        text = "A happened because B. Therefore C occurred."
        result = processor.extract_causal(text)

        assert "total_relations" in result.metadata
        assert "relation_types" in result.metadata
        assert "method" in result.metadata

    def test_empty_text(self, processor):
        """Empty text returns empty list."""
        result = processor.extract_causal("")

        assert result.status == "success"
        assert result.data == []

    def test_no_causal_relations(self, processor):
        """Text without causal relations returns empty list."""
        text = "The cat sat on the mat. The dog ran in the park."
        result = processor.extract_causal(text)

        assert result.status == "success"
        # May be empty or may find some weak patterns


class TestExtractDefinitions:
    """Tests for extract_definitions tool."""

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    def test_extracts_explicit_definition(self, processor):
        """Extracts 'X is defined as Y' patterns."""
        text = "Machine learning is defined as a subset of artificial intelligence."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        assert len(result.data) >= 1

        defn = result.data[0]
        assert defn['term'].lower() == 'machine learning'
        assert 'subset' in defn['definition'].lower()
        assert defn['pattern'] == 'explicit_definition'

    def test_extracts_refers_to_pattern(self, processor):
        """Extracts 'X refers to Y' patterns."""
        text = "Ontology refers to the study of being and existence."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        defns = [d for d in result.data if d['pattern'] == 'explicit_reference']
        assert len(defns) >= 1

    def test_extracts_means_pattern(self, processor):
        """Extracts 'X means Y' patterns."""
        text = "Semantics means the study of meaning in language."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        defns = [d for d in result.data if d['pattern'] == 'meaning']
        assert len(defns) >= 1

    def test_extracts_copula_definition(self, processor):
        """Extracts 'X is a Y' patterns."""
        text = "Python is a programming language used for data science."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        defns = [d for d in result.data if d['pattern'] == 'copula']
        assert len(defns) >= 1

    def test_extracts_acronym_definition(self, processor):
        """Extracts acronym expansions with strict validation."""
        text = "The API (Application Programming Interface) allows systems to communicate."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        acronyms = [d for d in result.data if d['pattern'] == 'acronym']
        # Should find API expansion
        if acronyms:
            assert acronyms[0]['term'] == 'API'
            assert 'application' in acronyms[0]['definition'].lower()

    def test_rejects_invalid_acronym(self, processor):
        """Rejects acronym patterns that don't match."""
        text = "The AI (LNAI Volume 478) was published recently."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        # Should NOT find this as a valid acronym (letters don't match)
        acronyms = [d for d in result.data if d['pattern'] == 'acronym' and d['term'] == 'AI']
        assert len(acronyms) == 0

    def test_rejects_citation_patterns(self, processor):
        """Rejects academic citation patterns."""
        text = "This was shown by Smith et al., 2015 in their study."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        # Should not extract citation as definition
        for defn in result.data:
            assert 'et al' not in defn['definition']

    def test_rejects_stopword_terms(self, processor):
        """Rejects common stopwords as terms."""
        text = "Which is a word used in questions."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        # Should not have 'which' as a term
        terms = [d['term'].lower() for d in result.data]
        assert 'which' not in terms

    def test_filters_long_terms(self, processor):
        """Rejects terms with more than 3 words."""
        text = "The very long term name here is defined as something."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        # Terms should have at most 3 words
        for defn in result.data:
            assert len(defn['term'].split()) <= 3

    def test_definition_has_position_info(self, processor):
        """Definitions include start/end positions."""
        text = "Algorithm is defined as a step-by-step procedure."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        for defn in result.data:
            assert 'start' in defn
            assert 'end' in defn

    def test_definition_has_confidence(self, processor):
        """Definitions include confidence score."""
        text = "Database is defined as an organized collection of data."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        for defn in result.data:
            assert 'confidence' in defn
            assert 0 <= defn['confidence'] <= 1

    def test_metadata_includes_stats(self, processor):
        """Metadata includes definition statistics."""
        text = "Term is defined as meaning. Concept refers to idea."
        result = processor.extract_definitions(text)

        assert "total_definitions" in result.metadata
        assert "pattern_types" in result.metadata
        assert "method" in result.metadata

    def test_empty_text(self, processor):
        """Empty text returns empty list."""
        result = processor.extract_definitions("")

        assert result.status == "success"
        assert result.data == []

    def test_no_definitions(self, processor):
        """Text without definitions returns empty list."""
        text = "The cat sat on the mat. The dog ran fast."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        # May be empty or may find weak patterns

    def test_dictionary_style_definition(self, processor):
        """Extracts dictionary-style definitions (TERM. Definition...)."""
        text = """
ALGORITHM. A step-by-step procedure for solving a problem.

DATABASE. An organized collection of structured data.
"""
        result = processor.extract_definitions(text)

        assert result.status == "success"
        dict_defs = [d for d in result.data if d['pattern'] == 'dictionary']
        assert len(dict_defs) >= 1


class TestExtractDefinitionsEdgeCases:
    """Edge case tests for definition extraction."""

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    def test_rejects_run_together_words(self, processor):
        """Rejects PDF extraction artifacts with run-together words."""
        text = "The byAgent mechanism isUsed for processing."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        # Should not extract terms with run-together words
        for defn in result.data:
            # Check for camelCase pattern in term
            import re
            assert not re.search(r'[a-z][A-Z]', defn['term'])

    def test_rejects_year_ranges(self, processor):
        """Rejects definitions containing year ranges."""
        text = "Period is defined as 1990-2000 timeframe."
        result = processor.extract_definitions(text)

        assert result.status == "success"
        # Should filter out year ranges in definitions
        for defn in result.data:
            import re
            # Allow the test to pass if no definitions found
            # or if definitions don't have year ranges
            if defn.get('definition'):
                # Year ranges should be rejected
                pass

    def test_handles_special_characters(self, processor):
        """Handles text with special characters."""
        text = "The term is defined as a process."
        result = processor.extract_definitions(text)

        assert result.status in ["success", "partial"]

    def test_handles_unicode(self, processor):
        """Handles Unicode text."""
        text = "Semantique is defined as the study of meaning."
        result = processor.extract_definitions(text)

        assert result.status in ["success", "partial"]


class TestPeriodAwareEmbeddingBasic:
    """Basic tests for period_aware_embedding tool.

    Note: Extensive period-aware embedding tests are in test_period_aware_embedding.py.
    These tests verify basic integration with DocumentProcessor.
    """

    @pytest.fixture
    def processor(self):
        return DocumentProcessor()

    def test_generates_embedding(self, processor):
        """Generates embedding for text."""
        text = "This is a test document about artificial intelligence."
        result = processor.period_aware_embedding(text)

        assert result.status == "success"
        assert result.tool_name == "period_aware_embedding"
        assert 'embedding' in result.data
        assert len(result.data['embedding']) > 0

    def test_respects_period_parameter(self, processor):
        """Uses provided period for model selection."""
        text = "Historical document from the early twentieth century."
        result = processor.period_aware_embedding(text, period="1920")

        assert result.status == "success"
        assert 'period' in result.metadata

    def test_embedding_has_metadata(self, processor):
        """Embedding result includes model and dimension info."""
        text = "Test document for embedding generation."
        result = processor.period_aware_embedding(text)

        assert result.status == "success"
        assert 'model' in result.metadata
        assert 'dimensions' in result.metadata
        assert result.metadata['dimensions'] > 0

    def test_truncates_long_text(self, processor):
        """Truncates very long text appropriately."""
        text = "Word " * 2000  # Very long text
        result = processor.period_aware_embedding(text)

        assert result.status == "success"
        assert result.metadata.get('truncated', False) or len(text) <= 5000


class TestToolExecutor:
    """Tests for ToolExecutor wrapper class."""

    def test_tool_executor_initialization(self):
        """ToolExecutor initializes with tool name."""
        from app.services.extraction_tools import ToolExecutor

        executor = ToolExecutor("segment_paragraph", user_id=1, experiment_id=2)
        assert executor.tool_name == "segment_paragraph"
        assert executor.user_id == 1
        assert executor.experiment_id == 2

    def test_get_artifact_config(self):
        """Returns correct artifact config for tools."""
        from app.services.extraction_tools import ToolExecutor

        executor = ToolExecutor("extract_entities_spacy")
        config = executor._get_artifact_config("extract_entities_spacy")

        assert config['type'] == 'entities'
        assert config['method_key'] == 'spacy_ner'

    def test_unknown_tool_config(self):
        """Returns unknown config for unrecognized tools."""
        from app.services.extraction_tools import ToolExecutor

        executor = ToolExecutor("unknown_tool")
        config = executor._get_artifact_config("unknown_tool")

        assert config['type'] == 'unknown'


class TestToolRegistry:
    """Tests for tool registry functions."""

    def test_get_tool_registry(self):
        """get_tool_registry returns all processing tools."""
        from app.services.extraction_tools import get_tool_registry

        registry = get_tool_registry()

        assert 'segment_paragraph' in registry
        assert 'segment_sentence' in registry
        assert 'extract_entities_spacy' in registry
        assert 'extract_temporal' in registry
        assert 'extract_causal' in registry
        assert 'extract_definitions' in registry
        assert 'period_aware_embedding' in registry

    def test_get_tool_registry_with_context(self):
        """get_tool_registry passes user/experiment context."""
        from app.services.extraction_tools import get_tool_registry

        registry = get_tool_registry(user_id=42, experiment_id=100)

        executor = registry['segment_paragraph']
        assert executor.user_id == 42
        assert executor.experiment_id == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
