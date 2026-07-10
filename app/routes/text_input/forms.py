"""Pasted-text and compatibility file-input form routes."""

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.services.base_service import ValidationError
from app.services.document_input_service import DocumentInputService
from app.utils.auth_decorators import write_login_required

from . import text_input_bp


def _success(document, message):
    redirect_url = url_for(
        'text_input.document_detail',
        document_uuid=document.uuid,
    )
    if request.is_json:
        return jsonify({
            'success': True,
            'document_id': document.id,
            'message': message,
            'redirect_url': redirect_url,
        })
    flash(f'{message}!', 'success')
    return redirect(redirect_url)


def _error(message, redirect_endpoint, status=400):
    if request.is_json:
        return jsonify({'error': message}), status
    flash(message, 'error')
    return redirect(url_for(redirect_endpoint))


@text_input_bp.route('/')
@text_input_bp.route('/upload')
@write_login_required
def upload_form():
    return redirect(url_for('upload.unified'))


@text_input_bp.route('/paste')
@write_login_required
def paste_form():
    return render_template('text_input/paste.html')


@text_input_bp.route('/submit_text', methods=['POST'])
@write_login_required
def submit_text():
    try:
        data = request.get_json(silent=True) if request.is_json else request.form
        document = DocumentInputService().create_text(data, current_user.id)
        return _success(document, 'Text submitted successfully')
    except ValidationError as exc:
        return _error(str(exc), 'text_input.paste_form')
    except Exception as exc:
        current_app.logger.error(f'Error submitting text: {exc}', exc_info=True)
        return _error(
            'An error occurred while processing your text',
            'text_input.paste_form',
            500,
        )


@text_input_bp.route('/upload_file', methods=['POST'])
@write_login_required
def upload_file():
    try:
        document = DocumentInputService().create_file(
            request.files.get('file'),
            request.form.get('title', ''),
            current_user.id,
            current_app.config['UPLOAD_FOLDER'],
            current_app.config['ALLOWED_EXTENSIONS'],
        )
        return _success(document, 'File uploaded successfully')
    except ValidationError as exc:
        return _error(str(exc), 'upload.unified')
    except Exception as exc:
        current_app.logger.error(f'Error uploading file: {exc}', exc_info=True)
        return _error(
            'An error occurred while uploading your file',
            'text_input.upload_form',
            500,
        )
