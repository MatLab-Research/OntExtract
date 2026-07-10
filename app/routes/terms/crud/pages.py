"""Term index and detail pages."""

from flask import render_template, request

from app import db
from app.models import Term

from .. import terms_bp


@terms_bp.route('/')
def term_index():
    """Display alphabetical index of all terms - public view"""
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Search functionality
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    domain_filter = request.args.get('domain', '')

    # Base query
    query = Term.query

    # Apply filters
    if search_query:
        query = query.filter(Term.term_text.ilike(f'%{search_query}%'))

    if status_filter:
        query = query.filter(Term.status == status_filter)

    if domain_filter:
        query = query.filter(Term.research_domain == domain_filter)

    # Order alphabetically
    query = query.order_by(Term.term_text)

    # Paginate
    terms = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get available domains for filter dropdown
    domains = db.session.query(Term.research_domain).distinct().filter(
        Term.research_domain.isnot(None)
    ).all()
    domains = [d[0] for d in domains]

    return render_template('terms/index.html',
                         terms=terms,
                         search_query=search_query,
                         status_filter=status_filter,
                         domain_filter=domain_filter,
                         domains=domains)
@terms_bp.route('/<uuid:term_id>')
def view_term(term_id):
    """View term details and all versions"""
    term = Term.query.get_or_404(term_id)

    # Get all versions ordered by temporal period
    versions = term.get_all_versions_ordered()

    # Get semantic drift activities
    drift_activities = term.get_semantic_drift_activities()

    return render_template('terms/view.html',
                         term=term,
                         versions=versions,
                         drift_activities=drift_activities)
