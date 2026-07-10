"""PROV-O graph visualization pages."""

from flask import render_template, request

from app.models.experiment import Experiment

from . import bp


@bp.route('/graph')
def provenance_graph():
    """
    Display the PROV-O provenance graph visualization.

    Supports optional entity filters via query parameters:
    - experiment_id: Filter by experiment
    - document_id: Filter by document (includes all versions)
    - term_id: Filter by term UUID

    Examples:
    - /provenance/graph?document_id=123
    - /provenance/graph?experiment_id=83
    - /provenance/graph?term_id=uuid-string
    """
    # Get filter parameters to pass to template
    experiment_id = request.args.get('experiment_id', type=int)
    document_id = request.args.get('document_id', type=int)
    term_id = request.args.get('term_id')

    # Get entity names for display
    filter_context = {}
    if document_id:
        from app.models.document import Document
        doc = Document.query.get(document_id)
        if doc:
            filter_context['document'] = doc.title or f"Document {doc.id}"
            filter_context['document_id'] = document_id
            filter_context['document_uuid'] = str(doc.uuid)

    if experiment_id:
        exp = Experiment.query.get(experiment_id)
        if exp:
            filter_context['experiment'] = exp.name
            filter_context['experiment_id'] = experiment_id

    if term_id:
        from app.models.term import Term
        from uuid import UUID
        try:
            term = Term.query.get(UUID(term_id))
            if term:
                filter_context['term'] = term.term_text
                filter_context['term_id'] = term_id
        except (ValueError, TypeError):
            pass

    return render_template(
        'provenance_graph.html',
        filter_context=filter_context,
        experiment_id=experiment_id,
        document_id=document_id,
        term_id=term_id
    )

@bp.route('/graph/compact')
def provenance_graph_compact():
    """Display the compact PROV-O provenance graph for papers."""
    return render_template('provenance_graph_compact.html')

@bp.route('/graph/simple')
def provenance_graph_simple():
    """Display the simple PROV-O provenance graph with manual layout."""
    return render_template('provenance_graph_simple.html')
