import os
import secrets
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import pytz

from flask import Flask, g, request, redirect, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_caching import Cache

from config import get_config
from sqlalchemy.exc import SQLAlchemyError

# 初始化擴充套件
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
cache = Cache() 
csrf = None

# 配置登入管理器
login_manager.login_view = 'auth.admin_login'

@login_manager.user_loader
def load_user(user_id: str) -> 'User':
    """為 Flask-Login 載入使用者"""
    from app.models import User
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None


def init_csrf(app: 'Flask') -> None:
    """如果 Flask-WTF 可用，初始化 CSRF 保護"""
    global csrf
    
    if not app.config.get('WTF_CSRF_ENABLED', True):
        return
    
    try:
        from flask_wtf.csrf import CSRFProtect
        csrf = CSRFProtect(app)
        app.logger.info('CSRF protection enabled')
    except ImportError:
        app.logger.warning('Flask-WTF not installed, CSRF protection disabled')


def configure_logging(app: 'Flask') -> None:
    """根據環境配置應用程式日誌"""
    if app.debug:
        # 開發環境日誌 - 控制台輸出
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.DEBUG)
        app.logger.info('Development logging configured')
    else:
        # 生產環境日誌 - 檔案輸出與輪替
        log_file = app.config.get('LOG_FILE', 'logs/app.log')
        
        # 確保日誌目錄存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except OSError as e:
                app.logger.error(f"Failed to create log directory {log_dir}: {e}. "
                         f"Please check file system permissions, ensure the directory path is valid, "
                         f"and verify write access for the application user. Falling back to 'app.log'.")
                # 回退到當前目錄
                log_file = 'app.log'
        
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Production logging configured')


def register_blueprints(app: 'Flask') -> None:
    """註冊所有應用程式藍圖"""
    # 註冊公開路由 (main, auth, sitemap)
    from app.routes.public import register_public_blueprints
    register_public_blueprints(app)
    
    # 註冊管理後台路由
    from app.routes.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)
    
    app.logger.info('All blueprints registered successfully')


def setup_security_headers(app: 'Flask') -> None:
    """配置安全相關的請求處理器"""
    
    @app.before_request
    def before_request():
        """在每個請求之前生成 nonce 並執行安全檢查"""
        # 生成 CSP nonce
        g.csp_nonce = secrets.token_urlsafe(16)
        # 在生產環境中強制使用 HTTPS（僅在正確的反向代理器後面）
        # 注意：當 app.debug 為 True 時會跳過此檢查，以避免干擾本地 HTTP 測試
        if not app.debug and not app.testing and app.config.get('FORCE_HTTPS', True):
            # 檢查請求是否為安全連線或透過 HTTPS 轉發
            if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
                if request.method == 'GET':
                    return redirect(request.url.replace('http://', 'https://'), code=301)
    
    @app.after_request
    def set_security_headers(response):
        """為所有回應新增全面的安全標頭"""
        # 基本安全標頭
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # HSTS 標頭（僅在生產環境）
        if not app.debug and app.config.get('FORCE_HTTPS', True):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # 簡單的內容安全政策
        csp_config = app.config.get('CSP')
        if csp_config:
            csp_parts = []
            for directive, values in csp_config.items():
                if values:
                    csp_parts.append(f"{directive} {' '.join(values)}")
                else:
                    csp_parts.append(directive)
            response.headers['Content-Security-Policy'] = '; '.join(csp_parts)
        
        return response


def register_error_handlers(app: 'Flask') -> None:
    """為應用程式註冊錯誤處理器"""
    
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """處理 403 禁止存取錯誤"""
        app.logger.warning(f"Forbidden access attempt from {request.remote_addr}: {request.url}")
        return render_template('error/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        """處理 404 找不到頁面錯誤"""
        app.logger.info(f"Page not found: {request.url}")
        return render_template('error/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """處理 500 伺服器內部錯誤"""
        db.session.rollback()
        app.logger.error(f"Server Error: {error}")
        return render_template('error/500.html'), 500
    
    
def register_context_processors(app: 'Flask') -> None:
    """Register template context processors
    
    Note: 'csrf_enabled' is injected into templates to check CSRF status.
    Example usage in Jinja: {% if csrf_enabled %}<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">{% endif %}
    This helps avoid errors when CSRF is disabled or not installed.
    """
    
    @app.context_processor
    def inject_template_vars():
        """Inject common variables into template context"""
        from app.models import Post 
        tz = pytz.timezone(app.config.get('TIMEZONE', 'UTC'))
        return {
            'now': datetime.now(tz),
            'csp_nonce': getattr(g, 'csp_nonce', ''),
            'app_version': app.config.get('VERSION', '1.0.0'),
            'debug_mode': app.debug,
            'csrf_enabled': csrf is not None,
            'Post': Post,
        }


def create_app(config_name: str = None, config_class = None) -> 'Flask':
    """
    Application factory function
    
    Args:
        config_name (str): Configuration environment name
        config_class: Configuration class (overrides config_name if provided)
        
    Returns:
        Flask: Configured Flask application instance
    """
    import time
    app = Flask(__name__)
    app.config['_app_start_time'] = time.time()

    
    # Load configuration
    if config_class:
        app.config.from_object(config_class)
    else:
        config_class = get_config(config_name)
        app.config.from_object(config_class)
    
    # Initialize configuration
    config_class.init_app(app)
    
    # Initialize core extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cache.init_app(app)
    init_csrf(app)

    # Configure application components
    configure_logging(app)
    register_blueprints(app)
    setup_security_headers(app)
    register_error_handlers(app)
    register_context_processors(app)

    
    # Development-specific setup
    if app.debug:
        app.logger.info('Application started in development mode')
        
        # Optional: Enable Flask-DebugToolbar in development
        try:
            from flask_debugtoolbar import DebugToolbarExtension
            if app.config.get('DEBUG_TB_INTERCEPT_REDIRECTS') is not False:
                app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
            DebugToolbarExtension(app)
            app.logger.info('Debug toolbar enabled. Ensure SECRET_KEY is set and app.debug=True for toolbar to appear.')
        except ImportError:
            app.logger.info('Flask-DebugToolbar not available')
    
    app.logger.info(f'Application created with {config_name or "default"} configuration')
    return app


def create_tables(app: 'Flask') -> None:
    """
    Create database tables
    
    This is a utility function for initializing the database.
    WARNING: Suitable only for development or one-time initialization.
    Do not use frequently in production; instead, use Flask-Migrate 
    (e.g., flask db init/migrate/upgrade) to manage schema changes safely 
    and avoid data loss or inconsistencies.
    
    Args:
        app: Flask application instance
    """
    with app.app_context():
        try:
            db.create_all()
            app.logger.info('Database tables created successfully')
        except Exception as e:
            app.logger.error(f'Error creating database tables: {e}')
            raise