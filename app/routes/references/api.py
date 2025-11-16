"""
References API Routes

This module handles API endpoints for search and WordNet operations.

Routes:
- GET /references/api/search              - Search references
- GET /references/api/wordnet/search      - Search WordNet
- GET /references/api/wordnet/similarity  - Calculate WordNet similarity
"""

from flask import request, jsonify
from app.utils.auth_decorators import api_require_login_for_write
from app.models.document import Document
from app.services.wordnet_service import WordNetService

from . import references_bp


@references_bp.route('/api/search')
@api_require_login_for_write
def api_search():
    """Search references for autocomplete/selection"""
    query = request.args.get('q', '')

    if not query:
        references = Document.query.filter_by(
            document_type='reference'
        ).limit(20).all()
    else:
        references = Document.query.filter(
            Document.document_type == 'reference',
            Document.title.contains(query)
        ).limit(20).all()

    return jsonify([{
        'id': ref.id,
        'title': ref.title,
        'source_info': ref.get_source_info(),
        'citation': ref.get_citation()
    } for ref in references])


@references_bp.route('/api/wordnet/search')
@api_require_login_for_write
def api_wordnet_search():
    """Search WordNet for a word and return synsets with definitions."""
    word = request.args.get('q', '').strip()
    if not word:
        return jsonify({"success": False, "error": "Missing 'q' query parameter"}), 400

    service = WordNetService()
    data = service.search_word(word)
    status = 200 if data.get('success', True) else 500
    return jsonify(data), status


@references_bp.route('/api/wordnet/similarity')
@api_require_login_for_write
def api_wordnet_similarity():
    """Calculate semantic similarity between two words using WordNet."""
    word1 = request.args.get('word1', '').strip()
    word2 = request.args.get('word2', '').strip()

    if not word1 or not word2:
        return jsonify({"success": False, "error": "Missing 'word1' or 'word2' query parameters"}), 400

    service = WordNetService()
    data = service.get_word_similarity(word1, word2)
    status = 200 if data.get('success', True) else 500
    return jsonify(data), status
