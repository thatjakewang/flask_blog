# -*- coding: utf-8 -*-
"""
Database Models Module

This module contains all database models for the Flask blog application.
All models are consolidated in this single file for better maintainability.
"""
from app import db, cache
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timezone
from sqlalchemy import event, func
import pytz
from flask import current_app, Flask
from app.utils import clean_html_content


# ========================================
# User Model
# ========================================

class User(UserMixin, db.Model):
    """
    User model for authentication and access control
    
    This model represents application users with authentication capabilities.
    It stores user credentials and provides methods for secure password handling.
    The UserMixin provides the implementation of Flask-Login properties and methods
    required for the authentication system.
    """

    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # 修復：使用 back_populates 保持一致性
    posts = db.relationship('Post', back_populates='author', lazy='dynamic',
                          cascade='all, delete-orphan')

    def set_password(self, password: str) -> None:
        """
        Set the user's password by generating a secure hash
        
        This method securely stores the password by generating a hash
        using Werkzeug's security functions. The original password is never stored.
        
        Args:
            password (str): The plaintext password to hash and store
        """
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash
        
        This method checks if the provided password matches the stored hash
        without ever decrypting or exposing the actual password.
        
        Args:
            password (str): The plaintext password to verify
            
        Returns:
            bool: True if the password is correct, False otherwise
        """
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self) -> None:
        """更新最後登入時間"""
        try:
            self.last_login = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # 記錄錯誤但不影響登入流程
            if hasattr(current_app, 'logger'):
                current_app.logger.warning(f"Failed to update last login time: {e}")
    
    @property
    def post_count(self):
        """取得使用者的文章數量"""
        return self.posts.count()
    
    @property
    def published_post_count(self):
        """取得使用者已發布的文章數量"""
        return self.posts.filter_by(status='published').count()
    
    def to_dict(self) -> dict:
        """轉換為字典格式（不包含敏感資訊）"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'post_count': self.post_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        """
        String representation of the User object
        
        Returns:
            str: A string in the format "<User username>"
        """
        return f'<User {self.username}>'
    
    def __str__(self):
        return self.username


# ========================================
# Category Model
# ========================================

class Category(db.Model):
    """文章分類模型"""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(200), nullable=True)
    slug = db.Column(db.String(60), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 修復：使用 back_populates 而不是 backref，更清晰的雙向關聯
    # 移除 cascade 刪除，避免刪除分類時自動刪除文章
    posts = db.relationship('Post', back_populates='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'
    
    def __str__(self):
        return self.name
    
    @property
    def post_count(self):
        """取得該分類下的文章數量"""
        return self.posts.filter_by(status='published').count()
    
    @property
    def total_post_count(self):
        """取得該分類下所有文章數量（包含草稿）"""
        return self.posts.count()
    
    @property
    def is_default_category(self):
        """檢查是否為預設分類（Uncategorized）"""
        return self.slug == 'uncategorized'
    
    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'post_count': self.post_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ========================================
# Post Model
# ========================================

class Post(db.Model):
    """文章模型"""
    __tablename__ = 'posts'
    __table_args__ = (
        db.Index('idx_status_created_at', 'status', 'created_at'),
        db.Index('idx_category_status', 'category_id', 'status'),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    thumbnail = db.Column(db.String(500), nullable=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(160))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    status = db.Column(db.String(20), default='draft', index=True)
    
    # 外鍵關聯
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    
    # 關聯關係 - 使用 back_populates 保持一致性
    author = db.relationship('User', back_populates='posts')
    category = db.relationship('Category', back_populates='posts')

    def __repr__(self):
        return f'<Post {self.title}>'
    
    def __str__(self):
        return self.title

    def validate_status(self) -> None:
        """驗證 status 值，只允許 'draft' 或 'published'"""
        if self.status not in ['draft', 'published']:
            raise ValueError(f"Invalid status: {self.status}. Must be 'draft' or 'published'.")

    def local_created_at(self, app: 'Flask' = None):
        """轉換 created_at 為配置時區"""
        if not self.created_at:
            return None
        
        try:
            # 確保 created_at 是 aware datetime
            if self.created_at.tzinfo is None:
                # 如果是 naive datetime，假設它是 UTC
                aware_dt = pytz.UTC.localize(self.created_at)
            else:
                aware_dt = self.created_at
                
            tz_name = app.config.get('TIMEZONE', 'UTC') if app else current_app.config.get('TIMEZONE', 'UTC')
            tz = pytz.timezone(tz_name)
            return aware_dt.astimezone(tz)
        except Exception as e:
            current_app.logger.warning(f"時區轉換錯誤 (created_at): {e}")
            return self.created_at

    def local_updated_at(self, app: 'Flask' = None):
        """轉換 updated_at 為配置時區"""
        if not self.updated_at:
            return None
            
        try:
            # updated_at 應該已經是 aware datetime (有 timezone)
            tz_name = app.config.get('TIMEZONE', 'UTC') if app else current_app.config.get('TIMEZONE', 'UTC')
            tz = pytz.timezone(tz_name)
            return self.updated_at.astimezone(tz)
        except Exception as e:
            current_app.logger.warning(f"時區轉換錯誤 (updated_at): {e}")
            return self.updated_at
    
    @property
    def category_name(self):
        """取得分類名稱"""
        return self.category.name if self.category else 'Uncategorized'
    
    @property
    def category_slug(self):
        """取得分類 slug"""
        if self.category:
            return self.category.slug or self.category.name.lower().replace(' ', '-')
        return None
    
    @property
    def author_name(self):
        """取得作者名稱"""
        return self.author.username if self.author else 'Unknown'

    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'description': self.description,
            'thumbnail': self.thumbnail,
            'status': self.status,
            'category': self.category_name,
            'author': self.author_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    @cache.cached(timeout=600, key_prefix='blog_available_categories')  # 增加快取時間到10分鐘
    def get_available_categories():
        """取得所有可用的分類名稱（快取）"""
        try:
            # 只取得有已發布文章的分類，並按名稱排序
            categories = db.session.query(Category.name)\
                .join(Post)\
                .filter(Post.status == 'published')\
                .distinct()\
                .order_by(Category.name)\
                .all()
            result = [cat[0] for cat in categories]
            current_app.logger.debug(f"載入可用分類：{len(result)}個")
            return result
        except Exception as e:
            current_app.logger.error(f"Failed to fetch categories: {e}")
            return []

    @staticmethod
    def get_category_stats(status='published'):
        """統計每個類別下的文章數量"""
        results = db.session.query(
            Category.name,
            func.count(Post.id).label('count')
        ).join(Post, Category.id == Post.category_id).filter(
            Post.status == status
        ).group_by(Category.name).all()
        
        return results
    
    @classmethod
    def get_published_posts(cls, page=1, per_page=10):
        """取得已發布的文章（分頁）"""
        return cls.query.filter_by(status='published')\
                       .order_by(cls.created_at.desc())\
                       .paginate(page=page, per_page=per_page, error_out=False)
    
    @classmethod
    def get_posts_by_category(cls, category_name, page=1, per_page=10):
        """根據分類名稱取得文章（分頁）"""
        return cls.query.join(Category)\
                       .filter(func.lower(Category.name) == category_name.lower(),
                              cls.status == 'published')\
                       .order_by(cls.created_at.desc())\
                       .paginate(page=page, per_page=per_page, error_out=False)


# ========================================
# SQLAlchemy Events
# ========================================

# SQLAlchemy 事件：插入或更新前自動清理內容
@event.listens_for(Post, 'before_insert')
@event.listens_for(Post, 'before_update')
def clean_post_content(mapper, connection, target):
    """自動清理 content，防止不安全 HTML"""
    if target.content:
        target.content = clean_html_content(target.content)
    target.validate_status()
    
    # 確保 updated_at 有正確的時區資訊
    if not target.updated_at or target.updated_at.tzinfo is None:
        target.updated_at = datetime.now(timezone.utc)

# SQLAlchemy 事件：文章狀態變更時清理分類快取
@event.listens_for(Post, 'after_insert')
@event.listens_for(Post, 'after_update')
@event.listens_for(Post, 'after_delete')
def clear_category_cache_on_post_change(mapper, connection, target):
    """當文章新增、更新或刪除時，清理分類快取"""
    try:
        from app import cache
        cache.delete('blog_available_categories')
    except Exception:
        # 在事件監聽器中避免拋出異常
        pass