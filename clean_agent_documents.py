#!/usr/bin/env python3
"""
Clean Agent Experiment Documents with LLM
Programmatically clean all documents for the Agent experiment
"""

import sys
sys.path.insert(0, '/home/chris/OntExtract')

from app import create_app, db
from app.models import Document, Experiment, ProcessingJob
from app.services.text_cleanup_service import TextCleanupService
from app.services.inheritance_versioning_service import InheritanceVersioningService
from datetime import datetime

def clean_documents():
    """Clean all documents in the Agent experiment"""
    app = create_app()

    with app.app_context():
        # Get the experiment
        experiment = Experiment.query.filter_by(id=32).first()

        if not experiment:
            print("❌ Experiment 32 not found")
            return

        print(f"📊 Experiment: {experiment.name}")

        # Get documents list
        exp_docs = experiment.documents.all() if hasattr(experiment.documents, 'all') else list(experiment.documents)

        print(f"📄 Documents: {len(exp_docs)}")
        print("=" * 80)

        cleanup_service = TextCleanupService()
        versioning_service = InheritanceVersioningService()

        cleaned_count = 0

        for document in exp_docs:
            # exp_docs contains Document objects directly

            print(f"\n📄 Processing: {document.title}")
            print(f"   UUID: {document.uuid}")
            print(f"   Content length: {len(document.content) if document.content else 0} chars")

            if not document.content:
                print("   ⚠️  Skipping - no content")
                continue

            try:
                # Check if already cleaned
                existing_cleaned = Document.query.filter_by(
                    parent_document_id=document.id,
                    version_type='processed'
                ).first()

                if existing_cleaned:
                    print(f"   ℹ️  Already has cleaned version (ID: {existing_cleaned.id})")
                    continue

                print("   🧹 Cleaning with Claude Sonnet 4.5...")

                # Clean the text
                cleaned_text, metadata = cleanup_service.clean_text(
                    document.content,
                    progress_callback=lambda curr, total: print(f"      Progress: {curr}/{total} chunks")
                )

                print(f"   ✅ Cleaned: {len(cleaned_text)} chars")
                print(f"   📊 Metadata: {metadata.get('changes_made', 0)} changes, "
                      f"{metadata.get('total_tokens', 0)} tokens, "
                      f"{metadata.get('processing_time', 0):.1f}s")

                # Create cleaned version manually
                cleaned_version = Document(
                    title=document.title,
                    content=cleaned_text,
                    content_type='file',
                    file_type=document.file_type,
                    document_type='document',
                    user_id=document.user_id,
                    version_type='processed',
                    version_number=2,
                    parent_document_id=document.id,
                    created_at=datetime.utcnow(),
                    original_filename=document.original_filename,
                    # Copy metadata from parent
                    source_metadata=document.source_metadata if document.source_metadata else None
                )
                db.session.add(cleaned_version)
                db.session.flush()  # Get the ID

                # Copy temporal metadata from parent
                from app.models import DocumentTemporalMetadata
                parent_temporal = DocumentTemporalMetadata.query.filter_by(
                    document_id=document.id
                ).first()

                if parent_temporal:
                    child_temporal = DocumentTemporalMetadata(
                        document_id=cleaned_version.id,
                        publication_year=parent_temporal.publication_year,
                        discipline=parent_temporal.discipline,
                        key_definition=parent_temporal.key_definition,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(child_temporal)
                    print(f"   ✅ Copied temporal metadata: {parent_temporal.publication_year} - {parent_temporal.discipline}")

                # Create processing job record
                job = ProcessingJob(
                    document_id=cleaned_version.id,
                    job_type='clean_text',
                    status='completed',
                    user_id=document.user_id,
                    model=metadata.get('model', 'claude-sonnet-4-5'),
                    provider=metadata.get('provider', 'claude'),
                    tokens_used=metadata.get('total_tokens', 0),
                    processing_time=metadata.get('processing_time', 0),
                    created_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
                job.set_parameters({
                    'original_length': len(document.content),
                    'cleaned_length': len(cleaned_text),
                    'changes_made': metadata.get('changes_made', 0)
                })
                job.set_result_data({
                    'original_text': document.content[:1000],  # First 1000 chars for reference
                    'cleaned_text': cleaned_text[:1000],
                    'metadata': metadata
                })

                db.session.add(job)
                db.session.commit()

                print(f"   ✅ Created cleaned version: {cleaned_version.uuid}")
                cleaned_count += 1

            except Exception as e:
                print(f"   ❌ ERROR: {str(e)}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
                continue

        print("\n" + "=" * 80)
        print(f"✅ Cleaned {cleaned_count}/{len(exp_docs)} documents")
        print("=" * 80)
        print("\n🎯 Next Steps:")
        print("1. Navigate to: http://localhost:8765/experiments/32")
        print("2. Click 'Run Orchestration' to start the 5-stage LLM workflow")
        print("=" * 80)

if __name__ == '__main__':
    clean_documents()
