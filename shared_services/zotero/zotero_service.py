"""
Zotero API service for retrieving bibliographic metadata.
"""

import logging
import os
from typing import Dict, List, Optional, Any
from pyzotero import zotero
from difflib import SequenceMatcher
import re

logger = logging.getLogger(__name__)


class ZoteroService:
    """Service for interacting with Zotero API to retrieve metadata."""
    
    def __init__(self, api_key: Optional[str] = None, 
                 user_id: Optional[str] = None,
                 group_id: Optional[str] = None,
                 library_type: str = 'user'):
        """
        Initialize Zotero service.
        
        Args:
            api_key: Zotero API key
            user_id: Zotero user ID
            group_id: Zotero group ID (if using group library)
            library_type: 'user' or 'group'
        """
        self.api_key = api_key or os.getenv('ZOTERO_API_KEY')
        self.user_id = user_id or os.getenv('ZOTERO_USER_ID')
        self.group_id = group_id or os.getenv('ZOTERO_GROUP_ID')
        self.library_type = library_type
        
        if not self.api_key:
            raise ValueError("Zotero API key is required")
        
        # Determine which library to use
        if self.library_type == 'group' and self.group_id:
            self.library_id = self.group_id
        else:
            self.library_id = self.user_id
            self.library_type = 'user'
        
        if not self.library_id:
            raise ValueError(f"Zotero {self.library_type} ID is required")
        
        # Initialize Zotero client
        self.zot = zotero.Zotero(self.library_id, self.library_type, self.api_key)
        logger.info(f"Initialized Zotero service for {self.library_type} library {self.library_id}")
    
    def search_by_title(self, title: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search Zotero library by title.
        
        Args:
            title: Document title to search for
            limit: Maximum number of results
            
        Returns:
            List of matching Zotero items
        """
        try:
            # Clean title for search
            clean_title = self._clean_search_text(title)
            
            # Search using Zotero's quick search
            results = self.zot.items(q=clean_title, limit=limit)
            
            # Filter results by title similarity
            filtered_results = []
            for item in results:
                item_data = item.get('data', {})
                item_title = item_data.get('title', '')
                
                # Calculate similarity score
                similarity = self._calculate_similarity(title, item_title)
                if similarity > 0.5:  # Threshold for relevance
                    item_data['_similarity_score'] = similarity
                    filtered_results.append(item)
            
            # Sort by similarity
            filtered_results.sort(key=lambda x: x['data'].get('_similarity_score', 0), reverse=True)
            
            logger.info(f"Found {len(filtered_results)} items matching title: {title[:50]}...")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error searching Zotero by title: {str(e)}")
            return []
    
    def search_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Search Zotero library by DOI.
        
        Args:
            doi: Document DOI
            
        Returns:
            Matching Zotero item or None
        """
        try:
            # Clean DOI
            clean_doi = self._clean_doi(doi)
            
            # Search for DOI
            results = self.zot.items(q=clean_doi, limit=5)
            
            # Check for exact DOI match
            for item in results:
                item_data = item.get('data', {})
                item_doi = item_data.get('DOI', '')
                
                if self._clean_doi(item_doi) == clean_doi:
                    logger.info(f"Found exact DOI match: {doi}")
                    return item
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching Zotero by DOI: {str(e)}")
            return None
    
    def search_by_multiple_fields(self, title: Optional[str] = None,
                                  authors: Optional[List[str]] = None,
                                  year: Optional[str] = None,
                                  doi: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search using multiple fields for better matching.
        
        Args:
            title: Document title
            authors: List of author names
            year: Publication year
            doi: Document DOI
            
        Returns:
            List of matching items ranked by relevance
        """
        matches = []
        
        # Try DOI first (most reliable)
        if doi:
            doi_match = self.search_by_doi(doi)
            if doi_match:
                doi_match['data']['_match_type'] = 'doi'
                doi_match['data']['_match_score'] = 1.0
                return [doi_match]
        
        # Search by title
        if title:
            title_matches = self.search_by_title(title)
            
            # Score matches based on additional criteria
            for item in title_matches:
                score = item['data'].get('_similarity_score', 0)
                match_fields = ['title']
                
                item_data = item['data']
                
                # Check author match
                if authors and 'creators' in item_data:
                    item_authors = self._extract_author_names(item_data['creators'])
                    author_match = self._calculate_author_match(authors, item_authors)
                    if author_match > 0:
                        score += author_match * 0.3
                        match_fields.append('authors')
                
                # Check year match
                if year and 'date' in item_data:
                    item_year = self._extract_year(item_data['date'])
                    if item_year == year:
                        score += 0.2
                        match_fields.append('year')
                
                item_data['_match_score'] = score
                item_data['_match_fields'] = match_fields
                item_data['_match_type'] = 'combined'
                matches.append(item)
        
        # Sort by match score
        matches.sort(key=lambda x: x['data'].get('_match_score', 0), reverse=True)
        
        # Return top matches
        return matches[:5]
    
    def get_item_by_key(self, item_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific item by its Zotero key.
        
        Args:
            item_key: Zotero item key
            
        Returns:
            Zotero item or None
        """
        try:
            item = self.zot.item(item_key)
            return item
        except Exception as e:
            logger.error(f"Error fetching item {item_key}: {str(e)}")
            return None
    
    def extract_proquest_url(self, item: Dict[str, Any]) -> Optional[str]:
        """
        Extract ProQuest URL from Zotero item.
        
        Args:
            item: Zotero item
            
        Returns:
            ProQuest URL if found
        """
        data = item.get('data', {})
        
        # Check URL field
        url = data.get('url', '')
        if 'proquest.com' in url:
            return url
        
        # Check extra field (often contains additional metadata)
        extra = data.get('extra', '')
        if 'proquest.com' in extra:
            # Extract URL from extra field
            url_match = re.search(r'https?://[^\s]+proquest\.com[^\s]+', extra)
            if url_match:
                return url_match.group(0)
        
        # Check attachments
        if 'links' in item:
            for link in item['links'].get('attachment', []):
                if 'proquest.com' in link.get('href', ''):
                    return link['href']
        
        return None
    
    def get_collections(self) -> List[Dict[str, str]]:
        """
        Get all collections from the library.
        
        Returns:
            List of collections with keys and names
        """
        try:
            collections = self.zot.collections()
            return [{'key': c['key'], 'name': c['data']['name']} for c in collections]
        except Exception as e:
            logger.error(f"Error fetching collections: {str(e)}")
            return []
    
    def get_items_from_collection(self, collection_key: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get items from a specific collection.
        
        Args:
            collection_key: Zotero collection key
            limit: Maximum number of items
            
        Returns:
            List of items in the collection
        """
        try:
            items = self.zot.collection_items(collection_key, limit=limit)
            return items
        except Exception as e:
            logger.error(f"Error fetching collection items: {str(e)}")
            return []
    
    # Helper methods
    
    def _clean_search_text(self, text: str) -> str:
        """Clean text for search queries."""
        # Remove special characters that might interfere with search
        text = re.sub(r'[^\w\s-]', ' ', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text
    
    def _clean_doi(self, doi: str) -> str:
        """Clean and normalize DOI."""
        # Remove URL prefix if present
        doi = re.sub(r'https?://doi\.org/', '', doi)
        doi = re.sub(r'https?://dx\.doi\.org/', '', doi)
        # Remove whitespace
        doi = doi.strip()
        return doi
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        # Normalize texts
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # Use SequenceMatcher for similarity
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _extract_author_names(self, creators: List[Dict[str, Any]]) -> List[str]:
        """Extract author names from Zotero creators field."""
        authors = []
        for creator in creators:
            if creator.get('creatorType') == 'author':
                if 'lastName' in creator and 'firstName' in creator:
                    authors.append(f"{creator['firstName']} {creator['lastName']}")
                elif 'name' in creator:
                    authors.append(creator['name'])
        return authors
    
    def _calculate_author_match(self, authors1: List[str], authors2: List[str]) -> float:
        """Calculate match score between two author lists."""
        if not authors1 or not authors2:
            return 0.0
        
        matches = 0
        for a1 in authors1:
            for a2 in authors2:
                if self._calculate_similarity(a1, a2) > 0.8:
                    matches += 1
                    break
        
        # Return ratio of matched authors
        return matches / max(len(authors1), len(authors2))
    
    def _extract_year(self, date_str: str) -> Optional[str]:
        """Extract year from date string."""
        if not date_str:
            return None
        
        # Look for 4-digit year
        year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
        if year_match:
            return year_match.group(0)
        
        return None
