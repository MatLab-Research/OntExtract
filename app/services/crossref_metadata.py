"""
CrossRef Metadata Extraction Service

Extracts bibliographic metadata from CrossRef API (used by Zotero).
Provides author, title, publication year, journal, DOI information.
"""

from typing import Optional, Dict, Any
import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CrossRefMetadataExtractor:
    """
    Extract bibliographic metadata from CrossRef API.

    CrossRef is the primary metadata service used by Zotero for academic papers.
    Provides author names, publication dates, titles, journal information, etc.
    """

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, email: Optional[str] = None):
        """
        Initialize CrossRef metadata extractor.

        Args:
            email: Optional polite pool email for better API performance
        """
        self.email = email
        self.session = requests.Session()
        if email:
            self.session.headers.update({'User-Agent': f'OntExtract/1.0 (mailto:{email})'})

    def extract_from_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from a DOI.

        Args:
            doi: Digital Object Identifier (e.g., "10.1145/1234567.1234568")

        Returns:
            Dictionary with metadata fields or None if not found
        """
        try:
            # Clean DOI (remove prefix if present)
            clean_doi = doi.replace('https://doi.org/', '').replace('http://dx.doi.org/', '')

            url = f"{self.BASE_URL}/{clean_doi}"
            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                logger.warning(f"CrossRef API returned status {response.status_code} for DOI: {doi}")
                return None

            data = response.json()
            message = data.get('message', {})

            # Extract metadata
            metadata = {
                'title': self._extract_title(message),
                'authors': self._extract_authors(message),
                'publication_year': self._extract_year(message),
                'journal': self._extract_journal(message),
                'doi': clean_doi,
                'abstract': message.get('abstract'),
                'publisher': message.get('publisher'),
                'type': message.get('type'),  # journal-article, book-chapter, etc.
                'url': message.get('URL'),
                'raw_date': self._extract_raw_date(message)
            }

            return metadata

        except requests.RequestException as e:
            logger.error(f"Error fetching CrossRef metadata for DOI {doi}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing CrossRef response for DOI {doi}: {e}")
            return None

    def extract_from_metadata(self, title: str, authors: Optional[list] = None, limit: int = 5) -> Optional[Dict[str, Any]]:
        """
        Search CrossRef using multiple metadata fields for better matching.

        Args:
            title: Paper title to search for
            authors: Optional list of author names
            limit: Number of results to fetch (default 5)

        Returns:
            Best matching metadata or None if not found
        """
        try:
            params = {
                'query.title': title,
                'rows': limit
            }

            # Add author filter if provided
            if authors and len(authors) > 0:
                # Use first author for filtering (most reliable)
                first_author = authors[0]
                params['query.author'] = first_author
                logger.info(f"Searching CrossRef with title and first author: {first_author}")

            response = self.session.get(self.BASE_URL, params=params, timeout=10)

            if response.status_code != 200:
                logger.warning(f"CrossRef API returned status {response.status_code} for metadata search: {title}")
                return None

            data = response.json()
            items = data.get('message', {}).get('items', [])

            if not items:
                return None

            # Get best match and verify
            best_match = items[0]
            match_score = best_match.get('score', 0)

            # Score thresholds
            HIGH_CONFIDENCE_THRESHOLD = 60.0
            LOW_CONFIDENCE_THRESHOLD = 30.0

            # If we used author matching, be more lenient with scores
            # Author matching significantly reduces false positives
            if authors:
                LOW_CONFIDENCE_THRESHOLD = 20.0
                logger.info(f"Using lower threshold (20.0) for author-enhanced search")

            if match_score < LOW_CONFIDENCE_THRESHOLD:
                logger.warning(
                    f"CrossRef match score too low ({match_score:.2f}) for '{title}'. "
                    f"Returned title: '{self._extract_title(best_match)}'. "
                    f"Rejecting match to avoid false positive."
                )
                return None

            # Determine confidence level
            confidence_level = "high" if match_score >= HIGH_CONFIDENCE_THRESHOLD else "low"
            confidence_value = 0.9 if match_score >= HIGH_CONFIDENCE_THRESHOLD else 0.6

            metadata = {
                'title': self._extract_title(best_match),
                'authors': self._extract_authors(best_match),
                'publication_year': self._extract_year(best_match),
                'journal': self._extract_journal(best_match),
                'doi': best_match.get('DOI'),
                'abstract': best_match.get('abstract'),
                'publisher': best_match.get('publisher'),
                'type': best_match.get('type'),
                'url': best_match.get('URL'),
                'raw_date': self._extract_raw_date(best_match),
                'match_score': match_score,
                'confidence_level': confidence_level,
                'confidence_value': confidence_value,
                'search_used_authors': bool(authors)  # Track if we used author matching
            }

            if confidence_level == "high":
                logger.info(
                    f"Accepted CrossRef match (high confidence, score: {match_score:.2f}) for '{title}': "
                    f"'{metadata['title']}' ({metadata.get('publication_year')})"
                )
            else:
                logger.warning(
                    f"Accepted CrossRef match (LOW CONFIDENCE, score: {match_score:.2f}) for '{title}': "
                    f"'{metadata['title']}' ({metadata.get('publication_year')}). "
                    f"Please verify this is the correct document."
                )

            return metadata

        except requests.RequestException as e:
            logger.error(f"Error searching CrossRef for metadata '{title}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing CrossRef search results for '{title}': {e}")
            return None

    def extract_from_title(self, title: str, authors: Optional[list] = None, limit: int = 5) -> Optional[Dict[str, Any]]:
        """
        Search CrossRef by title and return best match.

        Now delegates to extract_from_metadata() for enhanced searching with authors.

        Args:
            title: Paper title to search for
            authors: Optional list of author names for better matching
            limit: Number of results to fetch (default 5)

        Returns:
            Best matching metadata or None if not found
        """
        return self.extract_from_metadata(title, authors=authors, limit=limit)

    def extract_from_title_old(self, title: str, limit: int = 5) -> Optional[Dict[str, Any]]:
        """Old implementation - kept for reference."""
        try:
            params = {
                'query.title': title,
                'rows': limit
            }

            response = self.session.get(self.BASE_URL, params=params, timeout=10)

            if response.status_code != 200:
                logger.warning(f"CrossRef API returned status {response.status_code} for title search: {title}")
                return None

            data = response.json()
            items = data.get('message', {}).get('items', [])

            if not items:
                return None

            # Get best match (first result) but verify it's actually a good match
            best_match = items[0]
            match_score = best_match.get('score', 0)

            # CrossRef scores typically range from 0-100+
            # Score thresholds:
            # - Above 60: High confidence, auto-accept
            # - 30-60: Possible match, show with low confidence warning
            # - Below 30: Likely false positive, reject
            HIGH_CONFIDENCE_THRESHOLD = 60.0
            LOW_CONFIDENCE_THRESHOLD = 30.0

            if match_score < LOW_CONFIDENCE_THRESHOLD:
                logger.warning(
                    f"CrossRef match score too low ({match_score:.2f}) for title '{title}'. "
                    f"Returned title: '{self._extract_title(best_match)}'. "
                    f"Rejecting match to avoid false positive."
                )
                return None

            # Determine confidence level
            confidence_level = "high" if match_score >= HIGH_CONFIDENCE_THRESHOLD else "low"
            confidence_value = 0.9 if match_score >= HIGH_CONFIDENCE_THRESHOLD else 0.6

            metadata = {
                'title': self._extract_title(best_match),
                'authors': self._extract_authors(best_match),
                'publication_year': self._extract_year(best_match),
                'journal': self._extract_journal(best_match),
                'doi': best_match.get('DOI'),
                'abstract': best_match.get('abstract'),
                'publisher': best_match.get('publisher'),
                'type': best_match.get('type'),
                'url': best_match.get('URL'),
                'raw_date': self._extract_raw_date(best_match),
                'match_score': match_score,  # CrossRef relevance score (0-100+)
                'confidence_level': confidence_level,  # "high" or "low"
                'confidence_value': confidence_value  # 0.9 or 0.6
            }

            if confidence_level == "high":
                logger.info(
                    f"Accepted CrossRef match (high confidence, score: {match_score:.2f}) for '{title}': "
                    f"'{metadata['title']}' ({metadata.get('publication_year')})"
                )
            else:
                logger.warning(
                    f"Accepted CrossRef match (LOW CONFIDENCE, score: {match_score:.2f}) for '{title}': "
                    f"'{metadata['title']}' ({metadata.get('publication_year')}). "
                    f"Please verify this is the correct document."
                )

            return metadata

        except requests.RequestException as e:
            logger.error(f"Error searching CrossRef for title '{title}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing CrossRef search results for title '{title}': {e}")
            return None

    def _extract_title(self, message: Dict) -> Optional[str]:
        """Extract title from CrossRef message"""
        titles = message.get('title', [])
        return titles[0] if titles else None

    def _extract_authors(self, message: Dict) -> list:
        """Extract author names from CrossRef message"""
        authors = []
        for author in message.get('author', []):
            given = author.get('given', '')
            family = author.get('family', '')
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
        return authors

    def _extract_year(self, message: Dict) -> Optional[int]:
        """Extract publication year from CrossRef message"""
        # Try published-print first
        date_parts = message.get('published-print', {}).get('date-parts', [])
        if date_parts and date_parts[0]:
            return date_parts[0][0]

        # Try published-online
        date_parts = message.get('published-online', {}).get('date-parts', [])
        if date_parts and date_parts[0]:
            return date_parts[0][0]

        # Try created date
        date_parts = message.get('created', {}).get('date-parts', [])
        if date_parts and date_parts[0]:
            return date_parts[0][0]

        return None

    def _extract_raw_date(self, message: Dict) -> Optional[str]:
        """Extract full date string from CrossRef message"""
        date_parts = message.get('published-print', {}).get('date-parts', [])
        if not date_parts or not date_parts[0]:
            date_parts = message.get('published-online', {}).get('date-parts', [])

        if date_parts and date_parts[0]:
            parts = date_parts[0]
            if len(parts) >= 3:
                return f"{parts[0]}-{parts[1]:02d}-{parts[2]:02d}"
            elif len(parts) >= 2:
                return f"{parts[0]}-{parts[1]:02d}"
            elif len(parts) >= 1:
                return str(parts[0])

        return None

    def _extract_journal(self, message: Dict) -> Optional[str]:
        """Extract journal name from CrossRef message"""
        containers = message.get('container-title', [])
        return containers[0] if containers else None


def extract_metadata_from_doi(doi: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to extract metadata from DOI.

    Usage:
        metadata = extract_metadata_from_doi("10.1145/1234567.1234568")
    """
    extractor = CrossRefMetadataExtractor()
    return extractor.extract_from_doi(doi)


def extract_metadata_from_title(title: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to extract metadata from title.

    Usage:
        metadata = extract_metadata_from_title("Managing Semantic Change in Research")
    """
    extractor = CrossRefMetadataExtractor()
    return extractor.extract_from_title(title)
