from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
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
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.text_input import text_input_bp
    from app.routes.processing import processing_bp
    from app.routes.results import results_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(text_input_bp, url_prefix='/input')
    app.register_blueprint(processing_bp, url_prefix='/process')
    app.register_blueprint(results_bp, url_prefix='/results')
    
    # Main route
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    return app
