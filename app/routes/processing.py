from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

processing_bp = Blueprint('processing', __name__)

@processing_bp.route('/')
@login_required
def processing_home():
    """Processing pipeline home page"""
    return render_template('processing/index.html')

@processing_bp.route('/jobs')
@login_required
def job_list():
    """List processing jobs"""
    # Placeholder for now
    return render_template('processing/jobs.html')

@processing_bp.route('/start/<int:document_id>')
@login_required
def start_processing(document_id):
    """Start processing a document"""
    # Placeholder for now
    return jsonify({'message': 'Processing will be implemented in phase 2'})
