from flask import Blueprint, render_template

linked_data_bp = Blueprint('linked_data', __name__)

@linked_data_bp.route('/')
def index():
    """Linked Data placeholder page"""
    return render_template('linked_data/index.html')
