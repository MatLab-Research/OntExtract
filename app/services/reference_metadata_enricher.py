import os
import re
from typing import Dict, Any, List, Optional

import pypdf


class ReferenceMetadataEnricher:
    """Phase 1: Lightweight PDF heuristics to prefill reference metadata.

    Safe defaults:
    - Only fills missing fields.
    - Short abstracts only (<= 1000 chars).
    - Never overwrites user-provided values unless allow_overwrite=True.
    """

    DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
    DOI_URL_RE = re.compile(r"doi\.org/([\w./-]+)", re.I)
    YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
    ISBN_RE = re.compile(r"\b97[89][-\s]?(?:\d[-\s]?){9}[\dxX]\b|\b(?:\d[-\s]?){9}[\dxX]\b")

    def __init__(self, abstract_max_chars: int = 1000):
        self.abstract_max_chars = abstract_max_chars

    def extract(self, pdf_path: str, existing: Optional[Dict[str, Any]] = None, allow_overwrite: bool = False) -> Dict[str, Any]:
        existing = existing or {}
        meta: Dict[str, Any] = {}

        try:
            with open(pdf_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                docinfo = reader.metadata or {}
                text_first_pages = self._extract_first_pages(reader, pages=3)
        except Exception:
            return {}

        # PDF metadata
        title_meta = self._clean(docinfo.get('/Title') or docinfo.get('title'))
        author_meta = self._clean(docinfo.get('/Author') or docinfo.get('author'))
        if title_meta:
            self._maybe_set(meta, 'title', title_meta, existing, allow_overwrite)
        if author_meta:
            self._maybe_set(meta, 'authors', self._split_authors(author_meta), existing, allow_overwrite)

        # Heuristic from text
        lines = [l.strip() for l in text_first_pages.splitlines()]
        non_empty = [l for l in lines if l]
        if non_empty:
            # Title candidate: first non-empty line (trim overly long)
            title_guess = non_empty[0]
            if 5 <= len(title_guess) <= 300:
                self._maybe_set(meta, 'title', title_guess, existing, allow_overwrite)

        # Authors: look at next ~6 lines for names
        author_lines = non_empty[1:7]
        authors_guess = self._guess_authors(author_lines)
        if authors_guess:
            self._maybe_set(meta, 'authors', authors_guess, existing, allow_overwrite)

        # DOI
        doi = self._find_doi(text_first_pages)
        if doi:
            self._maybe_set(meta, 'doi', doi, existing, allow_overwrite)

        # ISBN
        isbn = self._find_isbn(text_first_pages)
        if isbn:
            self._maybe_set(meta, 'isbn', isbn, existing, allow_overwrite)

        # Year
        year = self._find_year_near_header(non_empty[:20]) or self._find_year(text_first_pages)
        if year:
            self._maybe_set(meta, 'publication_date', year, existing, allow_overwrite)

        # Abstract
        abstract = self._extract_abstract(text_first_pages)
        if abstract:
            self._maybe_set(meta, 'abstract', abstract[: self.abstract_max_chars], existing, allow_overwrite)

        # Journal/Publisher hints (very light)
        journal = self._guess_journal(non_empty[:40])
        if journal:
            self._maybe_set(meta, 'journal', journal, existing, allow_overwrite)

        return meta

    # --- internals ---

    def _extract_first_pages(self, reader: pypdf.PdfReader, pages: int = 3) -> str:
        buf: List[str] = []
        for i in range(min(len(reader.pages), pages)):
            try:
                buf.append(reader.pages[i].extract_text() or "")
            except Exception:
                continue
        return "\n".join(buf)

    def _find_doi(self, text: str) -> Optional[str]:
        if not text:
            return None
        m = self.DOI_RE.search(text)
        if m:
            return m.group(0).rstrip(').,;')
        mu = self.DOI_URL_RE.search(text)
        if mu:
            return mu.group(1).rstrip(').,;')
        return None

    def _find_isbn(self, text: str) -> Optional[str]:
        m = self.ISBN_RE.search(text or '')
        return m.group(0) if m else None

    def _find_year(self, text: str) -> Optional[str]:
        m = self.YEAR_RE.search(text or '')
        return m.group(0) if m else None

    def _find_year_near_header(self, lines: List[str]) -> Optional[str]:
        for l in lines[:10]:
            y = self._find_year(l)
            if y:
                return y
        return None

    def _extract_abstract(self, text: str) -> Optional[str]:
        if not text:
            return None
        # Detect 'Abstract' heading; capture following paragraph(s) until blank line or next heading
        chunks = text.splitlines()
        for i, line in enumerate(chunks):
            if re.match(r"^\s*abstract\s*[:.]?\s*$", line, re.I):
                # gather subsequent lines until blank or heading-like
                buf: List[str] = []
                for j in range(i + 1, min(i + 40, len(chunks))):
                    ln = chunks[j].strip()
                    if not ln:
                        break
                    if re.match(r"^[A-Z][A-Za-z0-9\s]{0,30}$", ln) and len(ln.split()) <= 6:
                        # looks like a heading
                        break
                    buf.append(ln)
                if buf:
                    para = " ".join(buf)
                    return re.sub(r"\s+", " ", para).strip()
        return None

    def _guess_journal(self, lines: List[str]) -> Optional[str]:
        for l in lines:
            if re.search(r"Proceedings of|Journal of|Transactions of|ACM|IEEE|Springer|Elsevier|Wiley|Oxford|Cambridge", l, re.I):
                return l[:200]
        return None

    def _split_authors(self, s: str) -> List[str]:
        # Split on commas/and/semicolons; clean whitespace
        parts = re.split(r"\band\b|,|;", s, flags=re.I)
        out = [p.strip() for p in parts if p.strip()]
        # Filter obviously non-names
        out = [p for p in out if 2 <= len(p.split()) <= 4]
        return out[:10]

    def _guess_authors(self, lines: List[str]) -> List[str]:
        coll: List[str] = []
        for l in lines:
            if len(l) > 200:
                continue
            cand = self._split_authors(l)
            if cand:
                coll.extend(cand)
        # de-dup
        seen = set()
        uniq: List[str] = []
        for a in coll:
            if a.lower() in seen:
                continue
            seen.add(a.lower())
            uniq.append(a)
        return uniq[:10]

    def _clean(self, s: Optional[str]) -> Optional[str]:
        if not s:
            return s
        return re.sub(r"\s+", " ", s).strip()

    def _maybe_set(self, meta: Dict[str, Any], key: str, value: Any, existing: Dict[str, Any], allow_overwrite: bool):
        if value is None or value == "":
            return
        if not allow_overwrite and (key in existing and existing.get(key)):
            return
        meta[key] = value
