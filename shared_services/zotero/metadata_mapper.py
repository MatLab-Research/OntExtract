"""
Maps Zotero metadata to OntExtract's source_metadata structure.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class ZoteroMetadataMapper:
    """Maps Zotero bibliographic data to OntExtract metadata format."""
    
    @staticmethod
    def map_to_source_metadata(zotero_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Zotero item to source_metadata format.
        
        Args:
            zotero_item: Raw Zotero item from API
            
        Returns:
            Formatted metadata dictionary
        """
        data = zotero_item.get('data', {})
        
        # Extract basic metadata
        metadata = {
            'authors': ZoteroMetadataMapper._extract_authors(data),
            'title': data.get('title', ''),
            'publication_date': ZoteroMetadataMapper._extract_date(data),
            'journal': ZoteroMetadataMapper._extract_journal(data),
            'doi': data.get('DOI', ''),
            'isbn': data.get('ISBN', ''),
            'url': data.get('url', ''),
            'abstract': data.get('abstractNote', ''),
            'citation': ZoteroMetadataMapper._generate_citation(data),
            'item_type': data.get('itemType', ''),
            'pages': data.get('pages', ''),
            'volume': data.get('volume', ''),
            'issue': data.get('issue', ''),
            'publisher': data.get('publisher', ''),
            'place': data.get('place', ''),
            'language': data.get('language', ''),
            'tags': ZoteroMetadataMapper._extract_tags(data),
            'collections': data.get('collections', []),
            'zotero_key': data.get('key', ''),
            'zotero_version': data.get('version', 0),
            'date_added': data.get('dateAdded', ''),
            'date_modified': data.get('dateModified', '')
        }
        
        # Add ProQuest URL if found
        proquest_url = ZoteroMetadataMapper._extract_proquest_url(zotero_item)
        if proquest_url:
            metadata['proquest_url'] = proquest_url
            metadata['source_database'] = 'ProQuest'
        
        # Add extra metadata field
        if data.get('extra'):
            metadata['extra_metadata'] = data['extra']
            # Try to parse structured data from extra field
            extra_parsed = ZoteroMetadataMapper._parse_extra_field(data['extra'])
            if extra_parsed:
                metadata.update(extra_parsed)
        
        # Add research design metadata if detected
        design = ZoteroMetadataMapper._extract_research_design(data)
        if design:
            metadata['design'] = design
        
        # Clean up empty values
        metadata = {k: v for k, v in metadata.items() if v}
        
        return metadata
    
    @staticmethod
    def map_to_prov_o(zotero_item: Dict[str, Any], document_id: str) -> Dict[str, Any]:
        """
        Map Zotero metadata to PROV-O format for provenance tracking.
        
        Args:
            zotero_item: Zotero item
            document_id: OntExtract document ID
            
        Returns:
            PROV-O formatted metadata
        """
        data = zotero_item.get('data', {})
        
        prov_entity = {
            '@id': f"zotero:item:{data.get('key', '')}",
            '@type': ['prov:Entity', 'ont:BibliographicRecord'],
            'prov:value': data.get('title', ''),
            'prov:generatedAtTime': datetime.now().isoformat(),
            'prov:wasAttributedTo': 'agent:zotero',
            'ont:documentId': document_id,
            'ont:itemType': data.get('itemType', ''),
            'ont:metadata': ZoteroMetadataMapper.map_to_source_metadata(zotero_item)
        }
        
        return prov_entity
    
    @staticmethod
    def determine_reference_subtype(zotero_item: Dict[str, Any]) -> str:
        """
        Determine the reference subtype based on Zotero item type.
        
        Args:
            zotero_item: Zotero item
            
        Returns:
            Reference subtype for OntExtract
        """
        item_type = zotero_item.get('data', {}).get('itemType', '')
        
        type_mapping = {
            'journalArticle': 'academic',
            'book': 'book',
            'bookSection': 'book',
            'conferencePaper': 'conference',
            'thesis': 'academic',
            'report': 'technical',
            'patent': 'patent',
            'webpage': 'website',
            'encyclopediaArticle': 'encyclopedia',
            'dictionaryEntry': 'dictionary_general',
            'standard': 'standard',
            'manuscript': 'academic',
            'preprint': 'academic',
            'presentation': 'conference'
        }
        
        return type_mapping.get(item_type, 'other')
    
    # Helper methods
    
    @staticmethod
    def _extract_authors(data: Dict[str, Any]) -> List[str]:
        """Extract author names from Zotero data."""
        authors = []
        
        for creator in data.get('creators', []):
            if creator.get('creatorType') == 'author':
                if 'lastName' in creator and 'firstName' in creator:
                    name = f"{creator['firstName']} {creator['lastName']}"
                elif 'name' in creator:
                    name = creator['name']
                else:
                    continue
                authors.append(name.strip())
        
        return authors
    
    @staticmethod
    def _extract_date(data: Dict[str, Any]) -> Optional[str]:
        """Extract and format publication date."""
        date_str = data.get('date', '')
        
        if not date_str:
            return None
        
        # Try to parse ISO date
        try:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date_obj.strftime('%Y-%m-%d')
        except:
            pass
        
        # Extract year if present
        year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
        if year_match:
            return year_match.group(0)
        
        return date_str
    
    @staticmethod
    def _extract_journal(data: Dict[str, Any]) -> Optional[str]:
        """Extract journal or publication name."""
        # Try different fields
        journal = data.get('publicationTitle', '')
        if not journal:
            journal = data.get('journalAbbreviation', '')
        if not journal:
            journal = data.get('proceedingsTitle', '')
        if not journal:
            journal = data.get('bookTitle', '')
        
        return journal if journal else None
    
    @staticmethod
    def _extract_tags(data: Dict[str, Any]) -> List[str]:
        """Extract tags from Zotero data."""
        tags = []
        for tag_obj in data.get('tags', []):
            if isinstance(tag_obj, dict) and 'tag' in tag_obj:
                tags.append(tag_obj['tag'])
            elif isinstance(tag_obj, str):
                tags.append(tag_obj)
        return tags
    
    @staticmethod
    def _generate_citation(data: Dict[str, Any]) -> str:
        """Generate a formatted citation string."""
        parts = []
        
        # Authors
        authors = ZoteroMetadataMapper._extract_authors(data)
        if authors:
            if len(authors) > 3:
                parts.append(f"{authors[0]} et al.")
            else:
                parts.append(", ".join(authors))
        
        # Year
        date = ZoteroMetadataMapper._extract_date(data)
        if date:
            year = date[:4] if len(date) >= 4 else date
            parts.append(f"({year})")
        
        # Title
        title = data.get('title', '')
        if title:
            parts.append(f'"{title}"')
        
        # Journal/Publication
        journal = ZoteroMetadataMapper._extract_journal(data)
        if journal:
            parts.append(f"*{journal}*")
        
        # Volume/Issue/Pages
        vol_issue_pages = []
        if data.get('volume'):
            vol_issue_pages.append(f"vol. {data['volume']}")
        if data.get('issue'):
            vol_issue_pages.append(f"no. {data['issue']}")
        if data.get('pages'):
            vol_issue_pages.append(f"pp. {data['pages']}")
        
        if vol_issue_pages:
            parts.append(", ".join(vol_issue_pages))
        
        # DOI
        if data.get('DOI'):
            parts.append(f"DOI: {data['DOI']}")
        
        return ". ".join(parts)
    
    @staticmethod
    def _extract_proquest_url(zotero_item: Dict[str, Any]) -> Optional[str]:
        """Extract ProQuest URL from various fields."""
        data = zotero_item.get('data', {})
        
        # Check main URL field
        url = data.get('url', '')
        if 'proquest.com' in url:
            return url
        
        # Check extra field
        extra = data.get('extra', '')
        if 'proquest.com' in extra:
            url_match = re.search(r'https?://[^\s]+proquest\.com[^\s]+', extra)
            if url_match:
                return url_match.group(0)
        
        # Check attachments
        attachments = data.get('attachments', [])
        for attachment in attachments:
            if 'url' in attachment and 'proquest.com' in attachment['url']:
                return attachment['url']
        
        return None
    
    @staticmethod
    def _parse_extra_field(extra: str) -> Dict[str, Any]:
        """Parse structured data from Zotero extra field."""
        parsed = {}
        
        if not extra:
            return parsed
        
        # Look for key: value pairs
        lines = extra.split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                # Map common fields
                if key in ['proquest_document_id', 'document_id', 'accession_number']:
                    parsed['proquest_id'] = value
                elif key in ['database', 'source']:
                    parsed['source_database'] = value
                elif key in ['document_url', 'stable_url']:
                    if 'proquest.com' in value:
                        parsed['proquest_url'] = value
        
        return parsed
    
    @staticmethod
    def _extract_research_design(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract research design metadata if present."""
        design = {}
        
        # Check abstract for methodology keywords
        abstract = data.get('abstractNote', '')
        if abstract:
            # Detect study type
            if re.search(r'randomized|RCT|experimental', abstract, re.I):
                design['type'] = 'experimental'
            elif re.search(r'quasi-experimental', abstract, re.I):
                design['type'] = 'quasi-experimental'
            elif re.search(r'survey|questionnaire', abstract, re.I):
                design['type'] = 'survey'
            elif re.search(r'case study|ethnograph', abstract, re.I):
                design['type'] = 'observational'
            
            # Extract sample size if mentioned
            sample_match = re.search(r'[nN]\s*=\s*(\d+)', abstract)
            if sample_match:
                design['sample_size'] = int(sample_match.group(1))
        
        # Check tags for methodology
        tags = ZoteroMetadataMapper._extract_tags(data)
        methodology_tags = [tag for tag in tags if any(
            term in tag.lower() for term in 
            ['qualitative', 'quantitative', 'mixed methods', 'experimental', 'survey']
        )]
        if methodology_tags:
            design['methodology_tags'] = methodology_tags
        
        return design if design else None
