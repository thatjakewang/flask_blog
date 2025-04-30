from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy.exc import OperationalError, DatabaseError

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.admin_login'
login_manager.login_message = 'Please log in to access this page'
login_manager.login_message_category = 'info'
login_manager.session_protection = 'strong'

# User loader function
@login_manager.user_loader
def load_user(id):
    from app.models import User
    return User.query.get(int(id))

# Application factory function
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if not app.debug:
        log_handler = RotatingFileHandler('app.log', maxBytes=1000000, backupCount=5)
        log_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        log_handler.setLevel(logging.INFO)
        app.logger.addHandler(log_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')

    try:
        db.init_app(app)
        with app.app_context():
            db.create_all()  # 測試資料庫連線
    except OperationalError as e:
        app.logger.error(f"Database connection failed: {e}")
        raise
 
    # Initialize extensions
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from app.routes import main, auth, dashboard
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)

    @app.context_processor
    def inject_now():
        return {'now': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback() 
        app.logger.error(f"Server Error: {error}")
        return render_template('error/500.html'), 500
    
    @app.errorhandler(DatabaseError)
    def database_error(error):
        app.logger.error(f"Database Error: {error}")
        return render_template('error/500.html'), 500

    return app