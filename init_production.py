#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正式環境初始化腳本
"""
import os
import sys

# 確保可以導入 app 模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def init_production():
    """初始化正式環境"""
    print("=== 初始化正式環境 ===")
    
    # 設定環境變數
    os.environ['FLASK_ENV'] = 'production'
    os.environ['HTTPS_ENABLED'] = 'false'
    
    # 如果沒有設定 DATABASE_URL，使用預設路徑
    if not os.environ.get('DATABASE_URL'):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'production.db')
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        print(f"使用預設數據庫路徑: {db_path}")
    
    # 如果沒有設定 SECRET_KEY，使用預設值
    if not os.environ.get('SECRET_KEY'):
        os.environ['SECRET_KEY'] = '5633a432b80c51cb7fbd54ff474bda18377e9da8c23174e2'
        print("使用預設 SECRET_KEY")
    
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL')}")
    
    try:
        from app import create_app, db
        from app.models import User
        
        app = create_app()
        
        with app.app_context():
            print(f"數據庫: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            # 創建數據庫表
            db.create_all()
            print("✅ 數據庫表已創建/更新")
            
            # 檢查或創建管理員用戶
            admin_email = 'thatjakewang@gmail.com'
            admin_user = User.query.filter_by(email=admin_email).first()
            
            if not admin_user:
                admin_user = User(
                    email=admin_email,
                    username='jake',
                    is_admin=True
                )
                admin_user.set_password('jake123')
                db.session.add(admin_user)
                db.session.commit()
                print("✅ 管理員用戶已創建")
            else:
                print("✅ 管理員用戶已存在")
            
            print("\n🎉 正式環境初始化完成！")
            print("現在可以啟動應用: python app_launcher.py")
            return True
            
    except Exception as e:
        print(f"❌ 初始化失敗: {e}")
        return False

if __name__ == '__main__':
    init_production()