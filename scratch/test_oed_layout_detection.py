import os
import pytest

from app.services.oed_parser_final import OEDParser


def make_pages(lines):
    return [{
        'width': 600,
        'height': 800,
        'lines': lines,
    }]


def test_quote_candidates_basic():
    parser = OEDParser()
    pages = make_pages([
        {'y': 100, 'left': 'a1832', 'right': 'First use of the term in context.'},
        {'y': 110, 'left': '', 'right': 'Continuation of the same quotation.'},
        {'y': 200, 'left': '1901', 'right': 'Another dated quotation.'},
    ])
    cands = parser._extract_quote_candidates(pages)
    assert len(cands) == 2
    assert cands[0]['year'] == '1832'
    assert 'Continuation' in cands[0]['text']
    assert cands[1]['year'] == '1901'


def test_serialize_structured_text_outputs_quote_lines():
    parser = OEDParser()
    pages = make_pages([
        {'y': 50, 'left': 'Preface', 'right': ''},
        {'y': 100, 'left': '1832', 'right': 'Quoted example.'},
        {'y': 130, 'left': '', 'right': 'More text of the quote.'},
        {'y': 200, 'left': 'Etymology', 'right': 'From Latin ...'},
    ])
    text = parser._serialize_structured_text(pages)
    # Expect a QUOTE line with year and text
    assert '[QUOTE] year=1832' in text
    assert 'Quoted example.' in text
    assert 'More text of the quote.' in text
