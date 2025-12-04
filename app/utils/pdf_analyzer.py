"""
PDF Analysis Utilities

Extracts metadata from PDF files similar to Zotero's approach:
- DOI extraction from first few pages
- Title extraction from first page
- PDF metadata fields
"""

import re
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFAnalyzer:
    """
    Analyzes PDF files to extract bibliographic metadata.

    Similar to Zotero's approach:
    1. Try to extract DOI from first 3 pages
    2. Extract title from first page
    3. Read embedded PDF metadata
    """

    # DOI regex pattern - matches standard DOI format
    DOI_PATTERN = r'10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+'

    # arXiv ID pattern - matches formats like 2501.04227, 2501.04227v2, 1234.5678v1
    ARXIV_PATTERN = r'\d{4}\.\d{4,5}(?:v\d+)?'

    def __init__(self):
        """Initialize PDF analyzer with optional dependencies."""
        self.has_pypdf2 = False
        self.has_pdfplumber = False

        try:
            # Try modern pypdf first (recommended)
            import pypdf
            self.PyPDF2 = pypdf
            self.has_pypdf2 = True
        except ImportError:
            try:
                # Fallback to legacy PyPDF2 if available
                import PyPDF2
                self.PyPDF2 = PyPDF2
                self.has_pypdf2 = True
            except ImportError:
                logger.warning("pypdf/PyPDF2 not available - PDF analysis will be limited")

        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
            self.has_pdfplumber = True
        except ImportError:
            logger.warning("pdfplumber not available - title extraction will be limited")

    def analyze(self, pdf_path: str, progress_callback=None) -> Dict[str, Any]:
        """
        Analyze PDF and extract all possible metadata.

        Args:
            pdf_path: Path to PDF file
            progress_callback: Optional callback function(message: str) for progress updates

        Returns:
            Dictionary with extracted metadata:
            - doi: Extracted DOI if found
            - arxiv_id: Extracted arXiv ID if found
            - title: Extracted title if found
            - authors: List of author names if found
            - abstract: Extracted abstract if found
            - metadata: PDF embedded metadata
            - extraction_methods: List of methods used
            - progress: List of progress messages
        """
        result = {
            'doi': None,
            'arxiv_id': None,
            'title': None,
            'authors': None,
            'abstract': None,
            'metadata': {},
            'extraction_methods': [],
            'progress': []
        }

        def report_progress(message: str):
            """Report progress both to callback and result list."""
            result['progress'].append(message)
            if progress_callback:
                progress_callback(message)
            logger.info(message)

        report_progress("Scanning PDF for identifiers...")

        # Try arXiv ID extraction (check filename first, then content)
        arxiv_id = self.extract_arxiv_id(pdf_path)
        if arxiv_id:
            result['arxiv_id'] = arxiv_id
            result['extraction_methods'].append('arxiv_id_from_filename_or_text')
            report_progress(f"Found arXiv ID: {arxiv_id}")

        # Try DOI extraction (most reliable for CrossRef lookup)
        doi = self.extract_doi(pdf_path)
        if doi:
            result['doi'] = doi
            result['extraction_methods'].append('doi_from_text')
            report_progress(f"Found DOI: {doi}")

        # Try title extraction
        report_progress("Extracting title from PDF...")
        title = self.extract_title(pdf_path)
        if title:
            result['title'] = title
            result['extraction_methods'].append('title_from_text')
            # Truncate for display
            display_title = title[:60] + '...' if len(title) > 60 else title
            report_progress(f"Found title: {display_title}")

        # Try author extraction
        report_progress("Extracting authors...")
        authors = self.extract_authors(pdf_path)
        if authors:
            result['authors'] = authors
            result['extraction_methods'].append('authors_from_text')
            report_progress(f"Found {len(authors)} author(s)")

        # Try abstract extraction
        abstract = self.extract_abstract(pdf_path)
        if abstract:
            result['abstract'] = abstract
            result['extraction_methods'].append('abstract_from_text')

        # Try embedded metadata
        metadata = self.extract_metadata(pdf_path)
        if metadata:
            result['metadata'] = metadata
            result['extraction_methods'].append('pdf_metadata')

            # Use embedded data if we don't have it yet
            if not result['title'] and metadata.get('title'):
                result['title'] = metadata['title']
                display_title = metadata['title'][:60] + '...' if len(metadata['title']) > 60 else metadata['title']
                report_progress(f"Found title in PDF metadata: {display_title}")

            if not result['authors'] and metadata.get('author'):
                # Parse author string (may be comma-separated)
                author_str = metadata['author']
                if ',' in author_str or ';' in author_str:
                    result['authors'] = [a.strip() for a in re.split('[,;]', author_str)]
                else:
                    result['authors'] = [author_str]
                report_progress(f"Found {len(result['authors'])} author(s) in PDF metadata")

        return result

    def extract_doi(self, pdf_path: str, max_pages: int = 3) -> Optional[str]:
        """
        Extract DOI from first few pages of PDF.

        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to search (default 3)

        Returns:
            DOI string if found, None otherwise
        """
        if not self.has_pypdf2:
            return None

        try:
            with open(pdf_path, 'rb') as f:
                reader = self.PyPDF2.PdfReader(f)
                num_pages = min(max_pages, len(reader.pages))

                for page_num in range(num_pages):
                    try:
                        page = reader.pages[page_num]
                        text = page.extract_text()

                        if text:
                            # Search for DOI pattern
                            match = re.search(self.DOI_PATTERN, text, re.IGNORECASE)
                            if match:
                                doi = match.group(0)
                                # Clean up common formatting issues
                                doi = doi.strip('.,;:')
                                return doi
                    except Exception as e:
                        logger.debug(f"Error extracting text from page {page_num}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error reading PDF for DOI extraction: {e}")

        return None

    def extract_arxiv_id(self, pdf_path: str) -> Optional[str]:
        """
        Extract arXiv ID from filename or PDF content.

        Args:
            pdf_path: Path to PDF file

        Returns:
            arXiv ID if found (e.g., "2501.04227v2")
        """
        # First try filename
        filename = Path(pdf_path).stem
        match = re.search(self.ARXIV_PATTERN, filename)
        if match:
            return match.group(0)

        # Then try first page content
        if not self.has_pypdf2:
            return None

        try:
            with open(pdf_path, 'rb') as f:
                reader = self.PyPDF2.PdfReader(f)
                if len(reader.pages) > 0:
                    first_page = reader.pages[0]
                    text = first_page.extract_text()

                    if text:
                        # Look for arXiv ID in text (often appears as "arXiv:2501.04227")
                        match = re.search(r'arXiv[:\s]*(' + self.ARXIV_PATTERN + ')', text, re.IGNORECASE)
                        if match:
                            return match.group(1)

        except Exception as e:
            logger.debug(f"Error extracting arXiv ID: {e}")

        return None

    def extract_authors(self, pdf_path: str) -> Optional[list]:
        """
        Extract author names from first page of PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of author names if found
        """
        if not self.has_pypdf2:
            return None

        try:
            with open(pdf_path, 'rb') as f:
                reader = self.PyPDF2.PdfReader(f)
                if len(reader.pages) > 0:
                    first_page = reader.pages[0]
                    text = first_page.extract_text()

                    if text:
                        # Look for author patterns after title, before abstract
                        # This is a heuristic - authors are usually listed after title
                        lines = [line.strip() for line in text.split('\n') if line.strip()]

                        # Find "Abstract" or "ABSTRACT" keyword
                        abstract_idx = None
                        for i, line in enumerate(lines):
                            if line.lower() == 'abstract':
                                abstract_idx = i
                                break

                        # Authors are usually in lines 2-10, before abstract
                        if abstract_idx:
                            # Look for lines that look like author names
                            # (capitalized, no numbers, reasonable length)
                            potential_authors = []
                            for line in lines[1:min(abstract_idx, 15)]:
                                # Skip very short or long lines
                                if 5 < len(line) < 100:
                                    # Check if it looks like names (has capital letters, no excessive special chars)
                                    if re.match(r'^[A-Za-z\s,\.]+$', line):
                                        # Split by comma or "and"
                                        names = re.split(r',\s*|\s+and\s+', line)
                                        for name in names:
                                            name = name.strip()
                                            # Filter out institutional affiliations
                                            if name and not any(word in name.lower() for word in ['university', 'institute', 'department', 'college']):
                                                potential_authors.append(name)

                            if potential_authors and len(potential_authors) <= 20:  # Sanity check
                                return potential_authors[:10]  # Limit to first 10

        except Exception as e:
            logger.debug(f"Error extracting authors: {e}")

        return None

    def extract_abstract(self, pdf_path: str, max_length: int = 1000) -> Optional[str]:
        """
        Extract abstract from first page of PDF.

        Args:
            pdf_path: Path to PDF file
            max_length: Maximum abstract length

        Returns:
            Abstract text if found
        """
        if not self.has_pypdf2:
            return None

        try:
            with open(pdf_path, 'rb') as f:
                reader = self.PyPDF2.PdfReader(f)
                if len(reader.pages) > 0:
                    first_page = reader.pages[0]
                    text = first_page.extract_text()

                    if text:
                        # Look for "Abstract" keyword
                        match = re.search(r'abstract\s*[:\-]?\s*(.*?)(?:\n\n|keywords|introduction|1\s+introduction)', text, re.IGNORECASE | re.DOTALL)
                        if match:
                            abstract = match.group(1).strip()
                            # Clean up line breaks and excessive whitespace
                            abstract = ' '.join(abstract.split())
                            # Limit length
                            if len(abstract) > max_length:
                                abstract = abstract[:max_length] + '...'
                            return abstract if abstract else None

        except Exception as e:
            logger.debug(f"Error extracting abstract: {e}")

        return None

    def extract_title(self, pdf_path: str) -> Optional[str]:
        """
        Extract title from first page of PDF.

        The title is typically the largest/most prominent text at the top of the first page.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Title string if found, None otherwise
        """
        # Try pdfplumber first (better for formatted text)
        if self.has_pdfplumber:
            title = self._extract_title_pdfplumber(pdf_path)
            if title:
                return title

        # Fallback to PyPDF2
        if self.has_pypdf2:
            title = self._extract_title_pypdf2(pdf_path)
            if title:
                return title

        return None

    def _extract_title_pypdf2(self, pdf_path: str) -> Optional[str]:
        """Extract title using PyPDF2 - basic text extraction."""
        try:
            with open(pdf_path, 'rb') as f:
                reader = self.PyPDF2.PdfReader(f)
                if len(reader.pages) > 0:
                    first_page = reader.pages[0]
                    text = first_page.extract_text()

                    if text:
                        # Simple heuristic: take first non-empty line that's substantial
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        for line in lines[:10]:  # Check first 10 lines
                            # Skip very short lines (likely headers/page numbers)
                            if len(line) > 15 and not line.isdigit():
                                # Clean up common title issues
                                title = self._clean_title(line)
                                if title:
                                    return title

        except Exception as e:
            logger.debug(f"PyPDF2 title extraction failed: {e}")

        return None

    def _extract_title_pdfplumber(self, pdf_path: str) -> Optional[str]:
        """Extract title using pdfplumber - better text positioning."""
        try:
            with self.pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) > 0:
                    first_page = pdf.pages[0]

                    # Get text with layout information
                    words = first_page.extract_words()

                    if words:
                        # Find largest text in upper portion of page (likely title)
                        # This is a simplified heuristic
                        page_height = first_page.height
                        upper_third = page_height / 3

                        # Get words in upper third, sorted by size
                        upper_words = [w for w in words if w['top'] < upper_third]

                        if upper_words:
                            # Group words by approximate y-position (same line)
                            lines = {}
                            for word in upper_words:
                                y = round(word['top'] / 5) * 5  # Group by 5pt intervals
                                if y not in lines:
                                    lines[y] = []
                                lines[y].append(word)

                            # Find line with largest average font size
                            best_line = None
                            best_size = 0

                            for y, words_list in lines.items():
                                if len(words_list) > 2:  # Need at least 3 words
                                    avg_size = sum(w.get('height', 0) for w in words_list) / len(words_list)
                                    if avg_size > best_size:
                                        best_size = avg_size
                                        best_line = words_list

                            if best_line:
                                # Sort words by x position and join
                                best_line.sort(key=lambda w: w['x0'])
                                title = ' '.join(w['text'] for w in best_line)
                                title = self._clean_title(title)
                                if title:
                                    return title

        except Exception as e:
            logger.debug(f"pdfplumber title extraction failed: {e}")

        return None

    def _clean_title(self, title: str) -> Optional[str]:
        """Clean up extracted title."""
        if not title:
            return None

        # Remove excessive whitespace
        title = ' '.join(title.split())

        # Remove common artifacts
        title = title.strip('*-_=')

        # Skip if too short or looks like metadata
        if len(title) < 10:
            return None

        # Skip if it looks like a header/footer
        if title.lower() in ['abstract', 'introduction', 'keywords', 'references']:
            return None

        return title

    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract embedded PDF metadata fields.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary of metadata fields
        """
        if not self.has_pypdf2:
            return {}

        try:
            with open(pdf_path, 'rb') as f:
                reader = self.PyPDF2.PdfReader(f)

                if reader.metadata:
                    metadata = {}

                    # Common metadata fields
                    if reader.metadata.get('/Title'):
                        metadata['title'] = reader.metadata['/Title']
                    if reader.metadata.get('/Author'):
                        metadata['author'] = reader.metadata['/Author']
                    if reader.metadata.get('/Subject'):
                        metadata['subject'] = reader.metadata['/Subject']
                    if reader.metadata.get('/Creator'):
                        metadata['creator'] = reader.metadata['/Creator']
                    if reader.metadata.get('/Producer'):
                        metadata['producer'] = reader.metadata['/Producer']
                    if reader.metadata.get('/CreationDate'):
                        metadata['creation_date'] = reader.metadata['/CreationDate']

                    return metadata

        except Exception as e:
            logger.debug(f"Error extracting PDF metadata: {e}")

        return {}


# Convenience instance
pdf_analyzer = PDFAnalyzer()
