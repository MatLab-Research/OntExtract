"""
Core Document Processing Tools

Pure Python implementations that can be used by:
1. Manual UI (direct function calls)
2. MCP Server (exposed via FastMCP)
3. LangChain orchestration (tool binding)

All tools return standardized ProcessingResult objects with PROV-O tracking.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid


@dataclass
class ProcessingResult:
    """
    Standardized output format for all processing tools.

    Includes PROV-O provenance tracking for research reproducibility.
    """
    tool_name: str
    status: str  # success, error, partial
    data: Any
    metadata: Dict[str, Any]
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class DocumentProcessor:
    """
    Core document processing tools.

    Each method is a standalone tool that can be called directly,
    exposed via MCP, or bound to LangChain.
    """

    def __init__(self, user_id: Optional[int] = None, experiment_id: Optional[int] = None):
        """
        Initialize processor with optional context.

        Args:
            user_id: ID of user running the tool (for provenance)
            experiment_id: ID of experiment (for provenance)
        """
        self.user_id = user_id
        self.experiment_id = experiment_id

    def _generate_provenance(self, tool_name: str, input_data: Any = None) -> Dict[str, Any]:
        """
        Generate PROV-O provenance record for tool execution.

        Args:
            tool_name: Name of the tool
            input_data: Optional input data description

        Returns:
            PROV-O compatible provenance dictionary
        """
        execution_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        return {
            "activity_id": f"urn:ontextract:activity:{execution_id}",
            "tool": tool_name,
            "started_at": timestamp,
            "ended_at": timestamp,
            "agent": f"urn:ontextract:user:{self.user_id}" if self.user_id else "urn:ontextract:agent:system",
            "experiment": f"urn:ontextract:experiment:{self.experiment_id}" if self.experiment_id else None,
            "input_summary": str(input_data)[:200] if input_data else None
        }

    # ========================================================================
    # SEGMENTATION TOOLS
    # ========================================================================

    def segment_paragraph(self, text: str) -> ProcessingResult:
        """
        Split document text into paragraphs.

        Uses double newline as paragraph delimiter (standard convention).

        Args:
            text: The document text to segment

        Returns:
            ProcessingResult with list of paragraphs
        """
        try:
            # Split on double newlines, remove empty strings
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

            metadata = {
                "count": len(paragraphs),
                "avg_length": sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
                "method": "double_newline_split"
            }

            return ProcessingResult(
                tool_name="segment_paragraph",
                status="success",
                data=paragraphs,
                metadata=metadata,
                provenance=self._generate_provenance("segment_paragraph", f"{len(text)} chars")
            )

        except Exception as e:
            return ProcessingResult(
                tool_name="segment_paragraph",
                status="error",
                data=[],
                metadata={"error": str(e)},
                provenance=self._generate_provenance("segment_paragraph")
            )

    def segment_sentence(self, text: str) -> ProcessingResult:
        """
        Split text into sentences using NLTK sentence tokenizer.

        Requires: nltk, punkt tokenizer

        Args:
            text: The document text to segment

        Returns:
            ProcessingResult with list of sentences
        """
        try:
            import nltk
            from nltk.tokenize import sent_tokenize

            # Download punkt if not already available
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)

            sentences = sent_tokenize(text)

            metadata = {
                "count": len(sentences),
                "avg_length": sum(len(s) for s in sentences) / len(sentences) if sentences else 0,
                "method": "nltk_punkt"
            }

            return ProcessingResult(
                tool_name="segment_sentence",
                status="success",
                data=sentences,
                metadata=metadata,
                provenance=self._generate_provenance("segment_sentence", f"{len(text)} chars")
            )

        except ImportError:
            return ProcessingResult(
                tool_name="segment_sentence",
                status="error",
                data=[],
                metadata={"error": "NLTK not installed. Run: pip install nltk"},
                provenance=self._generate_provenance("segment_sentence")
            )
        except Exception as e:
            return ProcessingResult(
                tool_name="segment_sentence",
                status="error",
                data=[],
                metadata={"error": str(e)},
                provenance=self._generate_provenance("segment_sentence")
            )

    # ========================================================================
    # EXTRACTION TOOLS (Stubs for now - will implement next)
    # ========================================================================

    def extract_entities_spacy(self, text: str) -> ProcessingResult:
        """
        Extract named entities using spaCy NER.

        TODO: Implement full spaCy integration

        Args:
            text: The document text to analyze

        Returns:
            ProcessingResult with list of entities
        """
        return ProcessingResult(
            tool_name="extract_entities_spacy",
            status="error",
            data=[],
            metadata={"error": "Not yet implemented - coming in Phase 2"},
            provenance=self._generate_provenance("extract_entities_spacy")
        )

    def extract_temporal(self, text: str) -> ProcessingResult:
        """
        Extract temporal expressions and timelines.

        TODO: Implement temporal extraction

        Args:
            text: The document text to analyze

        Returns:
            ProcessingResult with temporal expressions
        """
        return ProcessingResult(
            tool_name="extract_temporal",
            status="error",
            data=[],
            metadata={"error": "Not yet implemented - coming in Phase 2"},
            provenance=self._generate_provenance("extract_temporal")
        )

    def extract_causal(self, text: str) -> ProcessingResult:
        """
        Extract causal relationships between events.

        TODO: Implement causal extraction

        Args:
            text: The document text to analyze

        Returns:
            ProcessingResult with causal relationships
        """
        return ProcessingResult(
            tool_name="extract_causal",
            status="error",
            data=[],
            metadata={"error": "Not yet implemented - coming in Phase 3"},
            provenance=self._generate_provenance("extract_causal")
        )

    def extract_definitions(self, text: str) -> ProcessingResult:
        """
        Extract term definitions and explanations.

        TODO: Implement definition extraction

        Args:
            text: The document text to analyze

        Returns:
            ProcessingResult with definitions
        """
        return ProcessingResult(
            tool_name="extract_definitions",
            status="error",
            data=[],
            metadata={"error": "Not yet implemented - coming in Phase 2"},
            provenance=self._generate_provenance("extract_definitions")
        )

    def period_aware_embedding(self, text: str, period: Optional[str] = None) -> ProcessingResult:
        """
        Generate period-aware embeddings for semantic drift analysis.

        TODO: Implement embedding generation

        Args:
            text: The document text to embed
            period: Optional time period (e.g., "1950s", "contemporary")

        Returns:
            ProcessingResult with embedding vector
        """
        return ProcessingResult(
            tool_name="period_aware_embedding",
            status="error",
            data=[],
            metadata={"error": "Not yet implemented - coming in Phase 4"},
            provenance=self._generate_provenance("period_aware_embedding")
        )


# Convenience function for tool registry compatibility
def get_processor(user_id: Optional[int] = None, experiment_id: Optional[int] = None) -> DocumentProcessor:
    """
    Factory function to create DocumentProcessor instance.

    Args:
        user_id: Optional user ID for provenance
        experiment_id: Optional experiment ID for provenance

    Returns:
        Configured DocumentProcessor instance
    """
    return DocumentProcessor(user_id=user_id, experiment_id=experiment_id)
