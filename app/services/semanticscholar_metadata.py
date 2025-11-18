"""
Semantic Scholar Metadata Extraction Service

Extracts bibliographic metadata from Semantic Scholar API.
Provides comprehensive metadata for arXiv papers, published papers, and preprints.
"""

from typing import Optional, Dict, Any
import logging
from semanticscholar import SemanticScholar

logger = logging.getLogger(__name__)


class SemanticScholarMetadataExtractor:
    """
    Extract bibliographic metadata from Semantic Scholar API.

    Semantic Scholar provides comprehensive academic paper metadata including:
    - arXiv papers
    - Published journal/conference papers
    - Preprints (bioRxiv, medRxiv, etc.)
    - Author information
    - Citations and references
    - Abstracts and full metadata
    """

    def __init__(self):
        """Initialize Semantic Scholar client with timeout."""
        # Set a reasonable timeout (10 seconds)
        self.sch = SemanticScholar(timeout=10)

    def extract_from_arxiv_id(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata using arXiv ID.

        Args:
            arxiv_id: arXiv identifier (e.g., "2511.13699" or "2511.13699v2")

        Returns:
            Dictionary with metadata fields or None if not found
        """
        try:
            # Remove version suffix if present (Semantic Scholar uses base ID)
            base_arxiv_id = arxiv_id.split('v')[0]

            logger.info(f"Semantic Scholar: Querying for arXiv:{base_arxiv_id}")

            # Query Semantic Scholar
            paper = self.sch.get_paper(f'ARXIV:{base_arxiv_id}')

            if not paper:
                logger.warning(f"Semantic Scholar returned no results for arXiv:{arxiv_id}")
                return None

            logger.info(f"Semantic Scholar: Received response for arXiv:{arxiv_id}, parsing metadata")

            # Extract metadata
            metadata = self._parse_paper(paper)
            metadata['extraction_method'] = 'arxiv_id'
            metadata['arxiv_id'] = arxiv_id

            logger.info(f"Semantic Scholar: Found paper for arXiv:{arxiv_id}: '{metadata.get('title', 'Unknown')}'")
            return metadata

        except Exception as e:
            logger.error(f"Error fetching Semantic Scholar metadata for arXiv:{arxiv_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def extract_from_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata using DOI.

        Args:
            doi: Digital Object Identifier (e.g., "10.1145/1234567.1234568")

        Returns:
            Dictionary with metadata fields or None if not found
        """
        try:
            # Clean DOI (remove prefix if present)
            clean_doi = doi.replace('https://doi.org/', '').replace('http://dx.doi.org/', '')

            # Query Semantic Scholar
            paper = self.sch.get_paper(f'DOI:{clean_doi}')

            if not paper:
                logger.warning(f"Semantic Scholar returned no results for DOI:{doi}")
                return None

            # Extract metadata
            metadata = self._parse_paper(paper)
            metadata['extraction_method'] = 'doi'
            metadata['doi'] = clean_doi

            logger.info(f"Semantic Scholar: Found paper for DOI:{doi}: '{metadata.get('title', 'Unknown')}'")
            return metadata

        except Exception as e:
            logger.error(f"Error fetching Semantic Scholar metadata for DOI:{doi}: {e}")
            return None

    def extract_from_title(self, title: str, authors: Optional[list] = None, limit: int = 5) -> Optional[Dict[str, Any]]:
        """
        Search Semantic Scholar by title and return best match.

        Args:
            title: Paper title to search for
            authors: Optional list of author names for better matching
            limit: Number of results to fetch (default 5)

        Returns:
            Best matching metadata or None if not found
        """
        try:
            # Build search query
            query = title
            if authors and len(authors) > 0:
                # Add first author to query for better matching
                query = f"{title} {authors[0]}"
                logger.info(f"Semantic Scholar: Searching with title and first author: {authors[0]}")

            # Search Semantic Scholar
            results = self.sch.search_paper(query, limit=limit)

            if not results or len(results) == 0:
                logger.warning(f"Semantic Scholar: No results for title search: {title}")
                return None

            # Get best match (first result)
            best_match = results[0]

            # Extract metadata
            metadata = self._parse_paper(best_match)
            metadata['extraction_method'] = 'title_search'
            metadata['search_used_authors'] = bool(authors)

            # Semantic Scholar doesn't provide explicit match scores
            # Assume high confidence for first result
            metadata['confidence_level'] = 'high'
            metadata['confidence_value'] = 0.9

            logger.info(
                f"Semantic Scholar: Accepted match for '{title}': "
                f"'{metadata.get('title', 'Unknown')}' ({metadata.get('publication_year', 'N/A')})"
            )
            return metadata

        except Exception as e:
            logger.error(f"Error searching Semantic Scholar for title '{title}': {e}")
            return None

    def _parse_paper(self, paper) -> Dict[str, Any]:
        """
        Parse Semantic Scholar paper object into standard metadata format.

        Args:
            paper: SemanticScholar paper object

        Returns:
            Dictionary with standardized metadata fields
        """
        metadata = {}

        # Basic fields
        metadata['title'] = paper.title if hasattr(paper, 'title') else None
        metadata['abstract'] = paper.abstract if hasattr(paper, 'abstract') else None
        metadata['url'] = paper.url if hasattr(paper, 'url') else None

        # Publication year
        if hasattr(paper, 'year') and paper.year:
            metadata['publication_year'] = paper.year

        # Authors
        if hasattr(paper, 'authors') and paper.authors:
            author_names = [author.name for author in paper.authors if hasattr(author, 'name')]
            if author_names:
                metadata['authors'] = author_names

        # Journal/venue
        if hasattr(paper, 'venue') and paper.venue:
            metadata['journal'] = paper.venue

        # DOI
        if hasattr(paper, 'externalIds') and paper.externalIds:
            if 'DOI' in paper.externalIds:
                metadata['doi'] = paper.externalIds['DOI']
            if 'ArXiv' in paper.externalIds:
                metadata['arxiv_id'] = paper.externalIds['ArXiv']

        # Publication type (mapped from Semantic Scholar fields)
        if hasattr(paper, 'publicationTypes') and paper.publicationTypes:
            metadata['type'] = ', '.join(paper.publicationTypes)

        # Citation count (useful for provenance)
        if hasattr(paper, 'citationCount') and paper.citationCount:
            metadata['citation_count'] = paper.citationCount

        # PDF URL if available
        if hasattr(paper, 'openAccessPdf') and paper.openAccessPdf:
            if hasattr(paper.openAccessPdf, 'url'):
                metadata['pdf_url'] = paper.openAccessPdf.url

        # Semantic Scholar paper ID
        if hasattr(paper, 'paperId'):
            metadata['s2_paper_id'] = paper.paperId

        return metadata


# Convenience functions
def extract_metadata_from_arxiv(arxiv_id: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to extract metadata from arXiv ID.

    Usage:
        metadata = extract_metadata_from_arxiv("2511.13699")
    """
    extractor = SemanticScholarMetadataExtractor()
    return extractor.extract_from_arxiv_id(arxiv_id)


def extract_metadata_from_doi_s2(doi: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to extract metadata from DOI via Semantic Scholar.

    Usage:
        metadata = extract_metadata_from_doi_s2("10.1145/1234567.1234568")
    """
    extractor = SemanticScholarMetadataExtractor()
    return extractor.extract_from_doi(doi)


def extract_metadata_from_title_s2(title: str, authors: Optional[list] = None) -> Optional[Dict[str, Any]]:
    """
    Convenience function to extract metadata from title via Semantic Scholar.

    Usage:
        metadata = extract_metadata_from_title_s2("Managing Semantic Change in Research")
    """
    extractor = SemanticScholarMetadataExtractor()
    return extractor.extract_from_title(title, authors=authors)
