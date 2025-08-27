import re
import os
import sys
import logging
from typing import List, Dict, Any, Optional

from app import db
from app.models.text_segment import TextSegment

# Add shared services to path
shared_services_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'shared_services')
if shared_services_path not in sys.path:
    sys.path.insert(0, shared_services_path)

try:
    from shared_services.embedding.embedding_service import EmbeddingService
    from shared_services.embedding.file_processor import FileProcessingService
    from shared_services.ontology.entity_service import OntologyEntityService
    from shared_services.llm.base_service import BaseLLMService
    SHARED_SERVICES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Shared services not available: {e}")
    SHARED_SERVICES_AVAILABLE = False

logger = logging.getLogger(__name__)

class TextProcessingService:
    """Enhanced service for text processing, segmentation, and analysis using shared services"""
    
    def __init__(self):
        self.sentence_endings = re.compile(r'[.!?]+')
        self.paragraph_separator = re.compile(r'\n\s*\n')
        
        # Initialize shared services if available
        if SHARED_SERVICES_AVAILABLE:
            try:
                self.embedding_service = EmbeddingService()
                self.file_processor = FileProcessingService()
                self.ontology_service = OntologyEntityService()
                self.llm_service = BaseLLMService()
                self.enhanced_features_enabled = True
                logger.info("Enhanced text processing features enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize shared services: {e}")
                self.enhanced_features_enabled = False
        else:
            self.enhanced_features_enabled = False
        
    def create_initial_segments(self, document):
        """Create basic paragraph-level segments for a document"""
        try:
            content = document.content
            if not content:
                return
            
            # Split into paragraphs
            paragraphs = self.split_into_paragraphs(content)
            
            current_position = 0
            for i, paragraph_text in enumerate(paragraphs):
                if paragraph_text.strip():  # Skip empty paragraphs
                    # Find the actual position in the original text
                    start_pos = content.find(paragraph_text.strip(), current_position)
                    if start_pos == -1:
                        start_pos = current_position
                    end_pos = start_pos + len(paragraph_text.strip())
                    
                    # Create text segment
                    segment = TextSegment(
                        document_id=document.id,
                        content=paragraph_text.strip(),
                        segment_type='paragraph',
                        segment_number=i + 1,
                        start_position=start_pos,
                        end_position=end_pos,
                        level=0,
                        language=document.detected_language
                    )
                    
                    db.session.add(segment)
                    current_position = end_pos
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    def split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Split by double newlines or more
        paragraphs = self.paragraph_separator.split(text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting - can be improved with NLP libraries
        sentences = self.sentence_endings.split(text)
        result = []
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence:
                # Add back the sentence ending (except for the last one)
                if i < len(sentences) - 1:
                    # Look for the original ending
                    next_char_pos = text.find(sentence) + len(sentence)
                    if next_char_pos < len(text):
                        ending = text[next_char_pos]
                        if ending in '.!?':
                            sentence += ending
                result.append(sentence)
        
        return result
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract basic keywords from text"""
        # Simple keyword extraction - can be enhanced with NLP
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'can', 'this', 'that', 'these', 'those', 'a', 'an', 'as',
            'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'among', 'until', 'while', 'because',
            'if', 'when', 'where', 'what', 'which', 'who', 'how', 'why', 'there',
            'here', 'now', 'then', 'than', 'so', 'very', 'just', 'only', 'even',
            'also', 'too', 'much', 'many', 'more', 'most', 'some', 'any', 'no',
            'not', 'yes', 'all', 'both', 'each', 'every', 'other', 'another'
        }
        
        # Count word frequencies
        word_count = {}
        for word in words:
            if word not in stop_words and len(word) > 3:
                word_count[word] = word_count.get(word, 0) + 1
        
        # Return top keywords
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:20]]
    
    def calculate_readability_score(self, text: str) -> float:
        """Calculate a basic readability score"""
        if not text:
            return 0.0
        
        # Count sentences, words, and syllables (approximation)
        sentences = len(self.split_into_sentences(text))
        words = len(text.split())
        
        if sentences == 0 or words == 0:
            return 0.0
        
        # Approximate syllable count
        syllables = sum(self._count_syllables(word) for word in text.split())
        
        # Flesch Reading Ease approximation
        if sentences > 0 and words > 0:
            avg_sentence_length = words / sentences
            avg_syllables_per_word = syllables / words
            
            flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
            return max(0, min(100, flesch_score))  # Clamp between 0-100
        
        return 50.0  # Default moderate score
    
    def _count_syllables(self, word: str) -> int:
        """Approximate syllable count for a word"""
        word = word.lower().strip()
        if len(word) <= 3:
            return 1
        
        # Count vowel groups
        vowels = 'aeiouy'
        syllable_count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel
        
        # Adjust for silent 'e'
        if word.endswith('e'):
            syllable_count -= 1
        
        # Every word has at least one syllable
        return max(1, syllable_count)
    
    def detect_document_structure(self, text: str) -> Dict[str, Any]:
        """Detect basic document structure"""
        lines = text.split('\n')
        
        structure = {
            'total_lines': len(lines),
            'non_empty_lines': len([line for line in lines if line.strip()]),
            'paragraphs': len(self.split_into_paragraphs(text)),
            'sentences': len(self.split_into_sentences(text)),
            'has_headers': False,
            'has_lists': False,
            'has_numbered_sections': False
        }
        
        # Look for potential headers (lines that are short and followed by longer content)
        for i, line in enumerate(lines):
            line = line.strip()
            if line and len(line) < 100:
                # Check if followed by longer content
                if i + 1 < len(lines) and len(lines[i + 1].strip()) > len(line):
                    structure['has_headers'] = True
                    break
        
        # Look for lists
        list_indicators = ['•', '*', '-', '1.', '2.', '3.', 'a.', 'b.', 'c.']
        for line in lines:
            line = line.strip()
            for indicator in list_indicators:
                if line.startswith(indicator):
                    if indicator in ['1.', '2.', '3.']:
                        structure['has_numbered_sections'] = True
                    structure['has_lists'] = True
                    break
        
        return structure
    
    def segment_by_structure(self, document, structure_info: Dict[str, Any]):
        """Create segments based on detected document structure"""
        # This is a placeholder for more advanced segmentation
        # Could be enhanced to detect headers, sections, lists, etc.
        pass
    
    # Enhanced methods using shared services
    
    def process_file_content(self, file_path: str, file_type: str) -> str:
        """Process file and extract text content using shared services"""
        if not self.enhanced_features_enabled:
            logger.warning("Enhanced features not available, falling back to basic processing")
            return self._basic_file_processing(file_path, file_type)
        try:
            return self.file_processor.process_file(file_path, file_type)
        except Exception as e:
            logger.error(f"Error processing file with shared services: {e}")
            return self._basic_file_processing(file_path, file_type)

    def process_document(self, document):
        """Process a Document: extract content if file, create segments, and update stats.
        This is a minimal synchronous pipeline used after uploads."""
        try:
            # Extract content for files
            if document.content_type == 'file' and document.file_path and not document.content:
                ext = document.file_type or 'txt'
                content = self.process_file_content(document.file_path, ext)
                document.content = content
                document.content_preview = content[:500] + ('...' if len(content) > 500 else '') if content else None

            # Update counts
            if document.content:
                document.character_count = len(document.content)
                document.word_count = len(document.content.split())
                document.status = 'completed'

            db.session.commit()

            # Note: Segments are now created manually from document processing page
            # Removed automatic segmentation to allow user control
        except Exception as e:
            db.session.rollback()
            raise e
    
    def _basic_file_processing(self, file_path: str, file_type: str) -> str:
        """Basic file processing fallback"""
        if file_type.lower() in ['txt', 'text']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading text file: {e}")
                return ""
        else:
            logger.warning(f"File type {file_type} not supported in basic mode")
            return ""
    
    def chunk_text_for_processing(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """Split text into chunks suitable for LLM processing"""
        if self.enhanced_features_enabled:
            return self.file_processor.split_text(text, chunk_size, chunk_overlap)
        else:
            # Basic chunking fallback
            paragraphs = self.split_into_paragraphs(text)
            chunks = []
            current_chunk = ""
            
            for paragraph in paragraphs:
                if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    current_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            return chunks
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts using shared embedding service"""
        if not self.enhanced_features_enabled:
            logger.warning("Enhanced features not available, cannot generate embeddings")
            return []
        
        try:
            return self.embedding_service.embed_documents(texts)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return []
    
    def extract_ontology_entities(self, text: str, ontology_id: str = "engineering-ethics") -> List[Dict[str, Any]]:
        """Extract entities from text using ontology knowledge"""
        if not self.enhanced_features_enabled:
            logger.warning("Enhanced features not available, falling back to basic keyword extraction")
            keywords = self.extract_keywords(text)
            return [{"text": kw, "type": "keyword", "confidence": 0.5} for kw in keywords[:10]]
        
        try:
            # Get ontology entities for reference
            ontology_entities = self.ontology_service.get_entities(ontology_id)
            
            # Use LLM to extract entities based on ontology knowledge
            entity_types = list(ontology_entities.get("entities", {}).keys())
            if entity_types:
                return self.llm_service.extract_entities(text, entity_types)
            else:
                # Fallback to basic extraction
                return self.llm_service.extract_entities(text)
                
        except Exception as e:
            logger.error(f"Error extracting ontology entities: {e}")
            return []
    
    def summarize_with_llm(self, text: str, max_length: int = 500) -> str:
        """Generate summary using LLM service"""
        if not self.enhanced_features_enabled:
            logger.warning("Enhanced features not available, cannot generate LLM summary")
            return text[:max_length] + "..." if len(text) > max_length else text
        
        try:
            return self.llm_service.summarize_text(text, max_length)
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return text[:max_length] + "..." if len(text) > max_length else text
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        if not self.enhanced_features_enabled:
            # Basic word overlap similarity
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            return len(intersection) / len(union) if union else 0.0
        
        try:
            embedding1 = self.embedding_service.get_embedding(text1)
            embedding2 = self.embedding_service.get_embedding(text2)
            return self.embedding_service.similarity(embedding1, embedding2)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all shared services"""
        status = {
            "enhanced_features_enabled": self.enhanced_features_enabled,
            "shared_services_available": SHARED_SERVICES_AVAILABLE
        }
        
        if self.enhanced_features_enabled:
            status.update({
                "embedding_providers": self.embedding_service.get_provider_status(),
                "llm_providers": self.llm_service.get_provider_status(),
                "file_processor_types": self.file_processor.get_supported_types(),
                "available_ontologies": len(self.ontology_service.list_ontologies())
            })
        
        return status
