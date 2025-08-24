"""
Merriam-Webster API integration for term definitions and thesaurus lookups.
Provides backend endpoints to avoid CORS restrictions.
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
import requests
import json
from datetime import datetime

merriam_bp = Blueprint('merriam', __name__, url_prefix='/api/merriam-webster')

# API Keys - in production, these should be in environment variables
API_KEYS = {
    'dictionary': '7c42d40c-0ef8-4379-98b6-f93c618c339a',
    'thesaurus': '24be515e-4e66-4131-99ba-44dcf62957ac'
}

# API Base URLs
API_URLS = {
    'dictionary': 'https://www.dictionaryapi.com/api/v3/references/collegiate/json',
    'thesaurus': 'https://www.dictionaryapi.com/api/v3/references/thesaurus/json'
}

@merriam_bp.route('/dictionary/<term>')
@login_required
def search_dictionary(term):
    """Search Merriam-Webster Collegiate Dictionary for term definition."""
    try:
        url = f"{API_URLS['dictionary']}/{term}"
        params = {'key': API_KEYS['dictionary']}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Process the response for better display
        processed_results = []
        
        if data and isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and 'meta' in entry:
                    processed_entry = {
                        'id': entry.get('meta', {}).get('id', ''),
                        'word': entry.get('hwi', {}).get('hw', ''),
                        'pronunciation': entry.get('hwi', {}).get('prs', []),
                        'functional_label': entry.get('fl', ''),
                        'definitions': entry.get('shortdef', []),
                        'etymology': entry.get('et', []),
                        'date': entry.get('date', ''),
                        'offensive': entry.get('meta', {}).get('offensive', False)
                    }
                    processed_results.append(processed_entry)
        
        # Get current date for citation and temporal period
        current_date = datetime.now()
        access_date = current_date.strftime("%B %d, %Y")
        current_year = current_date.year
        
        # Generate citation
        citation = f"Merriam-Webster.com Dictionary, s.v. \"{term},\" accessed {access_date}, https://www.merriam-webster.com/dictionary/{term}."
        
        return jsonify({
            'success': True,
            'term': term,
            'service': 'dictionary',
            'results': processed_results,
            'citation': citation,
            'access_date': access_date,
            'current_year': current_year,
            'raw_data': data  # Include raw data for debugging
        })
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Merriam-Webster Dictionary API error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch dictionary data',
            'details': str(e)
        }), 500
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error in dictionary search: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@merriam_bp.route('/thesaurus/<term>')
@login_required
def search_thesaurus(term):
    """Search Merriam-Webster Thesaurus for synonyms and antonyms."""
    try:
        url = f"{API_URLS['thesaurus']}/{term}"
        params = {'key': API_KEYS['thesaurus']}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Process the response for better display
        processed_results = []
        
        if data and isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and 'meta' in entry:
                    processed_entry = {
                        'id': entry.get('meta', {}).get('id', ''),
                        'word': entry.get('hwi', {}).get('hw', ''),
                        'functional_label': entry.get('fl', ''),
                        'synonyms': entry.get('meta', {}).get('syns', []),
                        'antonyms': entry.get('meta', {}).get('ants', []),
                        'shortdef': entry.get('shortdef', [])
                    }
                    processed_results.append(processed_entry)
        
        # Get current date for citation and temporal period
        current_date = datetime.now()
        access_date = current_date.strftime("%B %d, %Y")
        current_year = current_date.year
        
        # Generate citation
        citation = f"Merriam-Webster.com Thesaurus, s.v. \"{term},\" accessed {access_date}, https://www.merriam-webster.com/thesaurus/{term}."
        
        return jsonify({
            'success': True,
            'term': term,
            'service': 'thesaurus',
            'results': processed_results,
            'citation': citation,
            'access_date': access_date,
            'current_year': current_year,
            'raw_data': data  # Include raw data for debugging
        })
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Merriam-Webster Thesaurus API error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch thesaurus data',
            'details': str(e)
        }), 500
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error in thesaurus search: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@merriam_bp.route('/test')
@login_required
def test_api():
    """Test endpoint to verify API connectivity."""
    return jsonify({
        'message': 'Merriam-Webster API integration active',
        'endpoints': {
            'dictionary': '/api/merriam-webster/dictionary/<term>',
            'thesaurus': '/api/merriam-webster/thesaurus/<term>'
        },
        'api_keys_configured': {
            'dictionary': bool(API_KEYS['dictionary']),
            'thesaurus': bool(API_KEYS['thesaurus'])
        }
    })