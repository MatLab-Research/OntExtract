"""Document version selection for segmentation workflows."""

from app.services.inheritance_versioning_service import InheritanceVersioningService


def get_segmentation_version(
    original_document,
    experiment_id,
    user,
    method,
    chunk_size,
    overlap,
    logger,
):
    """Get the experiment version or create a manual processing version."""
    processing_metadata = {
        'segmentation_method': method,
        'chunk_size': chunk_size,
        'overlap': overlap,
        'experiment_id': experiment_id,
        'processing_notes': f'Document segmentation using {method} method'
    }

    if experiment_id:
        processing_version, version_created = (
            InheritanceVersioningService.get_or_create_experiment_version(
                original_document=original_document,
                experiment_id=experiment_id,
                user=user
            )
        )
        logger.info(
            f"Using experiment version {processing_version.id} for experiment "
            f"{experiment_id} "
            f"({'newly created' if version_created else 'existing'})"
        )
        return processing_version

    processing_version = InheritanceVersioningService.create_new_version(
        original_document=original_document,
        processing_type='segmentation',
        processing_metadata=processing_metadata
    )
    logger.info(
        f"Created processed version {processing_version.id} for manual segmentation"
    )
    return processing_version
