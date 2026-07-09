"""Quick reference creation routes."""

from datetime import datetime

from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from app import db
from app.models.document import Document
from app.models.experiment import Experiment

from . import upload_bp


@upload_bp.route('/create_reference', methods=['POST'])
@login_required
def create_reference():
    """
    Create a reference document from dictionary definition
    Quick add feature for experiment creation
    """
    try:
        data = request.get_json()

        title = data.get('title')
        content = data.get('content')
        source = data.get('source')  # MW or OED
        source_type = data.get('source_type', 'dictionary')
        experiment_id = data.get('experiment_id')
        include_in_analysis = data.get('include_in_analysis', False)

        # Additional metadata from the source
        entry_url = data.get('entry_url')
        term = data.get('term')  # The term being defined

        if not title or not content:
            return jsonify({'success': False, 'error': 'Title and content are required'}), 400

        # Build source metadata and auto-fill bibliographic fields based on source
        source_metadata = {
            'source_type': source_type,
            'term': term,
            'entry_url': entry_url,
            'access_date': datetime.utcnow().strftime('%Y-%m-%d')
        }

        # Auto-fill publisher and metadata based on source
        publisher = None
        if source == 'MW':
            publisher = 'Merriam-Webster, Incorporated'
            source_metadata.update({
                'publisher': publisher,
                'publisher_location': 'Springfield, MA',
                'dictionary_name': 'Merriam-Webster Dictionary',
                'citation': f'"{term}." Merriam-Webster.com Dictionary, Merriam-Webster. Accessed {datetime.utcnow().strftime("%d %b %Y")}.'
            })
        elif source == 'OED':
            publisher = 'Oxford University Press'
            source_metadata.update({
                'publisher': publisher,
                'publisher_location': 'Oxford, UK',
                'dictionary_name': 'Oxford English Dictionary',
                'citation': f'"{term}." Oxford English Dictionary, Oxford University Press. Accessed {datetime.utcnow().strftime("%d %b %Y")}.'
            })

        # Create reference document with auto-filled metadata
        document = Document(
            title=title,
            content=content,
            document_type='reference',
            source=source,
            publisher=publisher,
            source_metadata=source_metadata,
            access_date=datetime.utcnow().date(),
            user_id=current_user.id,
            content_type='text/plain',
            word_count=len(content.split()),
            created_at=datetime.utcnow()
        )

        db.session.add(document)
        db.session.commit()

        # Get experiment if provided
        experiment = None
        if experiment_id:
            experiment = Experiment.query.get(experiment_id)
            if experiment and experiment.user_id == current_user.id:
                experiment.add_reference(document, include_in_analysis=include_in_analysis)

        # Create provenance record for the reference creation
        try:
            from app.services.provenance_service import ProvenanceService
            ProvenanceService.track_reference_creation(
                document=document,
                user=current_user,
                source=source,
                experiment=experiment,
                source_metadata=source_metadata
            )
        except Exception as prov_error:
            current_app.logger.warning(f"Failed to create provenance for reference: {prov_error}")
            # Don't fail the whole request if provenance fails

        return jsonify({
            'success': True,
            'document_id': document.id,
            'document_uuid': str(document.uuid),
            'metadata_filled': bool(publisher)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating reference: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
