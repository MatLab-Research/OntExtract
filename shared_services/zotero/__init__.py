"""
Zotero integration for metadata extraction and bibliographic data retrieval.
"""

from .zotero_service import ZoteroService
from .metadata_mapper import ZoteroMetadataMapper

__all__ = ['ZoteroService', 'ZoteroMetadataMapper']
