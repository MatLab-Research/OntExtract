import re
from typing import List, Dict, Any
from app import db
from app.models.text_segment import TextSegment

class TextProcessingService:
    """Service for basic text processing and segmentation"""
    
    def __init__(self):
        self.sentence_endings = re.compile(r'[.!?]+')
        self.paragraph_separator = re.compile(r'\n\s*\n')
        
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
