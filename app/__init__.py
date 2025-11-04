from flask import Flask
from sqlalchemy import or_
import click
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager: LoginManager = LoginManager()
cors = CORS()

def create_app(config_name=None):
    """Application factory pattern"""
    
    app = Flask(__name__)
    
    # Configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    from config import config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    
    # Configure login manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        # SQLAlchemy 2.0 style get via session
        return db.session.get(User, int(user_id))
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.text_input import text_input_bp
    from app.routes.processing import processing_bp
    from app.routes.results import results_bp
    from app.routes.experiments import experiments_bp
    from app.routes.references import references_bp
    from app.routes.upload import upload_bp
    from app.routes.terms import terms_bp
    from app.routes.merriam_webster import merriam_bp
    from app.routes.temporal_visual import temporal_visual_bp
    from app.routes.embeddings_api import embeddings_bp, document_api_bp
    from app.routes.api import api_bp
    from app.routes.orchestration_feedback import bp as orchestration_feedback_bp
    from app.routes.provenance_visualization import bp as provenance_bp
    from app.routes.orchestration import orchestration_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(text_input_bp, url_prefix='/input')
    app.register_blueprint(processing_bp, url_prefix='/process')
    app.register_blueprint(results_bp, url_prefix='/results')
    app.register_blueprint(experiments_bp)
    app.register_blueprint(references_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(terms_bp)
    app.register_blueprint(merriam_bp)
    app.register_blueprint(temporal_visual_bp)
    app.register_blueprint(embeddings_bp)
    app.register_blueprint(document_api_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(orchestration_feedback_bp)
    app.register_blueprint(provenance_bp)
    app.register_blueprint(orchestration_bp)

    # Composite documents removed - using inheritance-based versioning
    
    # Jinja filters
    @app.template_filter('number_format')
    def number_format(value):
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            try:
                return f"{float(value):,.0f}"
            except Exception:
                return value

    # Main route - PUBLIC ACCESS
    @app.route('/')
    def index():
        from flask import render_template
        from flask_login import current_user
        
        # Get user's dashboard data (only if authenticated)
        dashboard_data = {
            'recent_term': None,
            'term_counts': {
                'anchor_terms': 0,
                'term_versions': 0,
                'drift_analyses': 0
            }
        }
        
        if current_user.is_authenticated:
            try:
                from app.models.term import Term, TermVersion
                from app.models.semantic_drift import SemanticDriftActivity
                
                # Get most recent term
                dashboard_data['recent_term'] = Term.query.filter_by(created_by=current_user.id).order_by(Term.created_at.desc()).first()
                
                # Get counts
                dashboard_data['term_counts']['anchor_terms'] = Term.query.filter_by(created_by=current_user.id).count()
                dashboard_data['term_counts']['term_versions'] = TermVersion.query.filter_by(created_by=current_user.id).count()
                dashboard_data['term_counts']['drift_analyses'] = SemanticDriftActivity.query.filter_by(created_by=current_user.id).count()
                dashboard_data['term_counts']['total_analyses'] = dashboard_data['term_counts']['term_versions'] + dashboard_data['term_counts']['drift_analyses']
                
            except Exception as e:
                app.logger.debug(f"Could not fetch dashboard data: {e}")
        
        return render_template('index.html', **dashboard_data)
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Register CLI commands
    register_cli(app)
    
    return app


def register_cli(app: Flask) -> None:
    """Register Flask CLI commands."""

    @app.cli.command("init-db")
    def init_db_command():
        """Initialize database tables from models."""
        from app import db as _db
        with app.app_context():
            _db.create_all()
        click.echo("Database initialized.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin_command(username: str, email: str, password: str):
        """Create an admin user."""
        from app import db as _db
        from app.models.user import User
        with app.app_context():
            # Use session-based query to avoid class-level query property
            existing = db.session.query(User).filter(
                or_(getattr(User, "username") == username, getattr(User, "email") == email)
            ).first()
            if existing:
                click.echo("User with that username or email already exists.")
                return
            user = User(username=username, email=email, password=password, is_admin=True)
            _db.session.add(user)
            _db.session.commit()
            click.echo(f"Admin user '{username}' created.")

    @app.cli.command("create-demo-documents")
    def create_demo_documents_command():
        """Create demo documents for anonymous viewing."""
        from app import db as _db
        from app.models.document import Document
        from app.models.user import User
        from datetime import datetime
        
        with app.app_context():
            # Get or create a demo user
            demo_user = User.query.filter_by(username='demo_user').first()
            if not demo_user:
                demo_user = User(
                    username='demo_user',
                    email='demo@example.com',
                    password='demo_password_not_for_login',
                    is_active=False  # Prevent login
                )
                _db.session.add(demo_user)
                _db.session.commit()
                click.echo("Created demo user.")
            
            # Create demo documents if they don't exist
            existing_demos = Document.query.filter(Document.title.like('[DEMO]%')).count()
            if existing_demos > 0:
                click.echo(f"Demo documents already exist ({existing_demos} found).")
                return
            
            demo_docs = [
                {
                    'title': 'Semantic Evolution in Computing Terms',
                    'content': """The term "cloud" in computing has undergone significant semantic drift since the 1960s.
                    Originally used metaphorically in network diagrams to represent undefined network space,
                    it evolved through the 1990s to describe distributed computing resources, and by the 2000s
                    became synonymous with on-demand internet-based services. This evolution demonstrates
                    how technical terminology adapts to technological advancement while maintaining conceptual
                    continuity through metaphorical extension.""",
                    'detected_language': 'en',
                    'language_confidence': 0.99,
                    'status': 'completed'
                },
                {
                    'title': 'Historical Analysis of "Algorithm"',
                    'content': """The word "algorithm" derives from the name of 9th-century mathematician
                    al-Khwarizmi, originally referring to arithmetic procedures. Through the 20th century,
                    it broadened to encompass any systematic procedure for calculation. With the advent
                    of computer science, it specialized to mean precise computational procedures, yet
                    recent usage in phrases like "social media algorithm" shows renewed semantic expansion
                    into non-technical domains, illustrating cyclical patterns in terminological evolution.""",
                    'detected_language': 'en',
                    'language_confidence': 0.98,
                    'status': 'completed'
                },
                {
                    'title': 'PROV-O Tracking Example',
                    'content': """This document demonstrates PROV-O provenance tracking in OntExtract.
                    Each analytical operation creates traceable records following W3C standards.
                    When this document is processed, the system captures: (1) the agent performing
                    the analysis, (2) the activity type and parameters, (3) the resulting entities,
                    and (4) the derivation relationships between versions. This ensures complete
                    reproducibility and transparency in semantic analysis workflows.""",
                    'detected_language': 'en',
                    'language_confidence': 0.97,
                    'status': 'completed'
                }
            ]
            
            for doc_data in demo_docs:
                doc = Document(
                    **doc_data,
                    content_type='text',
                    user_id=demo_user.id,
                    word_count=len(doc_data['content'].split()),
                    character_count=len(doc_data['content']),
                    created_at=datetime.utcnow()
                )
                _db.session.add(doc)
            
            _db.session.commit()
            click.echo(f"Created {len(demo_docs)} demo documents.")
