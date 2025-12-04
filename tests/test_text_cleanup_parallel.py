"""
Tests for parallel chunk processing in TextCleanupService.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestTextCleanupParallel:
    """Test parallel vs sequential chunk processing."""

    def test_parallel_processing_preserves_order(self):
        """Verify chunks are reassembled in correct order after parallel processing."""
        from app.services.text_cleanup_service import TextCleanupService

        service = TextCleanupService()

        # Create test chunks
        chunks = [f"Chunk {i} content here." for i in range(5)]

        # Mock _clean_chunk to return predictable results
        def mock_clean_chunk(text):
            return f"CLEANED: {text}", {
                'input_tokens': 10,
                'output_tokens': 12
            }

        with patch.object(service, '_clean_chunk', side_effect=mock_clean_chunk):
            cleaned_text, metadata = service._clean_chunks_parallel(chunks, max_workers=3)

        # Verify order is preserved
        lines = cleaned_text.split('\n\n')
        assert len(lines) == 5
        for i, line in enumerate(lines):
            assert f"Chunk {i}" in line, f"Chunk {i} not in correct position"

        # Verify metadata
        assert metadata['processing_mode'] == 'parallel'
        assert metadata['chunks_processed'] == 5
        assert metadata['input_tokens'] == 50  # 5 chunks * 10 tokens
        assert metadata['output_tokens'] == 60  # 5 chunks * 12 tokens

    def test_sequential_processing_order(self):
        """Verify sequential processing maintains order."""
        from app.services.text_cleanup_service import TextCleanupService

        service = TextCleanupService()

        chunks = [f"Chunk {i} content." for i in range(3)]

        def mock_clean_chunk(text):
            return f"CLEANED: {text}", {'input_tokens': 5, 'output_tokens': 6}

        with patch.object(service, '_clean_chunk', side_effect=mock_clean_chunk):
            cleaned_text, metadata = service._clean_chunks_sequential(chunks)

        lines = cleaned_text.split('\n\n')
        assert len(lines) == 3
        assert metadata['processing_mode'] == 'sequential'

    def test_settings_control_processing_mode(self):
        """Verify settings determine parallel vs sequential mode."""
        from app.services.text_cleanup_service import TextCleanupService

        service = TextCleanupService()

        # Test with parallel enabled
        with patch('app.models.app_settings.AppSetting') as mock_setting:
            mock_setting.get_setting.side_effect = lambda key, default=None: {
                'concurrent_chunk_processing': True,
                'max_concurrent_chunks': 5
            }.get(key, default)

            enabled, max_chunks = service._get_processing_settings()
            assert enabled is True
            assert max_chunks == 5

        # Test with parallel disabled
        with patch('app.models.app_settings.AppSetting') as mock_setting:
            mock_setting.get_setting.side_effect = lambda key, default=None: {
                'concurrent_chunk_processing': False,
                'max_concurrent_chunks': 3
            }.get(key, default)

            enabled, max_chunks = service._get_processing_settings()
            assert enabled is False

    def test_max_concurrent_clamped(self):
        """Verify max_concurrent is clamped to 1-10 range."""
        from app.services.text_cleanup_service import TextCleanupService

        service = TextCleanupService()

        # Test values outside range
        with patch('app.models.app_settings.AppSetting') as mock_setting:
            # Too high
            mock_setting.get_setting.side_effect = lambda key, default=None: {
                'concurrent_chunk_processing': True,
                'max_concurrent_chunks': 100
            }.get(key, default)

            _, max_chunks = service._get_processing_settings()
            assert max_chunks == 10  # Clamped to max

            # Too low
            mock_setting.get_setting.side_effect = lambda key, default=None: {
                'concurrent_chunk_processing': True,
                'max_concurrent_chunks': 0
            }.get(key, default)

            _, max_chunks = service._get_processing_settings()
            assert max_chunks == 1  # Clamped to min

    def test_progress_callback_called(self):
        """Verify progress callback is called for each chunk."""
        from app.services.text_cleanup_service import TextCleanupService

        service = TextCleanupService()

        chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]
        progress_calls = []

        def track_progress(current, total):
            progress_calls.append((current, total))

        def mock_clean_chunk(text):
            return f"CLEANED: {text}", {'input_tokens': 5, 'output_tokens': 6}

        with patch.object(service, '_clean_chunk', side_effect=mock_clean_chunk):
            service._clean_chunks_parallel(chunks, progress_callback=track_progress, max_workers=2)

        # Should have 3 progress calls (one per chunk)
        assert len(progress_calls) == 3
        # All should report total=3
        assert all(total == 3 for _, total in progress_calls)
        # Current values should be 1, 2, 3 (in some order due to parallelism)
        assert sorted(current for current, _ in progress_calls) == [1, 2, 3]
