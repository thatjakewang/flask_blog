"""
Form Classes for Blog Application

This module contains the form classes used throughout the blog application,
built on Flask-WTF and WTForms. It provides form validation, sanitization,
and HTML cleaning capabilities.

The forms include:
    - PostForm: For creating and editing blog posts with secure HTML content
    - LoginForm: For user authentication
"""
from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, PasswordField, SelectField
from wtforms.validators import DataRequired, Length, Regexp, ValidationError, Email, Optional
from flask_login import current_user
from app.models import Category
from app import cache
from app.utils import clean_html_content

class PostForm(FlaskForm):

    def __init__(self, original_post=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_post = original_post
        self.is_edit_mode = original_post is not None
        # 分類選項將在路由中設定

    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    slug = StringField('Slug', validators=[
        DataRequired(),
        Length(max=60),
        Regexp(r'^[a-z0-9-]+$', message='網址代碼只能包含小寫字母、數字和連字號')
    ])
    thumbnail = StringField('Thumbnail', validators=[
        Optional(),
        Length(max=500),
        Regexp(r'^[a-zA-Z0-9_\-\.]+$', message='檔案名稱只能包含字母、數字、底線、連字號和點')
    ])
    description = TextAreaField('Description', validators=[Length(max=160)])
    content = TextAreaField('Content', validators=[DataRequired()])
    category = SelectField('Category', coerce=int, validators=[Optional()])
    
    # 修復：在類別層級定義所有按鈕，避免動態創建
    save = SubmitField('Save as Draft')
    update = SubmitField('Save')
    preview = SubmitField('Preview')
    publish = SubmitField('Publish')
    
    # 已移除表單層級自定義屬性過濾；統一使用 utils.clean_html_content

    def _update_category_choices(self):
        """更新分類選項，每次都從資料庫重新載入"""
        try:
            # 先找出 Uncategorized 分類
            uncategorized = Category.query.filter_by(slug='uncategorized').first()
            other_categories = Category.query.filter(Category.slug != 'uncategorized').order_by(Category.name).all()
            
            # 將 Uncategorized 放在第一位（除了 Select Category）
            choices = [(0, 'Select Category')]
            if uncategorized:
                choices.append((uncategorized.id, uncategorized.name))
            choices.extend([(cat.id, cat.name) for cat in other_categories])
            
            self.category.choices = choices
            
            # 更新快取
            if current_app:
                cache.set('blog_category_choices', choices, timeout=current_app.config.get('CATEGORY_CACHE_TIMEOUT', 300))
            
            if current_app:
                current_app.logger.info(f"Updated category choices: {choices}")
            
        except Exception as e:
            user_id = current_user.id if current_user.is_authenticated else "Anonymous"
            if current_app:
                current_app.logger.error(f"Failed to load categories: {e}. User ID: {user_id}")
            self.category.choices = [(0, 'Select Category')]

    def _get_category_choices(self):
        # 保留這個方法以向後相容，但改為呼叫新的更新方法
        self._update_category_choices()
        return self.category.choices

    def validate_slug(self, field):
        from app.models import Post
        field.data = field.data.lower()

        post = Post.query.filter_by(slug=field.data).first()

        if post and (not self.original_post or post.id != self.original_post.id):
            raise ValidationError('此網址代碼已存在，請選擇其他代碼。')

    def validate_content(self, field):
        if len(field.data or '') > 100000:
            raise ValidationError('內容過長，請縮短內容。')
        # 與後端一致：使用 utils.clean_html_content 進行清理
        try:
            field.data = clean_html_content(field.data or '', context='form')
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Content validation error: {e}")
            raise ValidationError('內容處理錯誤，請檢查內容格式。')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="電子郵件為必填欄位。"),
        Email(message="電子郵件格式不正確。")
    ])
    password = PasswordField('Password', validators=[DataRequired(message="密碼為必填欄位。")])
    submit = SubmitField('Login')

class CategoryForm(FlaskForm):
    def __init__(self, original_category=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_category = original_category

    name = StringField('分類名稱', validators=[DataRequired(), Length(max=50)])
    slug = StringField('Slug', validators=[
        DataRequired(),
        Length(max=60),
        Regexp(r'^[a-z0-9-]+$', message='網址代碼只能包含小寫字母、數字和連字號')
    ])
    description = TextAreaField('分類描述', validators=[Length(max=200)])
    submit = SubmitField('儲存')

    def validate_slug(self, field):
        """驗證 slug 是否唯一"""
        from app.models import Category
        existing_category = Category.query.filter_by(slug=field.data).first()
        
        # 如果是編輯模式，排除當前分類
        if existing_category:
            if self.original_category and existing_category.id == self.original_category.id:
                return  # 允許保持相同的 slug
            raise ValidationError('此 slug 已被使用，請選擇其他 slug。')
