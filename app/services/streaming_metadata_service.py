"""Server-sent event coordination for upload metadata extraction."""

import json
import queue
import threading

from app.services.base_service import ValidationError
from app.services.upload_metadata_workflow import UploadMetadataWorkflow


class StreamingMetadataService:
    """Save an upload temporarily and stream metadata extraction progress."""

    def __init__(
        self,
        upload_service,
        workflow_logger,
        workflow_factory=UploadMetadataWorkflow,
        heartbeat_seconds=1.0,
        join_timeout=30,
    ):
        self.upload_service = upload_service
        self.workflow_logger = workflow_logger
        self.workflow_factory = workflow_factory
        self.heartbeat_seconds = heartbeat_seconds
        self.join_timeout = join_timeout

    def create_stream(self, file, title, enable_crossref, app):
        if not file or not file.filename:
            raise ValidationError('No file uploaded')
        upload_result = self.upload_service.save_to_temp(file)
        if not upload_result.success:
            raise ValidationError(upload_result.error or 'Failed to save upload')
        return self._generate(
            upload_result.temp_path,
            upload_result.filename,
            title,
            enable_crossref,
            app,
        )

    def _generate(self, temp_path, filename, title, enable_crossref, app):
        messages = queue.Queue()
        abandoned = threading.Event()
        ownership_transferred = False

        def report(message):
            messages.put({'type': 'progress', 'message': message})

        def worker():
            try:
                with app.app_context():
                    if enable_crossref:
                        result = self.upload_service.extract_metadata_from_pdf_streaming(
                            temp_path,
                            progress_callback=report,
                        )
                    else:
                        result = {
                            'success': True,
                            'metadata': {},
                            'source': 'user',
                            'progress': [],
                        }
                    workflow = self.workflow_factory(
                        self.upload_service,
                        self.workflow_logger,
                    )
                    payload = workflow.build_streaming_payload(
                        result,
                        temp_path,
                        filename,
                        title,
                        enable_crossref,
                    )
                if abandoned.is_set():
                    self.upload_service.cleanup_temp(temp_path)
                    return
                messages.put({'type': 'complete', 'data': payload})
            except Exception as exc:
                self.upload_service.cleanup_temp(temp_path)
                messages.put({'type': 'error', 'message': str(exc)})

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        try:
            while True:
                try:
                    message = messages.get(timeout=self.heartbeat_seconds)
                except queue.Empty:
                    yield self._event({'type': 'heartbeat'})
                    continue
                if message['type'] == 'progress':
                    yield self._event(message)
                    continue
                if message['type'] == 'complete':
                    ownership_transferred = True
                    yield self._event(message)
                    break
                yield self._event(message)
                break
        finally:
            abandoned.set()
            thread.join(timeout=self.join_timeout)
            if not ownership_transferred:
                self.upload_service.cleanup_temp(temp_path)

    @staticmethod
    def _event(payload):
        return f'data: {json.dumps(payload)}\n\n'
