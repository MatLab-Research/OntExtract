"""Document listing and detail pages."""

from flask import render_template, request

from app.models.document import Document
from app.utils.auth_decorators import public_with_auth_context

from .. import text_input_bp


@text_input_bp.route('/documents')
@public_with_auth_context
def document_list():
    """List all sources (documents and references) with optional type filtering - public access"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    source_type = request.args.get('type', 'all')  # all, document, reference

    # Build query with optional type filter
    query = Document.query
    if source_type == 'document':
        query = query.filter_by(document_type='document')
    elif source_type == 'reference':
        query = query.filter_by(document_type='reference')
    # 'all' shows everything

    # Get documents ordered by creation date (newest first)
    all_documents = query.order_by(Document.created_at.desc()).all()

    # Group documents by base document
    document_groups = {}
    for doc in all_documents:
        # Determine the base document ID
        base_id = doc.source_document_id or doc.id

        if base_id not in document_groups:
            document_groups[base_id] = {
                'base_document': None,
                'versions': [],
                'latest_created': None
            }

        # Set the base document (original version)
        if doc.version_type == 'original':
            document_groups[base_id]['base_document'] = doc

        # Add to versions list
        document_groups[base_id]['versions'].append(doc)

        # Track latest creation date for sorting groups
        if document_groups[base_id]['latest_created'] is None or doc.created_at > document_groups[base_id]['latest_created']:
            document_groups[base_id]['latest_created'] = doc.created_at

    # Sort versions within each group (latest first)
    for group in document_groups.values():
        group['versions'].sort(key=lambda x: x.version_number, reverse=True)
        # If no base document was found, use the original version
        if group['base_document'] is None and group['versions']:
            group['base_document'] = min(group['versions'], key=lambda x: x.version_number)
        # Set latest_version to the first (newest) version
        if group['versions']:
            group['latest_version'] = group['versions'][0]

    # Convert to list and sort by latest creation date
    grouped_documents = list(document_groups.values())
    grouped_documents.sort(key=lambda x: x['latest_created'], reverse=True)

    # Implement pagination on groups
    start = (page - 1) * per_page
    end = start + per_page
    paginated_groups = grouped_documents[start:end]

    # Create pagination object
    total_groups = len(grouped_documents)
    has_prev = page > 1
    has_next = end < total_groups

    total_pages = (total_groups + per_page - 1) // per_page

    pagination = type('Pagination', (), {
        'items': paginated_groups,
        'page': page,
        'pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_num': page - 1 if has_prev else None,
        'next_num': page + 1 if has_next else None,
        'iter_pages': lambda *args: range(1, total_pages + 1)
    })()

    return render_template('text_input/document_list.html', documents=pagination, source_type=source_type)


@text_input_bp.route('/document/<uuid:document_uuid>')
@public_with_auth_context
def document_detail(document_uuid):
    """Show document details - simplified experiment-centric view"""
    # Get document - public access for viewing
    document = Document.query.filter_by(uuid=document_uuid).first_or_404()

    # Get version family (all versions of this document)
    version_family = document.get_all_versions()

    # Get temporal metadata for display
    from app.models import DocumentTemporalMetadata
    temporal_metadata = DocumentTemporalMetadata.query.filter_by(
        document_id=document.id
    ).first()

    # Get experiments that include this document with their processing results
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import DocumentProcessingIndex
    from app.models.processing_artifact_group import ProcessingArtifactGroup

    # Get ProcessingArtifactGroup count for this document (includes LLM orchestration results)
    artifact_group_count = ProcessingArtifactGroup.query.filter_by(document_id=document.id).count()

    # Get all experiment-document relationships for THIS VERSION
    this_version_experiments = ExperimentDocument.query.filter_by(document_id=document.id).all()

    # Get all experiment-document relationships for ALL VERSIONS in family
    all_version_doc_ids = [v.id for v in version_family]
    all_version_experiments = ExperimentDocument.query.filter(
        ExperimentDocument.document_id.in_(all_version_doc_ids)
    ).all()

    # Enrich with processing information - THIS VERSION
    document_experiments = []
    total_processing_count = 0

    for exp_doc in this_version_experiments:
        # Get processing operations for this experiment-document pair
        processing_results = DocumentProcessingIndex.query.filter_by(
            document_id=document.id,
            experiment_id=exp_doc.experiment_id
        ).all()

        # Create a data structure for the template
        exp_data = {
            'experiment': exp_doc.experiment,
            'document_version': document.version_number,
            'is_current_version': True,
            'processing_results': [
                {
                    'processing_type': proc.processing_type,
                    'processing_method': proc.processing_method,
                    'status': proc.status
                }
                for proc in processing_results
            ]
        }
        document_experiments.append(exp_data)
        total_processing_count += len(processing_results)

    # Add ProcessingArtifactGroup count (LLM orchestration results)
    total_processing_count += artifact_group_count

    # Enrich with processing information - ALL VERSIONS
    all_experiments = []
    for exp_doc in all_version_experiments:
        # Find which version this is
        version_doc = next((v for v in version_family if v.id == exp_doc.document_id), None)

        # Get processing operations
        processing_results = DocumentProcessingIndex.query.filter_by(
            document_id=exp_doc.document_id,
            experiment_id=exp_doc.experiment_id
        ).all()

        exp_data = {
            'experiment': exp_doc.experiment,
            'document_version': version_doc.version_number if version_doc else 0,
            'version_type': version_doc.version_type if version_doc else 'unknown',
            'is_current_version': exp_doc.document_id == document.id,
            'processing_results': [
                {
                    'processing_type': proc.processing_type,
                    'processing_method': proc.processing_method,
                    'status': proc.status
                }
                for proc in processing_results
            ]
        }
        all_experiments.append(exp_data)

    return render_template('text_input/document_detail_simplified.html',
                         document=document,
                         version_family=version_family,
                         temporal_metadata=temporal_metadata,
                         is_latest_version=document.is_latest_version(),
                         this_version_experiments=document_experiments,
                         all_version_experiments=all_experiments,
                         total_processing_count=total_processing_count)
