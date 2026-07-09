"""Segmentation execution for experiment documents."""

from app import db
from app.models import ExperimentDocument
from app.models.experiment_processing import ExperimentDocumentProcessing, ProcessingArtifact, DocumentProcessingIndex


class PipelineSegmentationMixin:
    def _process_segmentation(
        self,
        processing_op: ExperimentDocumentProcessing,
        index_entry: DocumentProcessingIndex,
        exp_doc: ExperimentDocument,
        processing_method: str
    ):
        """Process segmentation for a document"""
        if not exp_doc.document.content:
            processing_op.mark_completed({'segments_created': 0})
            index_entry.status = 'completed'
            return

        import nltk
        from nltk.tokenize import sent_tokenize
        import re

        # Ensure NLTK data is available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt_tab', quiet=True)

        content = exp_doc.document.content
        segments = []

        if processing_method == 'paragraph':
            # Enhanced paragraph splitting
            normalized_content = re.sub(r'\r\n|\r', '\n', content.strip())
            normalized_content = re.sub(r'\n{3,}', '\n\n', normalized_content)
            initial_paragraphs = re.split(r'\n\s*\n', normalized_content)

            processed_paragraphs = []
            for para in initial_paragraphs:
                para = para.strip()
                if len(para) < 20:
                    continue

                sentences_in_para = sent_tokenize(para)

                if len(sentences_in_para) > 1 or len(para) > 100:
                    processed_paragraphs.append(para)
                elif len(para) > 50:
                    processed_paragraphs.append(para)

            segments = processed_paragraphs

        elif processing_method == 'sentence':
            # NLTK sentence tokenization
            segments = sent_tokenize(content)
            segments = [s.strip() for s in segments if len(s.strip()) > 15]

        else:  # semantic
            # spaCy semantic chunking
            import spacy
            nlp = spacy.load('en_core_web_sm')
            doc = nlp(content)

            current_chunk = []
            chunks = []

            for sent in doc.sents:
                current_chunk.append(sent.text.strip())
                if len(current_chunk) >= 3 or (sent.ents and len(current_chunk) >= 2):
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []

            if current_chunk:
                chunks.append(' '.join(current_chunk))

            segments = [c for c in chunks if len(c.strip()) > 20]

        # Create artifacts for all segments
        for i, segment in enumerate(segments):
            if segment.strip():
                artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='text_segment',
                    artifact_index=i
                )
                artifact.set_content({
                    'text': segment.strip(),
                    'segment_type': processing_method,
                    'position': i
                })
                artifact.set_metadata({
                    'method': processing_method,
                    'length': len(segment),
                    'word_count': len(segment.split())
                })
                db.session.add(artifact)

        # Calculate metrics
        if segments:
            avg_length = sum(len(seg) for seg in segments) // len(segments)
            total_words = sum(len(seg.split()) for seg in segments)
            avg_words = total_words // len(segments)
        else:
            avg_length = 0
            avg_words = 0

        # Determine service used
        if processing_method == 'paragraph':
            service_used = "NLTK-Enhanced Paragraph Detection"
            model_info = "Punkt tokenizer + smart filtering"
        elif processing_method == 'sentence':
            service_used = "NLTK Punkt Tokenizer"
            model_info = "Pre-trained sentence boundary detection"
        else:
            service_used = "spaCy NLP + NLTK"
            model_info = "en_core_web_sm + punkt tokenizer"

        processing_op.mark_completed({
            'segmentation_method': processing_method,
            'segments_created': len(segments),
            'avg_segment_length': avg_length,
            'avg_words_per_segment': avg_words,
            'total_tokens': sum(len(seg.split()) for seg in segments),
            'service_used': service_used,
            'model_info': model_info
        })
        index_entry.status = 'completed'
