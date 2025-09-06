"""
Enhanced Document Processor - Integrates OED enrichment into document processing pipeline
"""

import logging
import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from app import db
from app.models.document import Document
from app.models.term import Term
from app.services.text_processing import TextProcessingService
from app.services.oed_enrichment_service import OEDEnrichmentService

logger = logging.getLogger(__name__)


class EnhancedDocumentProcessor(TextProcessingService):
    """Enhanced document processor that includes term extraction and OED enrichment"""
    
    def __init__(self):
        super().__init__()
        self.oed_enrichment_service = OEDEnrichmentService()
        
        # Term extraction patterns - can be enhanced with NER or more sophisticated methods
        self.term_patterns = {
            # Technical terms (words ending in common technical suffixes)
            'technical': re.compile(r'\b\w*(?:tion|sion|ment|ness|ity|ism|ist|ance|ence|ing|ed|er|or|al|ic|ive|ous|able|ible)\b', re.IGNORECASE),
            # Proper nouns (capitalized words that aren't sentence starters)
            'proper_nouns': re.compile(r'(?<!^)(?<!\. )\b[A-Z][a-z]+\b'),
            # Domain-specific terms (words with specific prefixes)
            'domain_specific': re.compile(r'\b(?:pre|post|anti|pro|multi|inter|intra|trans|meta|pseudo|quasi|semi)\w+\b', re.IGNORECASE),
            # Important keywords (often repeated, significant for analysis)
            'keywords': None  # Will be populated dynamically based on frequency
        }
    
    def process_document_with_enrichment(self, document: Document, 
                                       extract_terms: bool = True, 
                                       enrich_with_oed: bool = False,
                                       min_term_frequency: int = 2) -> Dict[str, Any]:
        """
        Process document with optional term extraction and OED enrichment
        
        Args:
            document: Document to process
            extract_terms: Whether to extract terms from document
            enrich_with_oed: Whether to enrich extracted terms with OED data
            min_term_frequency: Minimum frequency for term extraction
            
        Returns:
            Processing results with extracted terms and enrichment status
        """
        results = {
            'success': True,
            'document_processed': False,
            'terms_extracted': 0,
            'terms_enriched': 0,
            'errors': [],
            'extracted_terms': [],
            'enrichment_results': []
        }
        
        try:
            # Process document with base text processing
            logger.info(f"Processing document {document.id} with enrichment")
            self.process_document(document)
            results['document_processed'] = True
            
            if extract_terms and document.content:
                # Extract terms from document
                extracted_terms = self._extract_terms_from_content(
                    document.content, 
                    min_frequency=min_term_frequency
                )
                results['terms_extracted'] = len(extracted_terms)
                results['extracted_terms'] = extracted_terms
                
                # Create or update Term records
                created_terms = self._create_term_records(extracted_terms, document)
                
                if enrich_with_oed and created_terms:
                    # Enrich terms with OED data
                    enrichment_results = self._enrich_terms_with_oed(created_terms)
                    results['terms_enriched'] = sum(1 for r in enrichment_results if r.get('success'))
                    results['enrichment_results'] = enrichment_results
            
            logger.info(f"Document processing completed. Terms extracted: {results['terms_extracted']}, Terms enriched: {results['terms_enriched']}")
            
        except Exception as e:
            logger.error(f"Error in enhanced document processing: {str(e)}")
            results['success'] = False
            results['errors'].append(str(e))
        
        return results
    
    def _extract_terms_from_content(self, content: str, min_frequency: int = 2) -> List[Dict[str, Any]]:
        """
        Extract potentially interesting terms from document content
        
        Args:
            content: Document content to analyze
            min_frequency: Minimum frequency for term inclusion
            
        Returns:
            List of extracted terms with metadata
        """
        terms = []
        
        # Clean and normalize text
        text = self._clean_text_for_extraction(content)
        
        # Extract different types of terms
        term_candidates = set()
        
        # Technical terms
        technical_matches = self.term_patterns['technical'].findall(text)
        term_candidates.update([t.lower() for t in technical_matches if len(t) >= 4])
        
        # Proper nouns
        proper_noun_matches = self.term_patterns['proper_nouns'].findall(text)
        term_candidates.update([t.lower() for t in proper_noun_matches if len(t) >= 3])
        
        # Domain-specific terms
        domain_matches = self.term_patterns['domain_specific'].findall(text)
        term_candidates.update([t.lower() for t in domain_matches if len(t) >= 5])
        
        # Calculate term frequencies
        word_freq = {}
        words = text.lower().split()
        for word in words:
            clean_word = re.sub(r'[^a-zA-Z]', '', word)
            if len(clean_word) >= 3:
                word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
        
        # Add high-frequency terms
        for word, freq in word_freq.items():
            if freq >= min_frequency and len(word) >= 4:
                term_candidates.add(word)
        
        # Filter and rank terms
        filtered_terms = self._filter_and_rank_terms(term_candidates, word_freq, content)
        
        # Convert to term objects
        for term_text, metadata in filtered_terms.items():
            terms.append({
                'term_text': term_text,
                'frequency': metadata['frequency'],
                'contexts': metadata['contexts'][:3],  # Top 3 contexts
                'category': metadata['category'],
                'significance_score': metadata['significance']
            })
        
        # Sort by significance score
        terms.sort(key=lambda x: x['significance_score'], reverse=True)
        
        return terms[:50]  # Return top 50 terms
    
    def _clean_text_for_extraction(self, text: str) -> str:
        """Clean text for term extraction"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep word boundaries
        text = re.sub(r'[^\w\s\.\!\?\;\:]', ' ', text)
        return text.strip()
    
    def _filter_and_rank_terms(self, term_candidates: Set[str], word_freq: Dict[str, int], content: str) -> Dict[str, Dict[str, Any]]:
        """Filter and rank term candidates"""
        
        # Common stop words to exclude
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our',
            'out', 'day', 'had', 'has', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who',
            'boy', 'did', 'get', 'guy', 'man', 'put', 'run', 'say', 'she', 'too', 'use', 'way', 'will', 'with',
            'this', 'that', 'they', 'them', 'than', 'then', 'there', 'their', 'these', 'those', 'what', 'when',
            'where', 'which', 'while', 'would', 'could', 'should', 'might', 'about', 'after', 'again', 'also',
            'another', 'before', 'because', 'being', 'between', 'both', 'during', 'each', 'even', 'every',
            'first', 'from', 'further', 'have', 'here', 'however', 'into', 'just', 'last', 'like', 'make',
            'many', 'more', 'most', 'much', 'must', 'need', 'only', 'other', 'over', 'same', 'since', 'some',
            'such', 'take', 'than', 'through', 'time', 'under', 'very', 'want', 'well', 'were', 'work', 'year'
        }
        
        filtered_terms = {}
        
        for term in term_candidates:
            if (len(term) >= 3 and 
                term not in stop_words and 
                not term.isdigit() and 
                term.isalpha()):
                
                frequency = word_freq.get(term, 1)
                contexts = self._get_term_contexts(term, content)
                category = self._categorize_term(term)
                significance = self._calculate_significance(term, frequency, contexts, category)
                
                if significance > 0.1:  # Only include terms above minimum significance
                    filtered_terms[term] = {
                        'frequency': frequency,
                        'contexts': contexts,
                        'category': category,
                        'significance': significance
                    }
        
        return filtered_terms
    
    def _get_term_contexts(self, term: str, content: str, context_window: int = 50) -> List[str]:
        """Get contexts where term appears"""
        contexts = []
        pattern = re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE)
        
        for match in pattern.finditer(content):
            start = max(0, match.start() - context_window)
            end = min(len(content), match.end() + context_window)
            context = content[start:end].strip()
            contexts.append(context)
            
            if len(contexts) >= 5:  # Limit to 5 contexts
                break
        
        return contexts
    
    def _categorize_term(self, term: str) -> str:
        """Categorize term by type"""
        if self.term_patterns['technical'].match(term):
            return 'technical'
        elif term[0].isupper():
            return 'proper_noun'
        elif self.term_patterns['domain_specific'].match(term):
            return 'domain_specific'
        else:
            return 'general'
    
    def _calculate_significance(self, term: str, frequency: int, contexts: List[str], category: str) -> float:
        """Calculate significance score for term"""
        base_score = frequency * 0.1
        
        # Category bonuses
        category_bonus = {
            'technical': 0.3,
            'domain_specific': 0.25,
            'proper_noun': 0.15,
            'general': 0.1
        }.get(category, 0.1)
        
        # Length bonus (longer terms often more significant)
        length_bonus = min(len(term) * 0.02, 0.2)
        
        # Context diversity bonus
        context_bonus = min(len(set(contexts)) * 0.05, 0.25)
        
        return base_score + category_bonus + length_bonus + context_bonus
    
    def _create_term_records(self, extracted_terms: List[Dict[str, Any]], document: Document) -> List[Term]:
        """Create or update Term records from extracted terms"""
        created_terms = []
        
        try:
            for term_data in extracted_terms:
                term_text = term_data['term_text']
                
                # Check if term already exists
                existing_term = Term.query.filter_by(term_text=term_text).first()
                
                if not existing_term:
                    # Create new term
                    term = Term(
                        term_text=term_text,
                        description=f"Extracted from document: {document.filename or document.title}",
                        research_domain='document_analysis',
                        selection_rationale=f"Frequency: {term_data['frequency']}, Category: {term_data['category']}, Significance: {term_data['significance_score']:.3f}",
                        created_by=document.created_by
                    )
                    
                    db.session.add(term)
                    created_terms.append(term)
                else:
                    # Update existing term's selection rationale
                    if existing_term.selection_rationale:
                        existing_term.selection_rationale += f"; Also found in {document.filename or document.title}"
                    created_terms.append(existing_term)
            
            db.session.commit()
            logger.info(f"Created {len(created_terms)} term records")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating term records: {str(e)}")
            raise e
        
        return created_terms
    
    def _enrich_terms_with_oed(self, terms: List[Term]) -> List[Dict[str, Any]]:
        """Enrich terms with OED data"""
        enrichment_results = []
        
        for term in terms:
            try:
                logger.info(f"Enriching term '{term.term_text}' with OED data")
                result = self.oed_enrichment_service.enrich_term_with_oed_data(str(term.id))
                
                enrichment_results.append({
                    'term_id': str(term.id),
                    'term_text': term.term_text,
                    'success': result.get('success', False),
                    'etymology_created': result.get('etymology_created', False),
                    'definitions_created': result.get('definitions_created', 0),
                    'historical_stats_created': result.get('historical_stats_created', 0),
                    'quotation_summaries_created': result.get('quotation_summaries_created', 0),
                    'errors': result.get('errors', [])
                })
                
            except Exception as e:
                logger.error(f"Error enriching term {term.term_text}: {str(e)}")
                enrichment_results.append({
                    'term_id': str(term.id),
                    'term_text': term.term_text,
                    'success': False,
                    'errors': [str(e)]
                })
        
        return enrichment_results
    
    def process_document_batch_with_enrichment(self, document_ids: List[int], 
                                             extract_terms: bool = True,
                                             enrich_with_oed: bool = False) -> Dict[str, Any]:
        """Process multiple documents with optional OED enrichment"""
        batch_results = {
            'success': True,
            'documents_processed': 0,
            'total_terms_extracted': 0,
            'total_terms_enriched': 0,
            'document_results': [],
            'errors': []
        }
        
        for doc_id in document_ids:
            try:
                document = Document.query.get(doc_id)
                if document:
                    result = self.process_document_with_enrichment(
                        document, 
                        extract_terms=extract_terms,
                        enrich_with_oed=enrich_with_oed
                    )
                    
                    batch_results['document_results'].append({
                        'document_id': doc_id,
                        'document_title': document.title,
                        'result': result
                    })
                    
                    if result['success']:
                        batch_results['documents_processed'] += 1
                        batch_results['total_terms_extracted'] += result['terms_extracted']
                        batch_results['total_terms_enriched'] += result['terms_enriched']
                    else:
                        batch_results['errors'].extend(result['errors'])
                
            except Exception as e:
                error_msg = f"Error processing document {doc_id}: {str(e)}"
                logger.error(error_msg)
                batch_results['errors'].append(error_msg)
                batch_results['success'] = False
        
        logger.info(f"Batch processing completed. Documents: {batch_results['documents_processed']}, Terms extracted: {batch_results['total_terms_extracted']}, Terms enriched: {batch_results['total_terms_enriched']}")
        
        return batch_results