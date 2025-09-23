import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

"""
Application Configuration Module

This module contains all configuration settings for the application, including configurations for development, testing, and production environments.
"""

class Config:
    """
    Base Configuration Class
    
    This class defines the basic configuration parameters required by the application. 
    All environment-specific configuration classes inherit from this class.
    """
    # Basic Flask Configuration
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Core Settings
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///blog.db')
    TIMEZONE = os.environ.get('TIMEZONE', 'UTC')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    VERSION = os.environ.get('APP_VERSION', '1.0.0')
    
    # CSRF Configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # Session Configuration
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Security Configuration
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'true').lower() == 'true'
    
    # Category Cache Timeout (10 minutes)
    CATEGORY_CACHE_TIMEOUT = 600
    
    # Flask-Caching Configuration
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300

    # Basic Content Security Policy
    CSP = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "https://www.googletagmanager.com"],
        'style-src': ["'self'"],
        'img-src': ["'self'", "data:"],
        'object-src': ["'none'"],
        'frame-ancestors': ["'none'"]
    }
    
    @classmethod
    def init_app(cls, app):
        """
        初始化應用程式配置
        
        此方法在應用程式建立和配置後呼叫。
        子類別可以覆寫此方法來執行環境特定的初始化。
        
        Args:
            app: Flask 應用程式實例
        """
        # 基礎實作 - 子類別可以擴展此方法
        pass


class DevelopmentConfig(Config):
    """Development Environment Configuration (本地開發環境)"""
    
    DEBUG = True
    DEBUG_TB_ENABLED = False
    # Override SECRET_KEY for development with a secure default
    # Use a fixed key for development to maintain sessions across restarts
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    db_url = os.environ.get('DATABASE_URL')
    # Development database - create instance directory if it doesn't exist
    if db_url:
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
        os.makedirs(instance_dir, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(instance_dir, 'blog.db')
    
    # Relaxed session settings for development
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    FORCE_HTTPS = False  # Disable HTTPS enforcement in development
        
    # Development CSP - more permissive
    CSP = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-eval'", "'unsafe-inline'","https://www.googletagmanager.com","https://www.google-analytics.com"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", "data:", "https:", "blob:"],
        'object-src': ["'none'"],
        'font-src': ["'self'", "data:"],
        'connect-src': ["'self'", "https://www.google-analytics.com"]
    }
    
    @classmethod
    def init_app(cls, app):
        """Initialize development-specific settings"""
        super().init_app(app)
        
        # Enable detailed error pages in development
        app.config['PROPAGATE_EXCEPTIONS'] = True
        
        # Optional Flask-DebugToolbar configuration
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False


class ProductionConfig(Config):
    """Production Environment Configuration (線上生產環境)"""
    
    DEBUG = False
    
    # 正式環境數據庫配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # 臨時修復：如果沒有 HTTPS，允許在 HTTP 下使用 session
    SESSION_COOKIE_SECURE = os.environ.get('HTTPS_ENABLED', 'false').lower() == 'true'
    FORCE_HTTPS = os.environ.get('HTTPS_ENABLED', 'false').lower() == 'true'
        
    def __init__(self):
        super().__init__()
        self.__class__._validate_production_config()
    
    @classmethod
    def _validate_production_config(cls):
        """Validate that all required production settings are present"""
        required_vars = ['SECRET_KEY', 'DATABASE_URL']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables for production: {', '.join(missing_vars)}")
        
        # Validate DATABASE_URL format
        from urllib.parse import urlparse
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise ValueError("DATABASE_URL is required")
        parsed = urlparse(db_url)
        if not parsed.scheme or not parsed.path:
            raise ValueError("Invalid DATABASE_URL format")
        
    # Production CSP
    CSP = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "https://www.googletagmanager.com"],
        'connect-src': ["'self'", "https://www.google-analytics.com"],
        'img-src': ["'self'", "data:"],
        'object-src': ["'none'"],
        'frame-ancestors': ["'none'"]
    }
    
    @classmethod
    def init_app(cls, app):
        """Initialize production-specific settings"""
        super().init_app(app)

        cls._validate_production_config()
        
        # Ensure log directory exists
        log_file = app.config.get('LOG_FILE', 'logs/app.log')
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Add syslog handler for production logging
        import logging
        from logging.handlers import SysLogHandler
        
        try:
            syslog_handler = SysLogHandler(address='/dev/log')
            syslog_handler.setLevel(logging.WARNING)
            formatter = logging.Formatter(
                f'{app.name}: %(levelname)s in %(module)s: %(message)s'
            )
            syslog_handler.setFormatter(formatter)
            app.logger.addHandler(syslog_handler)
        except Exception as e:
            app.logger.warning(f"Could not setup syslog handler: {e}")

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """
    Get configuration class based on environment
    
    Args:
        config_name (str): Configuration name ('development', 'production', etc.)
        
    Returns:
        Config: Configuration class instance
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    config_class = config.get(config_name, config['default'])
    
    # Validate configuration class
    if not issubclass(config_class, Config):
        raise ValueError(f"Invalid configuration class: {config_class}")
    
    return config_class