from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
from datetime import datetime

# 初始化資料庫
db = SQLAlchemy()
migrate = Migrate()

login_manager = LoginManager()
login_manager.login_view = 'auth.admin_login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class) 

    login_manager.init_app(app)
    
    db.init_app(app)
    migrate.init_app(app, db) 
    
    from app.routes import main, auth, dashboard
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)

    # 添加全局上下文處理器
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    return app

@login_manager.user_loader
def load_user(id):
    from app.models import User
    return User.query.get(int(id))