import json
from collections import defaultdict
from typing import Dict, List, Tuple, Any

from app.models.document import Document


class DomainComparisonService:
    """Service to run cross-domain comparison experiments.

    Contract:
    - Input: experiment (with experiment_type == 'domain_comparison'), TextProcessingService instance
    - Uses: experiment.configuration JSON for optional fields:
        {
          "target_terms": ["ontology", "agent"],
          "discipline_assignments": { "Philosophy": [docId, ...], "Engineering": [docId, ...] },
          "discipline_fallback": "journal|context|none"
        }
      If missing, will default target_terms to ["ontology", "agent"], and infer disciplines from
      reference.source_metadata.journal or .context where available, else "General".
    - Scope: All experiment.references are considered (ignoring include_in_analysis flag for now).
    - Output: (results_dict, human_summary)
    """

    def run(self, experiment, text_service) -> Tuple[Dict[str, Any], str]:
        # Parse configuration
        try:
            cfg = json.loads(experiment.configuration) if experiment.configuration else {}
        except Exception:
            cfg = {}

        target_terms: List[str] = cfg.get("target_terms") or ["ontology", "agent"]
        discipline_assignments: Dict[str, List[int]] = cfg.get("discipline_assignments") or {}
        discipline_fallback: str = cfg.get("discipline_fallback") or "journal"

        # Gather references: use all references linked to the experiment
        references: List[Document] = list(experiment.references) if hasattr(experiment, 'references') else []

        # Build discipline buckets
        discipline_docs: Dict[str, List[Document]] = defaultdict(list)

        if discipline_assignments:
            # Explicit mapping provided
            ref_by_id = {ref.id: ref for ref in references}
            for discipline, ids in discipline_assignments.items():
                for _id in ids:
                    if _id in ref_by_id:
                        discipline_docs[discipline].append(ref_by_id[_id])
        else:
            # Infer from metadata
            for ref in references:
                discipline = self._infer_discipline(ref, fallback=discipline_fallback)
                discipline_docs[discipline].append(ref)

        # Extract term-specific definitions/snippets per discipline
        per_term_data: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for term in target_terms:
            per_term_data[term] = {}
            for discipline, docs in discipline_docs.items():
                entries: List[Dict[str, Any]] = []
                for doc in docs:
                    snippet = self._extract_term_snippet(doc, term)
                    if snippet:
                        entries.append({
                            "document_id": doc.id,
                            "title": doc.title,
                            "reference_subtype": doc.reference_subtype,
                            "source": (doc.source_metadata or {}).get("journal") or (doc.source_metadata or {}).get("context"),
                            "snippet": snippet
                        })
                if entries:
                    per_term_data[term][discipline] = entries

        # Compute similarity matrices per term across disciplines
        similarity_matrices: Dict[str, Dict[str, Dict[str, float]]] = {}
        for term, disc_entries in per_term_data.items():
            disciplines = sorted(disc_entries.keys())
            matrix: Dict[str, Dict[str, float]] = {d: {} for d in disciplines}
            for i, d1 in enumerate(disciplines):
                text1 = self._concat_snippets(disc_entries[d1])
                for j, d2 in enumerate(disciplines):
                    if j < i:
                        # mirror
                        matrix[d1][d2] = matrix[d2][d1]
                        continue
                    text2 = self._concat_snippets(disc_entries[d2])
                    if d1 == d2:
                        sim = 1.0
                    else:
                        sim = text_service.calculate_similarity(text1, text2)
                    matrix[d1][d2] = float(sim)
            similarity_matrices[term] = matrix

        # Build human summary
        discipline_count = len(discipline_docs)
        ref_count = sum(len(docs) for docs in discipline_docs.values())
        term_count = len(target_terms)
        summary = f"Compared {term_count} terms across {discipline_count} disciplines using {ref_count} references."

        # Assemble results
        results: Dict[str, Any] = {
            "experiment_type": "domain_comparison",
            "target_terms": target_terms,
            "disciplines": sorted(discipline_docs.keys()),
            "per_term_data": per_term_data,
            "similarity_matrices": similarity_matrices,
        }

        return results, summary

    def _infer_discipline(self, ref: Document, fallback: str = "journal") -> str:
        meta = ref.source_metadata or {}
        if fallback == "context" and meta.get("context"):
            return meta.get("context")
        if fallback == "journal" and meta.get("journal"):
            return meta.get("journal")
        # Try URL host as a last resort
        url = meta.get("url") or ""
        if "oed" in url.lower():
            return "OED"
        return "General"

    def _extract_term_snippet(self, ref: Document, term: str) -> str:
        """Very simple heuristic extractor for a term definition/snippet from the reference content."""
        if not ref.content:
            return ""
        text = ref.content
        t_lower = term.lower()

        # If it's our general dictionary format, look for a section
        if ref.reference_subtype and ref.reference_subtype.startswith("dictionary"):
            # Prefer lines containing the term and following content
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            # Try to locate a definition line by proximity to the term
            for idx, ln in enumerate(lines):
                if t_lower in ln.lower():
                    # Concatenate a small window around the line
                    window = lines[max(0, idx-1): min(len(lines), idx+3)]
                    snippet = " ".join(window)
                    return snippet[:600]
            # Fallback: first 2 paragraphs
            return " ".join(lines[:5])[:600]

        # For other reference types, take a relevant paragraph containing the term
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for p in paragraphs:
            if t_lower in p.lower():
                return p[:600]
        # Fallback to first paragraph
        return paragraphs[0][:600] if paragraphs else text[:600]

    def _concat_snippets(self, entries: List[Dict[str, Any]]) -> str:
        return "\n\n".join(e.get("snippet", "") for e in entries if e.get("snippet"))
