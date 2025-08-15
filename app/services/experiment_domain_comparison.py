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
          "discipline_fallback": "journal|context|none",
          "design": {
            "type": "experimental|quasi-experimental|survey|observational",
            "variables": {"independent": [{"name": str, "levels": [str, ...]}]},
            "groups": [{"name": str}]
          }
        }
      Defaults: target_terms -> ["ontology", "agent"].
      If no design grouping is provided, will group by disciplines inferred from metadata.
    - Scope: All experiment.references are considered.
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
        design: Dict[str, Any] = cfg.get("design") or {}

        # Gather references: use all references linked to the experiment
        references: List[Document] = list(experiment.references) if hasattr(experiment, "references") else []

        # Decide grouping mode: design-based groups/levels or discipline buckets
        buckets: Dict[str, List[Document]] = defaultdict(list)

        # Helper: map references to a best-fit bucket by simple metadata matching
        def assign_by_name(names: List[str]) -> None:
            name_lowers = [(n, n.lower()) for n in names if n]
            for ref in references:
                meta = ref.source_metadata or {}
                hay = " ".join([
                    (meta.get("journal") or ""),
                    (meta.get("context") or ""),
                    (meta.get("url") or ""),
                    (ref.title or ""),
                ]).lower()
                placed = False
                for display, nl in name_lowers:
                    if nl and nl in hay:
                        buckets[display].append(ref)
                        placed = True
                        break
                if not placed:
                    buckets["Other"].append(ref)

        # Normalize design groups and IV levels
        design_groups: List[str] = [
            str(g.get("name")) for g in (design.get("groups") or [])
            if isinstance(g, dict) and g.get("name")
        ]
        iv_levels: List[str] = []
        try:
            ivs = (design.get("variables") or {}).get("independent") or []
            if ivs and isinstance(ivs[0], dict):
                levels = ivs[0].get("levels")
                if isinstance(levels, list):
                    iv_levels = [str(x) for x in levels if x is not None]
        except Exception:
            iv_levels = []

        if design_groups:
            assign_by_name(design_groups)
            grouping_label = "groups"
        elif iv_levels:
            assign_by_name(iv_levels)
            grouping_label = "iv_levels"
        else:
            # Build discipline buckets (explicit mapping wins)
            if discipline_assignments:
                ref_by_id = {ref.id: ref for ref in references}
                for discipline, ids in discipline_assignments.items():
                    for _id in ids:
                        if _id in ref_by_id:
                            buckets[discipline].append(ref_by_id[_id])
            else:
                for ref in references:
                    discipline = self._infer_discipline(ref, fallback=discipline_fallback)
                    buckets[discipline].append(ref)
            grouping_label = "disciplines"

        # Extract term-specific definitions/snippets per bucket
        per_term_data: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for term in target_terms:
            per_term_data[term] = {}
            for bucket_name, docs in buckets.items():
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
                    per_term_data[term][bucket_name] = entries

        # Compute similarity matrices per term across buckets
        similarity_matrices: Dict[str, Dict[str, Dict[str, float]]] = {}
        for term, bucket_entries in per_term_data.items():
            names = sorted(bucket_entries.keys())
            matrix: Dict[str, Dict[str, float]] = {n: {} for n in names}
            for i, n1 in enumerate(names):
                text1 = self._concat_snippets(bucket_entries[n1])
                for j, n2 in enumerate(names):
                    if j < i:
                        matrix[n1][n2] = matrix[n2][n1]
                        continue
                    text2 = self._concat_snippets(bucket_entries[n2])
                    if n1 == n2:
                        sim = 1.0
                    else:
                        sim = text_service.calculate_similarity(text1, text2)
                    matrix[n1][n2] = float(sim)
            similarity_matrices[term] = matrix

        # Build human summary
        bucket_count = len(buckets)
        ref_count = sum(len(docs) for docs in buckets.values())
        term_count = len(target_terms)
        summary = f"Compared {term_count} terms across {bucket_count} groups using {ref_count} references."

        # Assemble results
        results: Dict[str, Any] = {
            "experiment_type": "domain_comparison",
            "target_terms": target_terms,
            # Backward-compatibility: include 'disciplines' when grouping by disciplines
            "disciplines": sorted(buckets.keys()) if grouping_label == "disciplines" else [],
            # Generic buckets for UI consumption
            "buckets": sorted(buckets.keys()),
            "grouping_label": grouping_label,
            "per_term_data": per_term_data,
            "similarity_matrices": similarity_matrices,
        }

        return results, summary

    def _infer_discipline(self, ref: Document, fallback: str = "journal") -> str:
        meta = ref.source_metadata or {}
        if fallback == "context" and meta.get("context"):
            return str(meta.get("context") or "Context")
        if fallback == "journal" and meta.get("journal"):
            return str(meta.get("journal") or "Journal")
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
