"""Period-aware embedding tools."""

from typing import Optional

from .context import ProcessorContext
from .result import ProcessingResult


class EmbeddingTools(ProcessorContext):
    def period_aware_embedding(self, text: str, period: Optional[str] = None,
                                domain: Optional[str] = None) -> ProcessingResult:
        """
        Generate period-aware embeddings for semantic drift analysis.

        Uses the PeriodAwareEmbeddingService to:
        - Automatically detect document period from temporal markers or text analysis
        - Select appropriate embedding model for the period and domain
        - Generate embeddings suitable for diachronic analysis

        From the JCDL paper: "The architecture selects period-appropriate embedding
        models based on the temporal and domain characteristics of the text."

        Requires: sentence-transformers

        Args:
            text: The document text to embed
            period: Optional time period (e.g., "1950s", "1850", "2000-2010")
            domain: Optional domain hint (e.g., "scientific", "legal", "philosophy")

        Returns:
            ProcessingResult with embedding data containing:
            - embedding: the embedding vector (list of floats)
            - period: detected or specified period
            - model: model used for embedding
            - dimensions: embedding dimensionality
            - selection_reason: why this model was chosen
            - selection_confidence: confidence in model selection
        """
        try:
            from app.services.period_aware_embedding_service import get_period_aware_embedding_service
            import re

            # Initialize period-aware embedding service
            try:
                period_service = get_period_aware_embedding_service()
            except Exception as e:
                return ProcessingResult(
                    tool_name="period_aware_embedding",
                    status="error",
                    data=[],
                    metadata={"error": f"Failed to initialize period-aware embedding service: {str(e)}"},
                    provenance=self._generate_provenance("period_aware_embedding")
                )

            # Parse year from period parameter if provided
            doc_year = None
            if period:
                year_match = re.search(r'\b(1[6-9]\d{2}|20[0-2]\d)\b', str(period))
                if year_match:
                    doc_year = int(year_match.group(1))

            # Limit text length for embedding (most models have token limits)
            max_chars = 5000
            text_to_embed = text[:max_chars] if len(text) > max_chars else text

            # Generate period-aware embedding using the service
            try:
                result = period_service.generate_period_aware_embedding(
                    text=text_to_embed,
                    year=doc_year,
                    domain=domain,
                    metadata={"text_length": len(text), "truncated": len(text) > max_chars}
                )

                embedding_vector = result.get('embedding', [])
                model_name = result.get('model_used', 'unknown')
                dimensions = result.get('dimension', len(embedding_vector) if embedding_vector else 0)

                # Calculate some additional metadata
                token_estimate = len(text_to_embed.split())

                metadata = {
                    "period": result.get('period_detected') or period or "unknown",
                    "period_confidence": result.get('selection_confidence', 0.5),
                    "period_detection": "manual" if period else "automatic",
                    "model": model_name,
                    "model_description": result.get('model_description', ''),
                    "selection_reason": result.get('selection_reason', ''),
                    "dimensions": dimensions,
                    "text_length": len(text),
                    "text_embedded": len(text_to_embed),
                    "truncated": len(text) > max_chars,
                    "estimated_tokens": token_estimate,
                    "embedding_type": "period_aware",
                    "domain_detected": result.get('domain_detected'),
                    "generated_at": result.get('generated_at'),
                    # Period-aware metadata for UI display
                    "period_category": result.get('period_category'),
                    "document_year": result.get('document_year') or doc_year,
                    "handles_archaic": result.get('handles_archaic', False),
                    "era": result.get('era'),
                    "model_full": result.get('model_used'),  # Full model path
                    "selection_confidence": result.get('selection_confidence', 0.5)
                }

                # The embedding is returned as both metadata and data
                # Data contains the actual vector for downstream processing
                data = {
                    "embedding": embedding_vector,
                    "period": metadata["period"],
                    "model": model_name,
                    "dimensions": dimensions,
                    "selection_confidence": result.get('selection_confidence', 0.5),
                    "selection_reason": result.get('selection_reason', ''),
                    # Include period-aware fields in data for artifact storage
                    "period_category": result.get('period_category'),
                    "document_year": result.get('document_year') or doc_year,
                    "handles_archaic": result.get('handles_archaic', False),
                    "era": result.get('era'),
                    "model_full": result.get('model_used'),
                    "model_description": result.get('model_description', '')
                }

                return ProcessingResult(
                    tool_name="period_aware_embedding",
                    status="success",
                    data=data,
                    metadata=metadata,
                    provenance=self._generate_provenance(
                        "period_aware_embedding",
                        f"{len(text)} chars, period={metadata['period']}, model={model_name}"
                    )
                )

            except Exception as e:
                return ProcessingResult(
                    tool_name="period_aware_embedding",
                    status="error",
                    data={},
                    metadata={
                        "error": f"Embedding generation failed: {str(e)}",
                        "period": period,
                        "text_length": len(text)
                    },
                    provenance=self._generate_provenance("period_aware_embedding")
                )

        except ImportError as e:
            return ProcessingResult(
                tool_name="period_aware_embedding",
                status="error",
                data={},
                metadata={
                    "error": "Required dependencies not installed. Run: pip install sentence-transformers",
                    "import_error": str(e)
                },
                provenance=self._generate_provenance("period_aware_embedding")
            )
        except Exception as e:
            return ProcessingResult(
                tool_name="period_aware_embedding",
                status="error",
                data={},
                metadata={"error": str(e)},
                provenance=self._generate_provenance("period_aware_embedding")
            )
