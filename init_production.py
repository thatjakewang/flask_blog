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
    
    # 檢查必要的環境變數
    required_vars = ['SECRET_KEY', 'DATABASE_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ 缺少必要的環境變數:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n請設定以下環境變數:")
        print("export SECRET_KEY='your-secret-key'")
        print("export DATABASE_URL='sqlite:///instance/production.db'")
        print("export HTTPS_ENABLED='false'")
        return False
    
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