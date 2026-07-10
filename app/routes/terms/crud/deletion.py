"""Term deletion routes."""

from flask import current_app, flash, redirect, url_for
from flask_login import current_user
from sqlalchemy import text

from app import db
from app.models import Term, TermVersion
from app.services.provenance_service import provenance_service
from app.utils.auth_decorators import write_login_required

from .. import terms_bp


@terms_bp.route('/<uuid:term_id>/delete', methods=['POST'])
@write_login_required
def delete_term(term_id):
    """Delete a term (admin only)"""
    # Check if user is admin
    if not current_user.is_admin:
        flash('You do not have permission to delete terms.', 'error')
        return redirect(url_for('terms.term_index'))

    term = Term.query.get_or_404(term_id)
    term_text = term.term_text

    try:
        # Handle provenance records (purge or invalidate based on settings)
        prov_result = provenance_service.delete_or_invalidate_term_provenance(term_id)
        current_app.logger.info(f"Provenance handling for term {term_id}: {prov_result}")

        from app.models.semantic_drift import SemanticDriftActivity

        # Get all version IDs for this term
        version_ids = [str(v.id) for v in TermVersion.query.filter_by(term_id=term.id).all()]

        if version_ids:
            # Delete all semantic drift activities for this term
            activities_to_delete = SemanticDriftActivity.get_activities_for_term(term.id)
            for activity in activities_to_delete:
                db.session.delete(activity)

            # Delete term_version_anchors junction table entries
            for version_id in version_ids:
                db.session.execute(
                    text("DELETE FROM term_version_anchors WHERE term_version_id = :version_id"),
                    {'version_id': version_id}
                )

            # Update context_anchors to remove references to these versions
            for version_id in version_ids:
                # Set first_used_in to NULL for anchors that reference this version
                db.session.execute(
                    text("UPDATE context_anchors SET first_used_in = NULL WHERE first_used_in = :version_id"),
                    {'version_id': version_id}
                )
                # Set last_used_in to NULL for anchors that reference this version
                db.session.execute(
                    text("UPDATE context_anchors SET last_used_in = NULL WHERE last_used_in = :version_id"),
                    {'version_id': version_id}
                )

            # Now delete all versions
            TermVersion.query.filter_by(term_id=term.id).delete()

        # Now delete the term itself
        db.session.delete(term)
        db.session.commit()

        flash(f'Term "{term_text}" and all its versions have been deleted successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting term {term_id}: {str(e)}")
        flash(f'An error occurred while deleting the term: {str(e)}', 'error')

    return redirect(url_for('terms.term_index'))
