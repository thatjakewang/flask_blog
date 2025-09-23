#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
創建管理員用戶腳本
"""
import os
import sys

# 確保可以導入 app 模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User


def create_admin_user():
    """創建管理員用戶"""
    app = create_app()
    
    with app.app_context():
        # 檢查是否已經有管理員用戶
        admin = User.query.filter_by(email='admin@example.com').first()
        if admin:
            print("管理員用戶已存在")
            return
        
        # 創建管理員用戶
        admin_user = User(
            email='admin@example.com',
            username='admin',
            is_admin=True
        )
        admin_user.set_password('admin123')  # 請修改為安全密碼
        
        db.session.add(admin_user)
        db.session.commit()
        
        print("管理員用戶創建成功！")
        print("Email: admin@example.com")
        print("Password: admin123")
        print("請記得修改密碼！")


if __name__ == '__main__':
    create_admin_user()