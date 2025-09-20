#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Application Launcher

統一的應用程式啟動器，支持開發和生產環境。
根據環境變數自動選擇適當的配置和啟動方式。

Usage:
    開發環境:
        python app_launcher.py
        或 python app_launcher.py --dev
    
    生產環境 (WSGI):
        gunicorn -w 4 app_launcher:app
        或 uwsgi --module app_launcher:app
    
    檢查配置:
        python app_launcher.py --check-config

Environment Variables:
    - FLASK_ENV: 'development' or 'production' (default: development)
    - FLASK_PORT: Port number for development server (default: 8080)
    - ENV_PATH: Path to .env file (default: .env)
"""
import os
import sys
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# 確保可以導入app模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from config import get_config, DevelopmentConfig, ProductionConfig


def load_environment():
    """載入環境變數"""
    # 首先嘗試載入 .env 檔案
    env_path = os.environ.get('ENV_PATH', '.env')
    env_loaded = False
    
    # 嘗試多個可能的 .env 檔案位置
    possible_env_paths = [
        env_path,
        '.env',
        os.path.join(os.path.dirname(__file__), '.env'),
        '/var/www/flask_blog/.env'
    ]
    
    for path in possible_env_paths:
        if Path(path).exists():
            if load_dotenv(path):
                print(f"✓ Environment loaded from: {path}")
                env_loaded = True
                break
    
    if not env_loaded:
        print("⚠ Warning: .env file not found. Using system environment variables.")
    
    return env_loaded


def setup_logging():
    """設置基本日誌"""
    log_level = logging.INFO if os.environ.get('FLASK_ENV') == 'production' else logging.DEBUG
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def check_config():
    """檢查配置是否正確"""
    print("🔍 Checking application configuration...")
    
    try:
        env = os.environ.get('FLASK_ENV', 'development')
        config_class = get_config(env)
        
        print(f"Environment: {env}")
        print(f"Config class: {config_class.__name__}")
        
        # 嘗試創建應用程式
        try:
            app = create_app(config_class=config_class)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e
        
        with app.app_context():
            print("✓ App created successfully")
            print(f"✓ Debug mode: {app.config.get('DEBUG')}")
            print(f"✓ Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
            print(f"✓ Secret key configured: {'Yes' if app.config.get('SECRET_KEY') else 'No'}")
            
            # 生產環境額外檢查
            if env == 'production':
                required_vars = ['SECRET_KEY', 'DATABASE_URL']
                missing = [var for var in required_vars if not os.environ.get(var)]
                if missing:
                    print(f"❌ Missing required environment variables: {', '.join(missing)}")
                    return False
                else:
                    print("✓ All required production variables present")
        
        print("✅ Configuration check passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration check failed: {e}")
        return False


def create_production_app():
    """創建生產環境應用程式實例"""
    try:
        load_environment()
        setup_logging()
        
        app = create_app(config_class=ProductionConfig)
        logging.info("Production WSGI application initialized successfully")
        return app
        
    except Exception as e:
        logging.error(f"Failed to create production app: {e}")
        raise


def run_development_server():
    """運行開發伺服器"""
    try:
        load_environment()
        setup_logging()
        
        app = create_app(config_class=DevelopmentConfig)
        
        # 開發伺服器配置
        host = os.environ.get('FLASK_HOST', '0.0.0.0')
        port = int(os.environ.get('FLASK_PORT', 8080))
        debug = os.environ.get('FLASK_ENV', 'development') == 'development'
        
        print(f"🚀 Starting development server on http://{host}:{port}")
        print(f"📝 Debug mode: {debug}")
        print(f"🔧 Environment: {os.environ.get('FLASK_ENV', 'development')}")
        
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,
            threaded=True
        )
        
    except Exception as e:
        logging.error(f"Failed to start development server: {e}")
        sys.exit(1)


def main():
    """主函數，處理命令行參數"""
    parser = argparse.ArgumentParser(description='Flask Application Launcher')
    parser.add_argument('--dev', action='store_true', help='Force development mode')
    parser.add_argument('--prod', action='store_true', help='Force production mode')
    parser.add_argument('--check-config', action='store_true', help='Check configuration and exit')
    
    args = parser.parse_args()
    
    # 檢查配置模式
    if args.check_config:
        success = check_config()
        sys.exit(0 if success else 1)
    
    # 決定運行模式
    if args.dev:
        os.environ['FLASK_ENV'] = 'development'
    elif args.prod:
        os.environ['FLASK_ENV'] = 'production'
    
    env = os.environ.get('FLASK_ENV', 'development')
    
    if env == 'development':
        run_development_server()
    else:
        print("⚠ Production mode detected. Use WSGI server instead:")
        print("  gunicorn -w 4 app_launcher:app")
        print("  or uwsgi --module app_launcher:app")
        sys.exit(1)


# ========================================
# WSGI Application Instance
# ========================================

# 為WSGI伺服器提供應用程式實例
# 這個變數會被 Gunicorn, uWSGI 等 WSGI 伺服器使用
try:
    if os.environ.get('FLASK_ENV') == 'production' or 'gunicorn' in os.environ.get('SERVER_SOFTWARE', ''):
        app = create_production_app()
    else:
        # 開發環境或測試環境
        load_environment()
        app = create_app(config_name='development')
except Exception as e:
    logging.error(f"Failed to create WSGI app instance: {e}")
    # 創建一個最小的錯誤應用程式
    from flask import Flask
    app = Flask(__name__)
    
    error_message = str(e)

    @app.route('/')
    def error():
        return f"Application initialization failed: {error_message}", 500


# ========================================
# Entry Point
# ========================================

if __name__ == '__main__':
    main()