"""
Text Analysis Module

Handles text analysis operations (keywords, readability, structure detection).
"""

import re
import logging
from typing import List, Dict, Any

from .segmentation import TextSegmentation

logger = logging.getLogger(__name__)


class TextAnalysis:
    """Handles text analysis operations"""

    def __init__(self):
        self.segmenter = TextSegmentation()

    def extract_keywords(self, text: str) -> List[str]:
        """Extract basic keywords from text"""
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
        """Calculate a basic readability score (Flesch Reading Ease)"""
        if not text:
            return 0.0

        sentences = len(self.segmenter.split_into_sentences(text))
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
            return max(0, min(100, flesch_score))

        return 50.0

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

        return max(1, syllable_count)

    def detect_document_structure(self, text: str) -> Dict[str, Any]:
        """Detect basic document structure"""
        lines = text.split('\n')

        structure = {
            'total_lines': len(lines),
            'non_empty_lines': len([line for line in lines if line.strip()]),
            'paragraphs': len(self.segmenter.split_into_paragraphs(text)),
            'sentences': len(self.segmenter.split_into_sentences(text)),
            'has_headers': False,
            'has_lists': False,
            'has_numbered_sections': False
        }

        # Look for potential headers
        for i, line in enumerate(lines):
            line = line.strip()
            if line and len(line) < 100:
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
