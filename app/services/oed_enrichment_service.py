"""
OED Enrichment Service - Extracts and processes OED data for semantic evolution visualization
Converts existing OED API responses into structured database records for integration
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re
import json
from flask import current_app
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.term import Term
from app.models.oed_models import (
    OEDEtymology, OEDDefinition, OEDHistoricalStats, OEDQuotationSummary
)
from app.services.oed_service import OEDService


class OEDEnrichmentService:
    """Service for enriching terms with OED etymology, definitions, and statistics"""
    
    def __init__(self):
        self.oed_service = OEDService()
        
    def enrich_term_with_oed_data(self, term_id: str, entry_id: str = None) -> Dict[str, Any]:
        """
        Enrich a term with comprehensive OED data including etymology, definitions, and statistics
        
        Args:
            term_id: UUID of the term to enrich
            entry_id: Optional specific OED entry ID (e.g., 'agent_nn01')
        
        Returns:
            Dict with enrichment results and statistics
        """
        term = Term.query.get(term_id)
        if not term:
            return {"success": False, "error": "Term not found"}
        
        results = {
            "success": True,
            "term_text": term.term_text,
            "etymology_created": False,
            "definitions_created": 0,
            "historical_stats_created": 0,
            "quotation_summaries_created": 0,
            "errors": []
        }
        
        try:
            # If no entry_id provided, try to find suggestions
            if not entry_id:
                suggestions_result = self.oed_service.suggest_ids(term.term_text, limit=1)
                if suggestions_result.get('success') and suggestions_result.get('suggestions'):
                    entry_id = suggestions_result['suggestions'][0]['entry_id']
                else:
                    return {"success": False, "error": "Could not find OED entry for term"}
            
            # Get word data from OED
            word_result = self.oed_service.get_word(entry_id)
            if not word_result.get('success'):
                return {"success": False, "error": f"Failed to get OED word data: {word_result.get('error')}"}
            
            word_data = word_result['data']
            
            # Extract and store etymology
            etymology_result = self._extract_and_store_etymology(term, word_data, entry_id)
            if etymology_result.get('created'):
                results['etymology_created'] = True
            if etymology_result.get('errors'):
                results['errors'].extend(etymology_result['errors'])
            
            # Extract and store definitions with temporal analysis
            definitions_result = self._extract_and_store_definitions(term, word_data, entry_id)
            results['definitions_created'] = definitions_result.get('created', 0)
            if definitions_result.get('errors'):
                results['errors'].extend(definitions_result['errors'])
            
            # Get quotations data
            quotations_result = self.oed_service.get_quotations(entry_id, limit=100)
            if quotations_result.get('success'):
                quotations_data = quotations_result['data']
                
                # Extract and store quotation summaries
                quotation_summaries_result = self._extract_and_store_quotation_summaries(
                    term, quotations_data, entry_id
                )
                results['quotation_summaries_created'] = quotation_summaries_result.get('created', 0)
                if quotation_summaries_result.get('errors'):
                    results['errors'].extend(quotation_summaries_result['errors'])
            
            # Calculate and store historical statistics
            stats_result = self._calculate_and_store_historical_stats(term)
            results['historical_stats_created'] = stats_result.get('created', 0)
            if stats_result.get('errors'):
                results['errors'].extend(stats_result['errors'])
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error enriching term {term.term_text} with OED data: {str(e)}")
            return {"success": False, "error": str(e)}
        
        return results
    
    def _extract_and_store_etymology(self, term: Term, word_data: Dict, entry_id: str) -> Dict[str, Any]:
        """Extract etymology information and store in OEDEtymology table"""
        result = {"created": False, "errors": []}
        
        try:
            # Check if etymology already exists
            existing = OEDEtymology.query.filter_by(term_id=term.id).first()
            if existing:
                return result
            
            # Extract etymology data from word_data
            etymology_text = self._extract_etymology_text(word_data)
            origin_info = self._analyze_origin_language(etymology_text, word_data)
            first_recorded_year = self._extract_first_recorded_year(word_data)
            
            etymology = OEDEtymology(
                term_id=term.id,
                etymology_text=etymology_text,
                origin_language=origin_info.get('language'),
                first_recorded_year=first_recorded_year,
                etymology_confidence=self._assess_etymology_confidence(word_data),
                language_family=origin_info.get('family'),
                root_analysis=self._analyze_word_roots(etymology_text, term.term_text),
                morphology=self._analyze_morphology(term.term_text, word_data),
                source_version="OED_API_2025",
                # PROV-O Entity metadata
                generated_at_time=datetime.utcnow(),
                was_attributed_to="OED_API_Service",
                was_derived_from=entry_id,
                derivation_type="etymology_extraction"
            )
            
            db.session.add(etymology)
            result["created"] = True
            
        except Exception as e:
            result["errors"].append(f"Etymology extraction error: {str(e)}")
        
        return result
    
    def _extract_and_store_definitions(self, term: Term, word_data: Dict, entry_id: str) -> Dict[str, Any]:
        """Extract definitions with temporal context and store in OEDDefinition table"""
        result = {"created": 0, "errors": []}
        
        try:
            # Get extracted senses from OED service
            senses = word_data.get('extracted_senses', [])
            
            for i, sense in enumerate(senses):
                try:
                    # Extract temporal information from definition
                    temporal_info = self._extract_temporal_context_from_definition(sense.get('definition', ''))
                    
                    # Determine historical period
                    historical_period = self._map_to_historical_period(
                        temporal_info.get('first_year'),
                        temporal_info.get('last_year')
                    )
                    
                    # Create excerpt (first 300 chars) and OED URL
                    definition_text = sense.get('definition', '')
                    definition_excerpt = (definition_text[:297] + '...') if len(definition_text) > 300 else definition_text
                    
                    # Generate OED URL for this sense
                    sense_id = sense.get('sense_id') or f"{entry_id}#{i+1}"
                    oed_url = f"https://www.oed.com/dictionary/{term.term_text.lower()}_{entry_id.split('_')[-1]}#{sense_id}"
                    
                    definition = OEDDefinition(
                        term_id=term.id,
                        definition_number=sense.get('label', f"{i+1}"),
                        definition_excerpt=definition_excerpt,
                        oed_sense_id=sense_id,
                        oed_url=oed_url,
                        first_cited_year=temporal_info.get('first_year'),
                        last_cited_year=temporal_info.get('last_year'),
                        part_of_speech=self._extract_part_of_speech(word_data, sense),
                        domain_label=self._extract_domain_label(sense.get('definition', '')),
                        status=self._determine_definition_status(sense.get('definition', '')),
                        quotation_count=temporal_info.get('quotation_count', 0),
                        sense_frequency_rank=i + 1,
                        historical_period=historical_period,
                        period_start_year=temporal_info.get('first_year'),
                        period_end_year=temporal_info.get('last_year'),
                        definition_confidence='medium',
                        # PROV-O Entity metadata
                        generated_at_time=datetime.utcnow(),
                        was_attributed_to="OED_API_Service",
                        was_derived_from=f"{entry_id}#{sense.get('label', f'{i+1}')}",
                        derivation_type="definition_extraction"
                    )
                    
                    db.session.add(definition)
                    result["created"] += 1
                    
                except Exception as e:
                    result["errors"].append(f"Definition {i+1} extraction error: {str(e)}")
                    continue
        
        except Exception as e:
            result["errors"].append(f"Definitions extraction error: {str(e)}")
        
        return result
    
    def _extract_and_store_quotation_summaries(self, term: Term, quotations_data: Dict, entry_id: str) -> Dict[str, Any]:
        """Extract quotation metadata and store in OEDQuotationSummary table"""
        result = {"created": 0, "errors": []}
        
        try:
            quotations = self._parse_quotations_from_data(quotations_data)
            
            for i, quotation in enumerate(quotations):
                try:
                    summary = OEDQuotationSummary(
                        term_id=term.id,
                        quotation_year=quotation.get('year'),
                        author_name=quotation.get('author'),
                        work_title=quotation.get('work_title'),
                        domain_context=self._infer_domain_context(quotation.get('work_title', '')),
                        usage_type=self._classify_usage_type(quotation.get('text', '')),
                        has_technical_usage=self._detect_technical_usage(quotation.get('text', '')),
                        represents_semantic_shift=self._detect_semantic_shift(quotation.get('text', ''), i, quotations),
                        chronological_rank=i + 1,
                        # PROV-O Entity metadata
                        generated_at_time=datetime.utcnow(),
                        was_attributed_to="OED_Quotation_Extractor",
                        was_derived_from=f"{entry_id}_quotation_{i+1}",
                        derivation_type="metadata_extraction"
                    )
                    
                    db.session.add(summary)
                    result["created"] += 1
                    
                except Exception as e:
                    result["errors"].append(f"Quotation {i+1} extraction error: {str(e)}")
                    continue
        
        except Exception as e:
            result["errors"].append(f"Quotations extraction error: {str(e)}")
        
        return result
    
    def _calculate_and_store_historical_stats(self, term: Term) -> Dict[str, Any]:
        """Calculate aggregated historical statistics and store in OEDHistoricalStats table"""
        result = {"created": 0, "errors": []}
        
        try:
            # Group definitions by historical period
            definitions = OEDDefinition.query.filter_by(term_id=term.id).all()
            quotations = OEDQuotationSummary.query.filter_by(term_id=term.id).all()
            
            periods = self._group_by_periods(definitions, quotations)
            
            for period_name, period_data in periods.items():
                try:
                    # Create PROV-O Activity metadata
                    used_definitions = [str(d.id) for d in period_data['definitions']]
                    used_quotations = [str(q.id) for q in period_data['quotations']]
                    
                    stats = OEDHistoricalStats(
                        term_id=term.id,
                        time_period=period_name,
                        start_year=period_data['start_year'],
                        end_year=period_data['end_year'],
                        definition_count=len(period_data['definitions']),
                        sense_count=len(period_data['definitions']),  # Same for now
                        quotation_span_years=period_data['quotation_span'],
                        earliest_quotation_year=period_data['earliest_quotation'],
                        latest_quotation_year=period_data['latest_quotation'],
                        semantic_stability_score=self._calculate_semantic_stability(period_data),
                        domain_shift_indicator=self._detect_domain_shift(period_data),
                        part_of_speech_changes=self._detect_pos_changes(period_data),
                        oed_edition="OED_API_2025",
                        # PROV-O Activity metadata
                        started_at_time=datetime.utcnow(),
                        ended_at_time=datetime.utcnow(),
                        was_associated_with="Statistical_Analysis_Service",
                        used_entity={
                            "definitions": used_definitions,
                            "quotations": used_quotations,
                            "analysis_period": period_name
                        },
                        generated_entity=f"oed_historical_stats_{term.term_text}_{period_name}"
                    )
                    
                    db.session.add(stats)
                    result["created"] += 1
                    
                except IntegrityError:
                    # Stats for this period already exist
                    db.session.rollback()
                    continue
                except Exception as e:
                    result["errors"].append(f"Stats for period {period_name} error: {str(e)}")
                    continue
        
        except Exception as e:
            result["errors"].append(f"Historical stats calculation error: {str(e)}")
        
        return result
    
    # Helper methods for data extraction and analysis
    
    def _extract_etymology_text(self, word_data: Dict) -> Optional[str]:
        """Extract etymology text from OED word data"""
        # Look for etymology in various possible locations
        etymology_fields = ['etymology', 'etymologies', 'origin']
        for field in etymology_fields:
            if field in word_data and word_data[field]:
                if isinstance(word_data[field], list):
                    return word_data[field][0] if word_data[field] else None
                return str(word_data[field])
        return None
    
    def _analyze_origin_language(self, etymology_text: str, word_data: Dict) -> Dict[str, Any]:
        """Analyze origin language and language family"""
        result = {"language": None, "family": None}
        
        if not etymology_text:
            return result
        
        # Common language patterns
        language_patterns = {
            'Latin': ['Latin', 'L.'],
            'Greek': ['Greek', 'Gr.'],
            'French': ['French', 'F.', 'Old French', 'OF.'],
            'Germanic': ['Germanic', 'OHG', 'Old High German'],
            'Anglo-Saxon': ['Anglo-Saxon', 'AS.', 'Old English', 'OE.']
        }
        
        etymology_lower = etymology_text.lower()
        for language, patterns in language_patterns.items():
            if any(pattern.lower() in etymology_lower for pattern in patterns):
                result["language"] = language
                # Add family information
                if language in ['Latin', 'Greek']:
                    result["family"] = {"family": "Indo-European", "branch": "Classical"}
                elif language in ['French']:
                    result["family"] = {"family": "Indo-European", "branch": "Romance"}
                elif language in ['Germanic', 'Anglo-Saxon']:
                    result["family"] = {"family": "Indo-European", "branch": "Germanic"}
                break
        
        return result
    
    def _extract_first_recorded_year(self, word_data: Dict) -> Optional[int]:
        """Extract first recorded year from word data"""
        # Look for date information in word data
        date_fields = ['first_use_date', 'earliest_date', 'date_of_first_use']
        for field in date_fields:
            if field in word_data and word_data[field]:
                try:
                    return int(word_data[field])
                except (ValueError, TypeError):
                    continue
        return None
    
    def _extract_temporal_context_from_definition(self, definition_text: str) -> Dict[str, Any]:
        """Extract temporal context from definition text"""
        result = {"first_year": None, "last_year": None, "quotation_count": 0}
        
        # Look for year patterns in definition
        year_pattern = r'\b(1[0-9]{3}|20[0-2][0-9])\b'
        years = re.findall(year_pattern, definition_text)
        
        if years:
            years = [int(y) for y in years]
            result["first_year"] = min(years)
            result["last_year"] = max(years)
        
        return result
    
    def _map_to_historical_period(self, first_year: Optional[int], last_year: Optional[int]) -> str:
        """Map years to historical periods matching existing system"""
        if not first_year:
            return "contemporary"
        
        if first_year < 1850:
            return "historical_pre1950"
        elif first_year < 2000:
            return "modern_2000plus"
        else:
            return "contemporary"
    
    def _extract_part_of_speech(self, word_data: Dict, sense: Dict) -> Optional[str]:
        """Extract part of speech from word data or sense"""
        pos_fields = ['pos', 'part_of_speech', 'grammatical_category']
        for field in pos_fields:
            if field in word_data and word_data[field]:
                return str(word_data[field])
            if field in sense and sense[field]:
                return str(sense[field])
        return None
    
    def _extract_domain_label(self, definition_text: str) -> Optional[str]:
        """Extract domain label from definition text"""
        # Common domain indicators
        domain_patterns = {
            'Law': ['legal', 'law', 'court', 'statute'],
            'Philosophy': ['philosophy', 'philosophical', 'metaphysical'],
            'Computing': ['computer', 'computing', 'software', 'algorithm'],
            'Economics': ['economic', 'economics', 'market', 'financial'],
            'Medicine': ['medical', 'medicine', 'clinical', 'therapeutic']
        }
        
        definition_lower = definition_text.lower()
        for domain, patterns in domain_patterns.items():
            if any(pattern in definition_lower for pattern in patterns):
                return domain
        
        return None
    
    def _determine_definition_status(self, definition_text: str) -> str:
        """Determine if definition is current, historical, or obsolete"""
        obsolete_indicators = ['obsolete', 'archaic', 'historical', 'no longer']
        definition_lower = definition_text.lower()
        
        if any(indicator in definition_lower for indicator in obsolete_indicators):
            return 'obsolete'
        
        # Add more sophisticated logic here
        return 'current'
    
    def _parse_quotations_from_data(self, quotations_data: Dict) -> List[Dict[str, Any]]:
        """Parse quotations from OED quotations data"""
        quotations = []
        
        # Handle different possible structures
        if 'quotations' in quotations_data:
            quotes = quotations_data['quotations']
        elif isinstance(quotations_data, list):
            quotes = quotations_data
        else:
            return quotations
        
        for quote in quotes:
            if isinstance(quote, dict):
                quotations.append({
                    'year': self._extract_year_from_quotation(quote),
                    'author': quote.get('author', ''),
                    'work_title': quote.get('work_title', quote.get('source', '')),
                    'text': quote.get('text', quote.get('quotation', ''))
                })
        
        return sorted(quotations, key=lambda x: x['year'] or 0)
    
    def _extract_year_from_quotation(self, quotation: Dict) -> Optional[int]:
        """Extract year from quotation data"""
        year_fields = ['year', 'date', 'publication_date']
        for field in year_fields:
            if field in quotation and quotation[field]:
                try:
                    year_str = str(quotation[field])
                    year_match = re.search(r'\b(1[0-9]{3}|20[0-2][0-9])\b', year_str)
                    if year_match:
                        return int(year_match.group(1))
                except (ValueError, TypeError):
                    continue
        return None
    
    def _assess_etymology_confidence(self, word_data: Dict) -> str:
        """Assess confidence level of etymology data"""
        # Simple heuristic based on available data
        confidence_indicators = 0
        
        if word_data.get('etymology'):
            confidence_indicators += 1
        if word_data.get('first_use_date'):
            confidence_indicators += 1
        if word_data.get('extracted_senses') and len(word_data['extracted_senses']) > 2:
            confidence_indicators += 1
        
        if confidence_indicators >= 2:
            return 'high'
        elif confidence_indicators == 1:
            return 'medium'
        else:
            return 'low'
    
    def _analyze_word_roots(self, etymology_text: str, term_text: str) -> Optional[Dict[str, Any]]:
        """Analyze word roots from etymology"""
        if not etymology_text:
            return None
        
        # Simple root analysis - could be enhanced
        return {
            "roots": [term_text[:3] if len(term_text) > 3 else term_text],
            "analysis": "Basic morphological analysis",
            "confidence": "low"
        }
    
    def _analyze_morphology(self, term_text: str, word_data: Dict) -> Optional[Dict[str, Any]]:
        """Analyze morphological structure"""
        morphology = {"type": "unknown", "components": []}
        
        # Simple morphological analysis
        if term_text.endswith('ent'):
            morphology["type"] = "agent_noun"
            morphology["suffixes"] = ["-ent"]
        elif term_text.endswith('er'):
            morphology["type"] = "agent_noun"
            morphology["suffixes"] = ["-er"]
        elif term_text.endswith('tion'):
            morphology["type"] = "abstract_noun"
            morphology["suffixes"] = ["-tion"]
        
        return morphology
    
    def _infer_domain_context(self, work_title: str) -> Optional[str]:
        """Infer domain context from work title"""
        domain_keywords = {
            'Law': ['law', 'legal', 'court', 'statute', 'constitution'],
            'Philosophy': ['philosophy', 'ethics', 'logic', 'metaphysics'],
            'Literature': ['novel', 'poem', 'poetry', 'literature'],
            'Science': ['science', 'nature', 'natural', 'experiment'],
            'Economics': ['economics', 'wealth', 'money', 'commerce']
        }
        
        title_lower = work_title.lower()
        for domain, keywords in domain_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return domain
        
        return None
    
    def _classify_usage_type(self, quotation_text: str) -> str:
        """Classify the type of usage in quotation"""
        # Simple classification - could be enhanced with ML
        if not quotation_text:
            return "unknown"
        
        text_lower = quotation_text.lower()
        
        if any(indicator in text_lower for indicator in ['metaphor', 'like', 'as if']):
            return "metaphorical"
        elif any(indicator in text_lower for indicator in ['technical', 'specifically', 'defined as']):
            return "technical"
        else:
            return "literal"
    
    def _detect_technical_usage(self, quotation_text: str) -> bool:
        """Detect if quotation represents technical usage"""
        technical_indicators = ['defined', 'technical', 'specifically', 'terminology', 'jargon']
        text_lower = quotation_text.lower() if quotation_text else ""
        return any(indicator in text_lower for indicator in technical_indicators)
    
    def _detect_semantic_shift(self, quotation_text: str, index: int, all_quotations: List[Dict]) -> bool:
        """Detect if quotation represents a semantic shift"""
        # Simple heuristic: if usage differs significantly from previous quotations
        if index == 0:
            return False
        
        # More sophisticated analysis could be implemented here
        return False
    
    def _group_by_periods(self, definitions: List[OEDDefinition], quotations: List[OEDQuotationSummary]) -> Dict[str, Any]:
        """Group definitions and quotations by historical periods"""
        periods = {}
        
        # Define period boundaries
        period_boundaries = {
            'historical_pre1950': (0, 1950),
            'modern_2000plus': (1950, 2000),
            'contemporary': (2000, 2030)
        }
        
        for period_name, (start, end) in period_boundaries.items():
            period_definitions = [d for d in definitions 
                                if d.first_cited_year and start <= d.first_cited_year < end]
            period_quotations = [q for q in quotations 
                               if q.quotation_year and start <= q.quotation_year < end]
            
            if period_definitions or period_quotations:
                quotation_years = [q.quotation_year for q in period_quotations if q.quotation_year]
                
                periods[period_name] = {
                    'start_year': start,
                    'end_year': end,
                    'definitions': period_definitions,
                    'quotations': period_quotations,
                    'quotation_span': max(quotation_years) - min(quotation_years) if quotation_years else 0,
                    'earliest_quotation': min(quotation_years) if quotation_years else None,
                    'latest_quotation': max(quotation_years) if quotation_years else None
                }
        
        return periods
    
    def _calculate_semantic_stability(self, period_data: Dict) -> Optional[float]:
        """Calculate semantic stability score for a period"""
        definitions = period_data['definitions']
        if not definitions:
            return None
        
        # Simple stability metric based on definition consistency
        # More sophisticated analysis could compare semantic similarity
        stability = 1.0 - (len(definitions) - 1) * 0.1
        return max(0.0, min(1.0, stability))
    
    def _detect_domain_shift(self, period_data: Dict) -> bool:
        """Detect if there's a domain shift in this period"""
        definitions = period_data['definitions']
        domains = set(d.domain_label for d in definitions if d.domain_label)
        return len(domains) > 1
    
    def _detect_pos_changes(self, period_data: Dict) -> Optional[List[str]]:
        """Detect part of speech changes in period"""
        definitions = period_data['definitions']
        pos_values = set(d.part_of_speech for d in definitions if d.part_of_speech)
        return list(pos_values) if pos_values else None


def enrich_term_with_oed(term_text: str, entry_id: str = None) -> Dict[str, Any]:
    """
    Convenience function to enrich a term with OED data
    
    Args:
        term_text: The term text to look up
        entry_id: Optional specific OED entry ID
    
    Returns:
        Dict with enrichment results
    """
    term = Term.query.filter_by(term_text=term_text).first()
    if not term:
        return {"success": False, "error": "Term not found in database"}
    
    service = OEDEnrichmentService()
    return service.enrich_term_with_oed_data(str(term.id), entry_id)