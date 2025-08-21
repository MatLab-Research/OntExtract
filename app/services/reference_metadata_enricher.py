import os
import re
from typing import Dict, Any, List, Optional
import logging

import pypdf
from shared_services.zotero.zotero_service import ZoteroService
from shared_services.zotero.metadata_mapper import ZoteroMetadataMapper

logger = logging.getLogger(__name__)


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

    def __init__(self, abstract_max_chars: int = 1000, use_zotero: bool = True):
        self.abstract_max_chars = abstract_max_chars
        self.use_zotero = use_zotero
        self.zotero_service = None
        
        # Initialize Zotero service if enabled
        if self.use_zotero:
            try:
                self.zotero_service = ZoteroService()
                logger.info("Zotero service initialized for metadata enrichment")
            except Exception as e:
                logger.warning(f"Could not initialize Zotero service: {str(e)}")
                self.zotero_service = None

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

        # Research design (experimental; Phase 1b)
        design = self._extract_design(text_first_pages)
        if design:
            # Only set if not present or overwrite allowed
            if allow_overwrite or not (existing.get('design')):
                meta['design'] = design

        return meta

    def extract_with_zotero(self, pdf_path: str, title: Optional[str] = None,
                           existing: Optional[Dict[str, Any]] = None, 
                           allow_overwrite: bool = False) -> Dict[str, Any]:
        """
        Extract metadata using both PDF extraction and Zotero lookup.
        
        Args:
            pdf_path: Path to PDF file
            title: Document title (if known)
            existing: Existing metadata
            allow_overwrite: Whether to overwrite existing values
            
        Returns:
            Combined metadata from PDF and Zotero
        """
        # First get PDF metadata
        pdf_meta = self.extract(pdf_path, existing, allow_overwrite)
        
        # If Zotero is not available, return PDF metadata
        if not self.zotero_service:
            return pdf_meta
        
        # Try to find document in Zotero
        zotero_matches = []
        
        # Use title from PDF extraction or provided title
        search_title = title or pdf_meta.get('title') or (existing or {}).get('title')
        search_doi = pdf_meta.get('doi') or (existing or {}).get('doi')
        search_authors = pdf_meta.get('authors') or (existing or {}).get('authors')
        search_year = pdf_meta.get('publication_date') or (existing or {}).get('publication_date')
        
        # Search Zotero
        if search_doi or search_title:
            try:
                zotero_matches = self.zotero_service.search_by_multiple_fields(
                    title=search_title,
                    doi=search_doi,
                    authors=search_authors if isinstance(search_authors, list) else None,
                    year=search_year
                )
            except Exception as e:
                logger.error(f"Error searching Zotero: {str(e)}")
        
        # If we found matches, merge the metadata
        if zotero_matches:
            best_match = zotero_matches[0]  # Already sorted by relevance
            zotero_meta = ZoteroMetadataMapper.map_to_source_metadata(best_match)
            
            # Log the match
            match_score = best_match['data'].get('_match_score', 0)
            match_type = best_match['data'].get('_match_type', 'unknown')
            logger.info(f"Found Zotero match (type: {match_type}, score: {match_score:.2f})")
            
            # Merge metadata - Zotero takes precedence for bibliographic data
            merged_meta = pdf_meta.copy()
            
            # Fields where Zotero should take precedence if available
            zotero_priority_fields = [
                'authors', 'title', 'publication_date', 'journal', 
                'doi', 'isbn', 'url', 'abstract', 'citation',
                'volume', 'issue', 'pages', 'publisher', 'place',
                'tags', 'proquest_url', 'source_database'
            ]
            
            for field in zotero_priority_fields:
                if field in zotero_meta and zotero_meta[field]:
                    # Only update if allowed or field is empty
                    if allow_overwrite or field not in merged_meta or not merged_meta[field]:
                        merged_meta[field] = zotero_meta[field]
            
            # Always add Zotero-specific metadata
            merged_meta['zotero_key'] = zotero_meta.get('zotero_key')
            merged_meta['zotero_match_score'] = match_score
            merged_meta['zotero_match_type'] = match_type
            
            # Merge research design info if present
            if 'design' in zotero_meta and not merged_meta.get('design'):
                merged_meta['design'] = zotero_meta['design']
            elif 'design' in zotero_meta and 'design' in merged_meta:
                # Merge design fields
                merged_meta['design'].update(zotero_meta['design'])
            
            return merged_meta
        
        return pdf_meta

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

    def _extract_design(self, text: str) -> Optional[Dict[str, Any]]:
        """Heuristically extract research design facets from early PDF text.

        Looks for common section headers and patterns (Method, Design, Participants, Measures, Hypotheses).
        Returns a lightweight dict suitable for source_metadata.design.
        """
        if not text:
            return None

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        blob = "\n".join(lines)

        # Hypotheses: capture lines starting with H1:, H2-, etc.
        hyps: List[str] = []
        for ln in lines[:120]:
            m = re.match(r"^(H\d+)\s*[:\-]\s*(.+)$", ln, re.I)
            if m:
                hyps.append(f"{m.group(1).upper()}: {m.group(2).strip()}")
        # Variables: simple keyword heuristics
        ivs: List[Dict[str, Any]] = []
        dvs: List[Dict[str, Any]] = []
        controls: List[str] = []
        for ln in lines[:200]:
            if re.search(r"independent variable|factor|manipulated", ln, re.I):
                ivs.append({"name": ln[:120]})
            if re.search(r"dependent variable|outcome|measured", ln, re.I):
                dvs.append({"name": ln[:120]})
            if re.search(r"control variable|covariate|held constant", ln, re.I):
                controls.append(ln[:120])

        # Design type guess
        dtype = None
        if re.search(r"random(ized|) (trial|experiment)|between\-subjects|within\-subjects", blob, re.I):
            dtype = "experimental"
        elif re.search(r"quasi\-experimental|natural experiment", blob, re.I):
            dtype = "quasi-experimental"
        elif re.search(r"survey|questionnaire|cross\-sectional|longitudinal", blob, re.I):
            dtype = "survey"
        elif re.search(r"observational|case study|ethnograph", blob, re.I):
            dtype = "observational"

        # Groups/conditions (very light): look for lines like Group A, Condition 1, Control, Treatment
        groups: List[Dict[str, Any]] = []
        for ln in lines[:200]:
            if re.search(r"\b(group|condition)\s+[A-Za-z0-9]+\b|\b(control|treatment)\b", ln, re.I):
                groups.append({"name": ln[:80]})
                if len(groups) >= 6:
                    break

        # Timeline
        timeline: Dict[str, Any] = {}
        if re.search(r"pre\-?test|baseline", blob, re.I):
            timeline["pre"] = True
        if re.search(r"post\-?test|follow\-?up", blob, re.I):
            timeline["post"] = True

        out: Dict[str, Any] = {}
        if dtype:
            out["type"] = dtype
        if hyps:
            out["hypotheses"] = hyps[:10]
        vars_obj: Dict[str, Any] = {}
        if ivs:
            vars_obj["independent"] = ivs[:5]
        if dvs:
            vars_obj["dependent"] = dvs[:5]
        if controls:
            vars_obj["control"] = controls[:8]
        if vars_obj:
            out["variables"] = vars_obj
        if groups:
            out["groups"] = groups
        if timeline:
            out["timeline"] = timeline

        return out or None

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
