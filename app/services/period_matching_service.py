"""
Period Matching Service - Matches OED definitions to relevant time periods
based on their actual date ranges rather than applying all periods to all definitions
"""

from typing import Dict, List, Optional, Any, Tuple
import json
from datetime import datetime


class PeriodMatchingService:
    """Service for matching OED definitions to their relevant time periods"""
    
    def match_definitions_to_periods(self, 
                                    definitions: List[Dict], 
                                    target_years: List[int]) -> List[Dict]:
        """
        Match each OED definition to its relevant time periods based on date overlap
        
        Args:
            definitions: List of OED definition dicts with date information
            target_years: List of analysis years (e.g., [1957, 1976, 1995, 2018])
        
        Returns:
            List of definitions with matched relevant periods
        """
        
        enhanced_definitions = []
        
        for definition in definitions:
            enhanced_def = definition.copy()
            
            # Extract date range for this definition
            first_year = definition.get('first_cited_year')
            last_year = definition.get('last_cited_year')
            
            # Determine which target years are relevant for this definition
            relevant_years = self._find_relevant_years(
                first_year, last_year, target_years
            )
            
            # Store the matched periods
            enhanced_def['matched_periods'] = relevant_years
            enhanced_def['period_relevance_note'] = self._create_relevance_note(
                first_year, last_year, relevant_years
            )
            
            enhanced_definitions.append(enhanced_def)
        
        return enhanced_definitions
    
    def _find_relevant_years(self, 
                            first_year: Optional[int], 
                            last_year: Optional[int], 
                            target_years: List[int]) -> List[int]:
        """
        Find which target years are relevant for a definition based on its date range
        
        Args:
            first_year: First citation year of the definition
            last_year: Last citation year of the definition (None if still current)
            target_years: List of analysis years
        
        Returns:
            List of relevant years for this definition
        """
        
        if not first_year and not last_year:
            # No date information - consider all years potentially relevant
            return target_years
        
        relevant_years = []
        
        for year in target_years:
            # Check if this target year falls within the definition's active period
            if self._is_year_relevant(year, first_year, last_year):
                relevant_years.append(year)
        
        # If no exact matches, find the closest year
        if not relevant_years and (first_year or last_year):
            closest_year = self._find_closest_year(first_year, last_year, target_years)
            if closest_year:
                relevant_years = [closest_year]
        
        return relevant_years
    
    def _is_year_relevant(self, 
                         target_year: int, 
                         first_year: Optional[int], 
                         last_year: Optional[int]) -> bool:
        """
        Check if a target year falls within a definition's active period
        
        Args:
            target_year: Year to check
            first_year: Start of definition's period
            last_year: End of definition's period (None if still current)
        
        Returns:
            True if the year is relevant to this definition
        """
        
        # If no first year, we can't determine relevance
        if not first_year:
            return False
        
        # Check if target year is after the definition started
        if target_year < first_year:
            return False
        
        # If no last year, definition is still current
        if not last_year:
            return target_year >= first_year
        
        # Check if target year is within the range
        return first_year <= target_year <= last_year
    
    def _find_closest_year(self, 
                          first_year: Optional[int], 
                          last_year: Optional[int], 
                          target_years: List[int]) -> Optional[int]:
        """
        Find the closest target year to a definition's period
        
        Args:
            first_year: Start of definition's period
            last_year: End of definition's period
            target_years: List of analysis years
        
        Returns:
            Closest target year, or None if no reasonable match
        """
        
        if not target_years:
            return None
        
        # Use the midpoint of the definition's period as reference
        if first_year and last_year:
            reference_year = (first_year + last_year) // 2
        elif first_year:
            reference_year = first_year
        elif last_year:
            reference_year = last_year
        else:
            return None
        
        # Find the closest target year
        closest_year = min(target_years, key=lambda y: abs(y - reference_year))
        
        # Only return if reasonably close (within 50 years)
        if abs(closest_year - reference_year) <= 50:
            return closest_year
        
        return None
    
    def _create_relevance_note(self, 
                              first_year: Optional[int], 
                              last_year: Optional[int], 
                              relevant_years: List[int]) -> str:
        """
        Create a human-readable note about period relevance
        
        Args:
            first_year: Start of definition's period
            last_year: End of definition's period
            relevant_years: Years matched to this definition
        
        Returns:
            Human-readable relevance note
        """
        
        if not relevant_years:
            return "No matching analysis periods"
        
        if first_year and last_year:
            period_desc = f"{first_year}-{last_year}"
        elif first_year:
            period_desc = f"{first_year}-present"
        elif last_year:
            period_desc = f"until {last_year}"
        else:
            period_desc = "undated"
        
        years_str = ", ".join(map(str, sorted(relevant_years)))
        
        return f"Definition period ({period_desc}) relevant to: {years_str}"
    
    def create_period_specific_excerpt(self, 
                                      definition: Dict, 
                                      relevant_years: List[int]) -> str:
        """
        Create an excerpt that highlights the definition's relevance to specific periods
        
        Args:
            definition: OED definition dict
            relevant_years: Years this definition is relevant to
        
        Returns:
            Period-specific excerpt
        """
        
        # Get the definition text
        def_text = (definition.get('definition_excerpt') or 
                   definition.get('definition_text') or 
                   definition.get('text') or '')
        
        if not def_text:
            return "No definition text available"
        
        # If already has excerpt, use it
        if definition.get('definition_excerpt'):
            return def_text
        
        # Create excerpt (first 200 chars)
        excerpt = def_text[:200]
        if len(def_text) > 200:
            excerpt += "..."
        
        return excerpt
    
    def enhance_definitions_with_period_matching(self,
                                                definitions: List[Dict],
                                                target_years: List[int],
                                                term: str) -> List[Dict]:
        """
        Enhanced method that both matches periods and creates appropriate excerpts
        
        Args:
            definitions: List of OED definitions
            target_years: Analysis years
            term: The term being analyzed
            
        Returns:
            Enhanced definitions with period matching and excerpts
        """
        
        # First, match definitions to their relevant periods
        matched_definitions = self.match_definitions_to_periods(definitions, target_years)
        
        # Then enhance each definition with period-specific information
        for definition in matched_definitions:
            relevant_years = definition.get('matched_periods', [])
            
            # Create period-specific excerpt
            definition['period_relevant_excerpt'] = self.create_period_specific_excerpt(
                definition, relevant_years
            )
            
            # Set relevance info
            definition['relevant_periods'] = relevant_years
            definition['excerpt_relevance'] = definition.get('period_relevance_note', '')
            
            # Clean up temporary fields
            if 'matched_periods' in definition:
                del definition['matched_periods']
            if 'period_relevance_note' in definition:
                del definition['period_relevance_note']
        
        return matched_definitions
