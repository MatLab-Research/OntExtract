"""Paragraph and sentence segmentation tools."""

from .context import ProcessorContext
from .result import ProcessingResult


class SegmentationTools(ProcessorContext):
    def segment_paragraph(self, text: str) -> ProcessingResult:
        """
        Split document text into paragraphs.

        Uses regex pattern for robust paragraph splitting (handles various whitespace patterns).

        Args:
            text: The document text to segment

        Returns:
            ProcessingResult with list of paragraphs (minimum 10 chars each)
        """
        try:
            import re

            # Robust paragraph splitting that handles various whitespace patterns
            paragraphs = re.split(r'\n\s*\n', text.strip())

            # Filter empty paragraphs and very short ones (< 10 chars)
            paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]

            metadata = {
                "count": len(paragraphs),
                "avg_length": sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
                "total_chars": len(text),
                "method": "regex_paragraph_split",
                "min_length": 10
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
