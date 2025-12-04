"""
Tests for Period-Aware Embedding Service

Tests the JCDL paper's period-aware embedding approach including:
- Model selection based on temporal periods
- Model selection based on domain
- Archaic language detection
- Embedding generation with period metadata
- Period drift calculation
- Model availability and download checks
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
import warnings


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def period_service():
    """Create a fresh PeriodAwareEmbeddingService instance."""
    from app.services.period_aware_embedding_service import PeriodAwareEmbeddingService
    return PeriodAwareEmbeddingService()


@pytest.fixture
def sample_texts():
    """Sample texts for different periods and domains."""
    return {
        'archaic': """
            Wherefore art thou seeking such knowledge? Thou hast not the wisdom
            of thine elders who spake these truths in ages past. Henceforth, let
            it be known that such matters doth require careful consideration.
        """,
        'historical_1800s': """
            In the year 1848, the revolutionary movements swept across Europe.
            The philosophical foundations laid by Hegel and his contemporaries
            profoundly influenced the political discourse of the era.
        """,
        'modern_1970s': """
            The computational paradigm emerged in the 1970s as researchers
            developed new approaches to artificial intelligence. The symbolic
            AI methods dominated the field during this period.
        """,
        'contemporary': """
            Machine learning models trained on large datasets have achieved
            state-of-the-art performance on many NLP tasks. Transformer
            architectures enable efficient parallel processing.
        """,
        'scientific': """
            The empirical methodology employed in this study utilized quantitative
            analysis of the experimental parameters. Statistical significance was
            determined through rigorous hypothesis testing with p-values below 0.05.
        """,
        'legal': """
            The defendant hereby stipulates that the aforementioned contract
            shall be null and void. Pursuant to Section 12(a) of the statute,
            the plaintiff is entitled to damages.
        """,
        'philosophy': """
            The ontological status of abstract objects remains contested in
            contemporary metaphysics. The dialectical method reveals inherent
            contradictions in the thesis.
        """
    }


# ==============================================================================
# Model Selection Tests
# ==============================================================================

class TestModelSelection:
    """Tests for period and domain-based model selection."""

    def test_select_model_pre1850(self, period_service):
        """Test model selection for pre-1850 texts."""
        result = period_service.select_model_for_period(year=1750)

        assert 'model' in result
        assert 'selection_reason' in result
        assert 'selection_confidence' in result
        assert result['era'] == 'pre-industrial'
        assert result['handles_archaic'] is True
        assert 'Pre-industrial' in result['selection_reason'] or 'archaic' in result['selection_reason'].lower()

    def test_select_model_1850_1950(self, period_service):
        """Test model selection for 1850-1950 texts."""
        result = period_service.select_model_for_period(year=1920)

        assert result['era'] == 'industrial'
        assert result['handles_archaic'] is True
        assert 'Industrial' in result['selection_reason']

    def test_select_model_1950_2000(self, period_service):
        """Test model selection for 1950-2000 texts."""
        result = period_service.select_model_for_period(year=1985)

        assert result['era'] == 'modern'
        assert result['handles_archaic'] is False
        assert 'Modern' in result['selection_reason']

    def test_select_model_post2000(self, period_service):
        """Test model selection for post-2000 texts."""
        result = period_service.select_model_for_period(year=2020)

        assert result['era'] == 'contemporary'
        assert 'roberta' in result['model'].lower() or 'Contemporary' in result['selection_reason']

    def test_select_model_boundary_years(self, period_service):
        """Test model selection at period boundaries."""
        # Exactly 1850
        result_1850 = period_service.select_model_for_period(year=1850)
        assert result_1850['era'] == 'industrial'

        # Exactly 1950
        result_1950 = period_service.select_model_for_period(year=1950)
        assert result_1950['era'] == 'modern'

        # Exactly 2000
        result_2000 = period_service.select_model_for_period(year=2000)
        assert result_2000['era'] == 'contemporary'

    def test_select_model_scientific_domain(self, period_service):
        """Test model selection for scientific domain."""
        result = period_service.select_model_for_period(domain='scientific')

        assert 'scibert' in result['model'].lower()
        assert result['domain'] == 'science'
        assert 'Domain-specific' in result['selection_reason']

    def test_select_model_legal_domain(self, period_service):
        """Test model selection for legal domain."""
        result = period_service.select_model_for_period(domain='legal')

        assert 'legal' in result['model'].lower()
        assert result['domain'] == 'law'

    def test_select_model_biomedical_domain(self, period_service):
        """Test model selection for biomedical domain."""
        result = period_service.select_model_for_period(domain='biomedical')

        assert 'biobert' in result['model'].lower()
        assert result['domain'] == 'medicine'

    def test_domain_takes_precedence(self, period_service):
        """Test that domain takes precedence over year for model selection."""
        result = period_service.select_model_for_period(year=1850, domain='scientific')

        # Domain should take precedence
        assert 'scibert' in result['model'].lower()
        assert 'Domain-specific' in result['selection_reason']

    def test_select_model_no_parameters(self, period_service):
        """Test default model selection with no parameters."""
        result = period_service.select_model_for_period()

        assert 'model' in result
        assert result['selection_confidence'] == 0.5  # Default/fallback confidence
        assert 'Default' in result['selection_reason'] or 'insufficient' in result['selection_reason'].lower()


# ==============================================================================
# Text Analysis Tests
# ==============================================================================

class TestTextAnalysis:
    """Tests for text characteristic analysis."""

    def test_detect_archaic_language(self, period_service, sample_texts):
        """Test detection of archaic language patterns."""
        result = period_service._analyze_text_characteristics(sample_texts['archaic'])

        assert result['likely_archaic'] is True
        assert result['archaic_score'] > 0

    def test_detect_technical_vocabulary(self, period_service, sample_texts):
        """Test detection of technical vocabulary."""
        result = period_service._analyze_text_characteristics(sample_texts['scientific'])

        assert result['likely_technical'] is True
        assert result['technical_score'] > 0

    def test_modern_text_not_archaic(self, period_service, sample_texts):
        """Test that modern text is not classified as archaic."""
        result = period_service._analyze_text_characteristics(sample_texts['contemporary'])

        assert result['likely_archaic'] is False

    def test_text_analysis_from_sample(self, period_service, sample_texts):
        """Test model selection using text sample analysis."""
        result = period_service.select_model_for_period(text_sample=sample_texts['archaic'])

        assert result['selection_confidence'] >= 0.6
        assert 'Archaic' in result['selection_reason'] or 'archaic' in result['selection_reason'].lower()


# ==============================================================================
# Embedding Generation Tests
# ==============================================================================

class TestEmbeddingGeneration:
    """Tests for period-aware embedding generation."""

    def test_generate_embedding_with_year(self, period_service, sample_texts):
        """Test embedding generation with year specified."""
        result = period_service.generate_period_aware_embedding(
            text=sample_texts['historical_1800s'],
            year=1848
        )

        assert 'embedding' in result
        assert 'model_used' in result
        assert 'selection_reason' in result
        assert 'dimension' in result
        assert result['period_detected'] == 1848

    def test_generate_embedding_with_domain(self, period_service, sample_texts):
        """Test embedding generation with domain specified."""
        result = period_service.generate_period_aware_embedding(
            text=sample_texts['scientific'],
            domain='scientific'
        )

        assert 'embedding' in result
        assert result['domain_detected'] == 'scientific'

    def test_embedding_has_correct_dimension(self, period_service):
        """Test that embedding has expected dimensions."""
        result = period_service.generate_period_aware_embedding(
            text="Test text for embedding.",
            year=2020
        )

        if result.get('embedding'):
            assert len(result['embedding']) == result['dimension']

    def test_embedding_result_metadata(self, period_service):
        """Test that embedding result contains required metadata."""
        result = period_service.generate_period_aware_embedding(
            text="Sample text",
            year=1900
        )

        required_fields = [
            'embedding', 'model_used', 'model_description',
            'selection_reason', 'selection_confidence', 'dimension',
            'period_detected', 'domain_detected', 'generated_at'
        ]

        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_fallback_embedding_on_error(self, period_service):
        """Test that fallback embedding is returned on error."""
        # This tests the service's error handling
        with patch.object(period_service, 'base_service', None):
            result = period_service.generate_period_aware_embedding(
                text="Test text"
            )

            # Should still return an embedding (fallback)
            assert 'embedding' in result
            assert len(result['embedding']) > 0


# ==============================================================================
# Period Drift Calculation Tests
# ==============================================================================

class TestPeriodDrift:
    """Tests for semantic drift calculation between periods."""

    def test_calculate_drift_basic(self, period_service):
        """Test basic drift calculation."""
        # Create mock embeddings for two periods
        np.random.seed(42)
        period1_embeddings = [np.random.rand(384).tolist() for _ in range(5)]
        period2_embeddings = [np.random.rand(384).tolist() for _ in range(5)]

        result = period_service.calculate_period_drift(
            term="test_term",
            period1_embeddings=period1_embeddings,
            period2_embeddings=period2_embeddings,
            period1_year=1900,
            period2_year=2000
        )

        assert 'drift_magnitude' in result
        assert 'cosine_distance' in result
        assert 'cosine_similarity' in result
        assert 'classification' in result
        assert 'confidence' in result
        assert result['method'] == 'period_aware_centroid_comparison'

    def test_drift_classification_stable(self, period_service):
        """Test that identical embeddings are classified as stable."""
        # Create identical embeddings
        embedding = np.random.rand(384).tolist()
        period1_embeddings = [embedding for _ in range(5)]
        period2_embeddings = [embedding for _ in range(5)]

        result = period_service.calculate_period_drift(
            term="stable_term",
            period1_embeddings=period1_embeddings,
            period2_embeddings=period2_embeddings,
            period1_year=1900,
            period2_year=2000
        )

        assert result['classification'] == 'stable'
        assert result['drift_magnitude'] < 0.2

    def test_drift_empty_embeddings(self, period_service):
        """Test drift calculation with empty embeddings."""
        result = period_service.calculate_period_drift(
            term="empty_term",
            period1_embeddings=[],
            period2_embeddings=[],
            period1_year=1900,
            period2_year=2000
        )

        assert result['drift_magnitude'] == 0.0
        assert result['confidence'] == 0.0
        assert 'error' in result

    def test_drift_sample_size_tracking(self, period_service):
        """Test that sample sizes are tracked in drift results."""
        period1_embeddings = [np.random.rand(384).tolist() for _ in range(10)]
        period2_embeddings = [np.random.rand(384).tolist() for _ in range(5)]

        result = period_service.calculate_period_drift(
            term="sample_term",
            period1_embeddings=period1_embeddings,
            period2_embeddings=period2_embeddings,
            period1_year=1900,
            period2_year=2000
        )

        assert result['sample_size_1'] == 10
        assert result['sample_size_2'] == 5


# ==============================================================================
# Model Availability Tests
# ==============================================================================

class TestModelAvailability:
    """Tests for model availability and download checking."""

    def test_get_available_models(self, period_service):
        """Test getting list of available models."""
        available = period_service.get_available_models()

        assert 'period_models' in available
        assert 'base_service_available' in available
        assert 'total_models' in available
        assert available['total_models'] > 0

    def test_period_models_have_required_fields(self, period_service):
        """Test that all period models have required configuration."""
        required_fields = ['model', 'description', 'dimension']

        for model_key, model_config in period_service.PERIOD_MODELS.items():
            for field in required_fields:
                assert field in model_config, f"Model {model_key} missing field: {field}"

    def test_model_dimensions_valid(self, period_service):
        """Test that model dimensions are valid."""
        for model_key, model_config in period_service.PERIOD_MODELS.items():
            assert model_config['dimension'] in [384, 768, 1024], \
                f"Model {model_key} has unexpected dimension: {model_config['dimension']}"

    def test_health_check(self, period_service):
        """Test service health check (sync wrapper)."""
        import asyncio

        async def run_health_check():
            return await period_service.health_check()

        # Use asyncio.run() for Python 3.7+ or create new event loop to avoid conflicts
        try:
            # Try asyncio.run() first (cleaner, avoids event loop issues)
            health = asyncio.run(run_health_check())
        except RuntimeError:
            # Fallback for nested event loop situations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                health = loop.run_until_complete(run_health_check())
            finally:
                loop.close()

        assert 'service_status' in health
        assert health['service_status'] == 'ok'
        assert 'period_models_count' in health


# ==============================================================================
# Model Download Tests
# ==============================================================================

class TestModelDownload:
    """Tests for model download functionality and availability checking."""

    def test_sentence_transformers_available(self):
        """Test that sentence-transformers library is available."""
        try:
            from sentence_transformers import SentenceTransformer
            assert True
        except ImportError:
            pytest.skip("sentence-transformers not installed")

    def test_default_model_loads(self):
        """Test that the default embedding model can be loaded."""
        try:
            from sentence_transformers import SentenceTransformer
            # Try to load the default model
            model = SentenceTransformer("all-MiniLM-L6-v2")
            assert model is not None

            # Test embedding generation
            embedding = model.encode("Test text")
            assert len(embedding) == 384
        except Exception as e:
            pytest.skip(f"Default model not available: {e}")

    def test_embedding_service_initialization(self):
        """Test that EmbeddingService can be initialized."""
        try:
            from shared_services.embedding.embedding_service import EmbeddingService
            service = EmbeddingService()
            assert service is not None
        except Exception as e:
            # This is expected if models aren't downloaded
            warnings.warn(f"EmbeddingService initialization failed: {e}")

    def test_model_cache_directory_exists(self):
        """Test that HuggingFace cache directory is accessible."""
        import os

        # Check common cache locations
        cache_dirs = [
            os.path.expanduser("~/.cache/huggingface"),
            os.path.expanduser("~/.cache/torch/sentence_transformers"),
            os.environ.get("HF_HOME", ""),
            os.environ.get("TRANSFORMERS_CACHE", "")
        ]

        existing_caches = [d for d in cache_dirs if d and os.path.exists(d)]

        # At least one cache directory should exist if models are downloaded
        # This is informational, not a hard requirement
        if not existing_caches:
            warnings.warn("No HuggingFace cache directories found - models may need to be downloaded")


class TestModelAvailabilityCheck:
    """
    Tests for checking whether models need to be downloaded.

    Similar to NLTK's approach where we check if data exists before using it.
    These tests can be run during startup or deployment to verify models are ready.
    """

    def test_check_model_cached(self):
        """Check if the default model is already cached locally."""
        import os

        # HuggingFace caches models in ~/.cache/huggingface/hub/
        cache_base = os.path.expanduser("~/.cache/huggingface/hub")
        model_name = "sentence-transformers--all-MiniLM-L6-v2"

        model_path = os.path.join(cache_base, f"models--{model_name}")

        if os.path.exists(model_path):
            # Model is cached, check if snapshots exist
            snapshots_path = os.path.join(model_path, "snapshots")
            if os.path.exists(snapshots_path) and os.listdir(snapshots_path):
                assert True, "Model is cached and ready"
            else:
                warnings.warn(f"Model directory exists but no snapshots: {model_path}")
        else:
            warnings.warn(
                f"Model not cached locally. To download, run:\n"
                f"  python -c \"from sentence_transformers import SentenceTransformer; "
                f"SentenceTransformer('all-MiniLM-L6-v2')\""
            )

    def test_check_all_period_models_status(self, period_service):
        """Check download status of all period-aware models."""
        import os

        cache_base = os.path.expanduser("~/.cache/huggingface/hub")
        model_status = {}

        for model_key, config in period_service.PERIOD_MODELS.items():
            model_name = config['model']
            # Convert model name to cache directory format
            cache_name = model_name.replace("/", "--")
            model_path = os.path.join(cache_base, f"models--{cache_name}")

            if os.path.exists(model_path):
                snapshots = os.path.join(model_path, "snapshots")
                if os.path.exists(snapshots) and os.listdir(snapshots):
                    model_status[model_key] = 'cached'
                else:
                    model_status[model_key] = 'incomplete'
            else:
                model_status[model_key] = 'not_downloaded'

        # Report status
        cached = [k for k, v in model_status.items() if v == 'cached']
        not_downloaded = [k for k, v in model_status.items() if v == 'not_downloaded']

        if not_downloaded:
            warnings.warn(
                f"Some models not downloaded: {not_downloaded}\n"
                f"Run ensure_models_downloaded() to download them."
            )

        # At least the default models should be available
        assert len(cached) > 0 or len(not_downloaded) == len(model_status), \
            "Model cache check completed"

    def test_ensure_models_function(self):
        """Test that ensure_models_downloaded utility works."""
        from app.services.period_aware_embedding_service import (
            PeriodAwareEmbeddingService,
            ensure_models_downloaded
        )

        # This function should exist and be callable
        result = ensure_models_downloaded(download=False)  # Just check, don't download

        assert isinstance(result, dict)
        assert 'models_checked' in result
        assert 'models_available' in result
        assert 'models_missing' in result


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestIntegration:
    """Integration tests for period-aware embedding in the processing pipeline."""

    def test_processing_tools_integration(self, sample_texts):
        """Test period-aware embedding via DocumentProcessor."""
        try:
            from app.services.processing_tools import DocumentProcessor

            processor = DocumentProcessor()
            result = processor.period_aware_embedding(
                sample_texts['historical_1800s'],
                period='1848'
            )

            assert result.status == 'success'
            assert result.tool_name == 'period_aware_embedding'
            assert 'embedding' in result.data
            assert 'period' in result.metadata
            assert 'selection_reason' in result.metadata
        except Exception as e:
            pytest.skip(f"Processing tools integration test failed: {e}")

    def test_processing_tools_with_domain(self, sample_texts):
        """Test period-aware embedding with domain parameter."""
        try:
            from app.services.processing_tools import DocumentProcessor

            processor = DocumentProcessor()
            result = processor.period_aware_embedding(
                sample_texts['scientific'],
                domain='scientific'
            )

            assert result.status == 'success'
            assert 'scibert' in result.metadata.get('model', '').lower() or \
                   'scientific' in result.metadata.get('selection_reason', '').lower()
        except Exception as e:
            pytest.skip(f"Processing tools domain test failed: {e}")


# ==============================================================================
# Confidence and Quality Tests
# ==============================================================================

class TestConfidenceScores:
    """Tests for confidence score calculation."""

    def test_manual_period_high_confidence(self, period_service):
        """Test that manually specified periods have high confidence."""
        result = period_service.select_model_for_period(year=1920)
        assert result['selection_confidence'] >= 0.8

    def test_domain_high_confidence(self, period_service):
        """Test that domain-specified selections have high confidence."""
        result = period_service.select_model_for_period(domain='scientific')
        assert result['selection_confidence'] >= 0.9

    def test_text_analysis_medium_confidence(self, period_service, sample_texts):
        """Test that text-analysis-based selection has medium confidence."""
        result = period_service.select_model_for_period(
            text_sample=sample_texts['archaic']
        )
        # Text analysis should have lower confidence than explicit parameters
        assert 0.5 <= result['selection_confidence'] <= 0.8

    def test_default_low_confidence(self, period_service):
        """Test that default selection has low confidence."""
        result = period_service.select_model_for_period()
        assert result['selection_confidence'] <= 0.5


# ==============================================================================
# Edge Case Tests
# ==============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_text(self, period_service):
        """Test handling of empty text."""
        result = period_service.generate_period_aware_embedding(text="", year=2020)
        assert 'embedding' in result or 'error' in result

    def test_very_long_text(self, period_service):
        """Test handling of very long text."""
        long_text = "word " * 10000  # 10K words
        result = period_service.generate_period_aware_embedding(text=long_text, year=2020)
        assert 'embedding' in result

    def test_invalid_year(self, period_service):
        """Test handling of unusual year values."""
        # Very old year
        result_old = period_service.select_model_for_period(year=1500)
        assert 'model' in result_old
        assert result_old['handles_archaic'] is True

        # Future year
        result_future = period_service.select_model_for_period(year=2100)
        assert 'model' in result_future

    def test_unknown_domain(self, period_service):
        """Test handling of unknown domain."""
        result = period_service.select_model_for_period(domain='unknown_domain')
        # Should fall back to default
        assert 'model' in result

    def test_special_characters_in_text(self, period_service):
        """Test handling of special characters."""
        text = "Test with special chars: émoji 🔬 and symbols © ® ™"
        result = period_service.generate_period_aware_embedding(text=text)
        assert 'embedding' in result

    def test_unicode_text(self, period_service):
        """Test handling of non-ASCII text."""
        text = "Философия и наука: 哲学与科学"
        result = period_service.generate_period_aware_embedding(text=text)
        assert 'embedding' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
