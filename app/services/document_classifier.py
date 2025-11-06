"""
Document Classification Service for Temporal Experiments

Uses LLM to classify documents by discipline, temporal period, and extract
key definitions for semantic change analysis.

Based on "Managing Semantic Change in Research" framework (Rauch et al., 2024)
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import json
import logging
from anthropic import Anthropic

from app.utils.file_handler import FileHandler

logger = logging.getLogger(__name__)


@dataclass
class DocumentClassification:
    """Results of document classification"""
    discipline: str
    subdiscipline: Optional[str]
    temporal_period: str
    publication_year: Optional[int]
    key_definition: str
    semantic_features: Dict[str, bool]
    semantic_category: Optional[str]
    confidence: float
    extraction_method: str = "llm"


class DocumentClassifier:
    """
    Classifies documents for temporal evolution experiments.

    Extracts:
    - Discipline (philosophy, law, economics, AI, etc.)
    - Temporal period classification
    - Key definition of target term
    - Semantic features for comparison
    - Timeline track assignment
    """

    DISCIPLINES = [
        "philosophy",
        "law",
        "economics",
        "computer_science",
        "artificial_intelligence",
        "linguistics",
        "cognitive_science",
        "sociology",
        "psychology",
        "other"
    ]

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize classifier with optional API key"""
        self.file_handler = FileHandler()
        self.api_key = anthropic_api_key

    def classify_document(self, file_path: str, filename: str,
                         term_text: str,
                         semantic_features: Optional[Dict[str, str]] = None,
                         publication_year: Optional[int] = None,
                         authors: Optional[list] = None) -> DocumentClassification:
        """
        Classify a document for temporal evolution experiment.

        Args:
            file_path: Path to document file
            filename: Original filename
            term_text: The target term being analyzed (e.g., "agent")
            semantic_features: Dict of feature names to descriptions for this term
            publication_year: Year from bibliographic metadata (if available)
            authors: List of author names (if available)

        Returns:
            DocumentClassification with all extracted information
        """
        # Extract text from document
        content = self.file_handler.extract_text_from_file(file_path, filename)

        if not content:
            raise ValueError(f"Could not extract text from document: {filename}")

        # Use LLM to classify
        classification = self._classify_with_llm(
            content,
            term_text,
            filename,
            semantic_features,
            publication_year,
            authors
        )

        return classification

    def _classify_with_llm(self, content: str, term_text: str, filename: str,
                          semantic_features: Optional[Dict[str, str]] = None,
                          publication_year: Optional[int] = None,
                          authors: Optional[list] = None) -> DocumentClassification:
        """
        Use Claude to classify document and extract semantic information.
        """
        client = Anthropic()

        # Prepare context information
        context_info = []
        if publication_year:
            context_info.append(f"Publication year: {publication_year}")
        if authors:
            context_info.append(f"Authors: {', '.join(authors)}")
        if filename:
            context_info.append(f"Filename: {filename}")

        context_str = "\n".join(context_info) if context_info else "No metadata available"

        # Build semantic features section dynamically
        if semantic_features:
            features_json = ",\n    ".join([
                f'"{key}": <boolean - {desc}>'
                for key, desc in semantic_features.items()
            ])
        else:
            # Default features if none provided
            features_json = """
    "intentionality": <boolean - does definition involve intention/purpose>,
    "autonomy": <boolean - does definition involve autonomous action>,
    "legal_authority": <boolean - does definition involve legal representation>,
    "moral_responsibility": <boolean - does definition involve moral agency>,
    "computational": <boolean - does definition involve algorithms/software>,
    "causation": <boolean - does definition emphasize causal efficacy>,
    "representation": <boolean - does definition involve acting on behalf of others>"""

        prompt = f"""Analyze this academic document to classify it for semantic change analysis of the term "{term_text}".

Document Metadata:
{context_str}

Document Content (first 10000 characters):
{content[:10000]}

Provide a JSON response with the following structure:
{{
  "discipline": "<primary discipline from: {', '.join(self.DISCIPLINES)}>",
  "subdiscipline": "<more specific field or null>",
  "temporal_period": "<descriptive period label like 'Early 20th Century', 'Contemporary AI Era', 'Classical Period'>",
  "publication_year": <integer year or null>,
  "key_definition": "<How this document defines '{term_text}' - extract the most important definition or characterization, max 500 chars>",
  "semantic_features": {{
    {features_json}
  }},
  "semantic_category": "<primary category: 'philosophical', 'legal', 'computational', 'economic', 'general' or null>",
  "confidence": <float between 0.0 and 1.0 indicating classification confidence>
}}

IMPORTANT INSTRUCTIONS:
1. Choose the MOST SPECIFIC discipline that applies
2. The temporal_period should be descriptive and discipline-aware:
   - For philosophy: "Ancient Greek", "Early Modern", "20th Century Analytic", "Contemporary"
   - For law: "Common Law Era", "Modern Legal Theory", "Contemporary Legal Practice"
   - For AI: "Early AI (1950s-1970s)", "Expert Systems Era", "Machine Learning Era", "Contemporary AI"
3. The key_definition should be the document's PRIMARY characterization of "{term_text}"
   - Quote directly if there's an explicit definition
   - Synthesize from context if implicit
4. Semantic features should reflect THIS DOCUMENT'S understanding, not general knowledge
5. If publication_year is provided in metadata, use it; otherwise infer from content/references
6. Confidence should reflect:
   - 0.9-1.0: Very clear discipline and definition
   - 0.7-0.9: Clear discipline, somewhat ambiguous definition
   - 0.5-0.7: Interdisciplinary or unclear focus
   - <0.5: Very uncertain

Return ONLY the JSON, no other text."""

        # Call Claude API
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        response_text = message.content[0].text.strip()

        # Extract JSON from response (handle markdown code blocks)
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {e}\nResponse: {response_text[:500]}")
            raise ValueError(f"LLM returned invalid JSON: {e}")

        # Build classification object
        classification = DocumentClassification(
            discipline=data.get('discipline', 'other'),
            subdiscipline=data.get('subdiscipline'),
            temporal_period=data.get('temporal_period', 'Unknown Period'),
            publication_year=data.get('publication_year') or publication_year,
            key_definition=data.get('key_definition', ''),
            semantic_features=data.get('semantic_features', {}),
            semantic_category=data.get('semantic_category'),
            confidence=data.get('confidence', 0.5),
            extraction_method='llm'
        )

        return classification

    def determine_timeline_track(self, discipline: str) -> str:
        """
        Determine which timeline track a document should be on.

        Returns track identifier for visualization (e.g., 'philosophy', 'law', 'ai')
        """
        track_mapping = {
            'philosophy': 'philosophy',
            'law': 'law',
            'economics': 'economics',
            'computer_science': 'ai',
            'artificial_intelligence': 'ai',
            'linguistics': 'other',
            'cognitive_science': 'other',
            'sociology': 'other',
            'psychology': 'other',
            'other': 'other'
        }
        return track_mapping.get(discipline, 'other')

    def get_track_color(self, track: str) -> str:
        """
        Get color code for timeline track.

        Based on visualization_config from database migration.
        """
        colors = {
            'oed': '#6c757d',
            'philosophy': '#3498db',
            'law': '#e74c3c',
            'economics': '#2ecc71',
            'ai': '#9b59b6',
            'other': '#95a5a6'
        }
        return colors.get(track, '#95a5a6')


def classify_document_for_experiment(file_path: str, filename: str,
                                    term_text: str,
                                    publication_year: Optional[int] = None,
                                    authors: Optional[list] = None) -> DocumentClassification:
    """
    Convenience function to classify a document.

    Usage:
        classification = classify_document_for_experiment(
            "/path/to/document.pdf",
            "anscombe-intention-1956.pdf",
            "agent",
            publication_year=1956,
            authors=["G.E.M. Anscombe"]
        )
    """
    classifier = DocumentClassifier()
    return classifier.classify_document(
        file_path,
        filename,
        term_text,
        publication_year,
        authors
    )
