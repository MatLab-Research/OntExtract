"""
WordNet service for semantic analysis and term definitions.
Provides access to WordNet lexical database via NLTK.
"""

import nltk
from nltk.corpus import wordnet as wn
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Ensure WordNet data is available
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    try:
        nltk.download('wordnet')
    except Exception as e:
        logger.warning(f"Could not download WordNet data: {e}")

class WordNetService:
    """Service for accessing WordNet lexical database."""
    
    def __init__(self):
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if WordNet is available."""
        try:
            # Try to access WordNet
            list(wn.synsets('test'))
            return True
        except Exception as e:
            logger.warning(f"WordNet not available: {e}")
            return False
    
    def search_word(self, word: str) -> Dict[str, Any]:
        """
        Search for a word in WordNet and return synsets with definitions.
        
        Args:
            word: The word to search for
            
        Returns:
            Dictionary with search results
        """
        if not self.available:
            return {
                "success": False,
                "error": "WordNet is not available. Please ensure NLTK WordNet data is installed."
            }
        
        word = word.strip().lower()
        if not word:
            return {"success": False, "error": "No word provided"}
        
        try:
            # Get all synsets for the word
            synsets = wn.synsets(word)
            
            if not synsets:
                return {
                    "success": True,
                    "word": word,
                    "synsets": [],
                    "message": f"No synsets found for '{word}'"
                }
            
            results = []
            pos_counts = {}
            
            for synset in synsets:
                # Get basic synset information
                synset_info = {
                    "name": synset.name(),
                    "pos": synset.pos(),
                    "pos_name": self._get_pos_name(synset.pos()),
                    "definition": synset.definition(),
                    "examples": synset.examples(),
                    "lemmas": [lemma.name().replace('_', ' ') for lemma in synset.lemmas()],
                }
                
                # Get synonyms (other lemmas in the same synset)
                synonyms = []
                for lemma in synset.lemmas():
                    lemma_name = lemma.name().replace('_', ' ')
                    if lemma_name.lower() != word:
                        synonyms.append(lemma_name)
                synset_info["synonyms"] = synonyms
                
                # Get antonyms
                antonyms = []
                for lemma in synset.lemmas():
                    for antonym in lemma.antonyms():
                        antonyms.append(antonym.name().replace('_', ' '))
                synset_info["antonyms"] = antonyms
                
                # Get hypernyms (more general terms)
                hypernyms = []
                for hypernym in synset.hypernyms():
                    hypernyms.append({
                        "name": hypernym.name(),
                        "definition": hypernym.definition(),
                        "lemmas": [lemma.name().replace('_', ' ') for lemma in hypernym.lemmas()]
                    })
                synset_info["hypernyms"] = hypernyms[:3]  # Limit to 3
                
                # Get hyponyms (more specific terms)  
                hyponyms = []
                for hyponym in synset.hyponyms():
                    hyponyms.append({
                        "name": hyponym.name(),
                        "definition": hyponym.definition(),
                        "lemmas": [lemma.name().replace('_', ' ') for lemma in hyponym.lemmas()]
                    })
                synset_info["hyponyms"] = hyponyms[:3]  # Limit to 3
                
                results.append(synset_info)
                
                # Count parts of speech
                pos = synset.pos()
                pos_counts[pos] = pos_counts.get(pos, 0) + 1
            
            return {
                "success": True,
                "word": word,
                "synsets": results,
                "total_synsets": len(results),
                "pos_distribution": pos_counts,
                "citation": "WordNet: A Lexical Database for English. Princeton University."
            }
            
        except Exception as e:
            logger.error(f"Error searching WordNet for '{word}': {e}")
            return {
                "success": False,
                "error": f"Error searching WordNet: {str(e)}"
            }
    
    def _get_pos_name(self, pos_code: str) -> str:
        """Convert POS code to readable name."""
        pos_names = {
            'n': 'noun',
            'v': 'verb', 
            'a': 'adjective',
            'r': 'adverb',
            's': 'adjective satellite'
        }
        return pos_names.get(pos_code, pos_code)
    
    def get_word_similarity(self, word1: str, word2: str) -> Dict[str, Any]:
        """
        Calculate semantic similarity between two words using WordNet.
        
        Args:
            word1: First word
            word2: Second word
            
        Returns:
            Dictionary with similarity information
        """
        if not self.available:
            return {
                "success": False,
                "error": "WordNet is not available"
            }
        
        try:
            synsets1 = wn.synsets(word1.strip().lower())
            synsets2 = wn.synsets(word2.strip().lower())
            
            if not synsets1 or not synsets2:
                return {
                    "success": True,
                    "similarity": 0.0,
                    "message": f"One or both words not found in WordNet"
                }
            
            # Find maximum similarity between any pair of synsets
            max_similarity = 0.0
            best_synsets = None
            
            for s1 in synsets1:
                for s2 in synsets2:
                    try:
                        sim = s1.path_similarity(s2)
                        if sim and sim > max_similarity:
                            max_similarity = sim
                            best_synsets = (s1, s2)
                    except:
                        continue
            
            result = {
                "success": True,
                "word1": word1,
                "word2": word2,
                "similarity": max_similarity,
            }
            
            if best_synsets:
                result["best_match"] = {
                    "synset1": best_synsets[0].name(),
                    "synset2": best_synsets[1].name(),
                    "definition1": best_synsets[0].definition(),
                    "definition2": best_synsets[1].definition()
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating similarity for '{word1}' and '{word2}': {e}")
            return {
                "success": False,
                "error": f"Error calculating similarity: {str(e)}"
            }