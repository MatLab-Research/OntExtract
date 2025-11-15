"""
Text Segmentation Module

Handles all text segmentation operations (paragraphs, sentences, semantic chunks, structure).
"""

import re
import logging
from typing import List, Dict, Any
import nltk
import spacy

from app import db
from app.models.text_segment import TextSegment
from app.text_utils import clean_jstor_boilerplate

logger = logging.getLogger(__name__)

# Load spacy model
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    nlp = None


class TextSegmentation:
    """Handles text segmentation operations"""

    def __init__(self):
        self.sentence_endings = re.compile(r'[.!?]+')
        self.paragraph_separator = re.compile(r'\n\s*\n')

    def create_initial_segments(self, document):
        """Create basic paragraph-level segments for a document"""
        try:
            content = clean_jstor_boilerplate(document.content)
            if not content:
                return

            paragraphs = self.split_into_paragraphs(content)

            current_position = 0
            for i, paragraph_text in enumerate(paragraphs):
                if paragraph_text.strip():
                    start_pos = content.find(paragraph_text.strip(), current_position)
                    if start_pos == -1:
                        start_pos = current_position
                    end_pos = start_pos + len(paragraph_text.strip())

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
        """Split text into paragraphs using improved regex patterns"""
        paragraphs = re.split(r'\n\s*\n', text.strip())
        return [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]

    def segment_by_paragraphs(self, document):
        """Create paragraph-level segments for a document"""
        try:
            content = clean_jstor_boilerplate(document.content)
            if not content:
                return

            paragraphs = self.split_into_paragraphs(content)

            current_position = 0
            for i, paragraph_text in enumerate(paragraphs):
                if paragraph_text.strip():
                    start_pos = content.find(paragraph_text, current_position)
                    if start_pos == -1:
                        start_pos = current_position
                    end_pos = start_pos + len(paragraph_text)

                    segment = TextSegment(
                        document_id=document.id,
                        content=paragraph_text,
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

    def segment_by_sentences(self, document):
        """Create sentence-level segments for a document using spaCy"""
        try:
            content = clean_jstor_boilerplate(document.content)
            if not content or not nlp:
                return

            doc = nlp(content)

            for i, sent in enumerate(doc.sents):
                segment = TextSegment(
                    document_id=document.id,
                    content=sent.text,
                    segment_type='sentence',
                    segment_number=i + 1,
                    start_position=sent.start_char,
                    end_position=sent.end_char,
                    level=1,
                    language=document.detected_language
                )
                db.session.add(segment)

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            raise e

    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using NLTK punkt tokenizer"""
        from nltk.tokenize import sent_tokenize

        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt_tab', quiet=True)

        sentences = sent_tokenize(text)
        return [s.strip() for s in sentences if len(s.strip()) > 15]

    def split_into_semantic_chunks(self, text: str) -> List[str]:
        """Split text into semantic chunks using spaCy NLP analysis"""
        try:
            from nltk.tokenize import sent_tokenize

            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt_tab', quiet=True)

            # Try spaCy for entity-aware chunking
            if nlp:
                doc = nlp(text)
                current_chunk = []
                chunks = []

                for sent in doc.sents:
                    current_chunk.append(sent.text.strip())
                    if len(current_chunk) >= 3 or (sent.ents and len(current_chunk) >= 2):
                        chunks.append(' '.join(current_chunk))
                        current_chunk = []

                if current_chunk:
                    chunks.append(' '.join(current_chunk))

                return [c for c in chunks if len(c.strip()) > 20]
            else:
                # Fallback to sentence-based chunking
                sentences = sent_tokenize(text)
                chunk_size = max(2, len(sentences) // 10)
                chunks = []
                for i in range(0, len(sentences), chunk_size):
                    chunk = ' '.join(sentences[i:i+chunk_size])
                    if len(chunk.strip()) > 20:
                        chunks.append(chunk)
                return chunks

        except Exception as e:
            logger.error(f"Error in semantic chunking: {e}")
            return self.split_into_paragraphs(text)

    def segment_by_structure(self, document, structure_info: Dict[str, Any]):
        """Create segments based on detected document structure"""
        # Placeholder for more advanced segmentation
        pass
