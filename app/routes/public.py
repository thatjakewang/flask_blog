# -*- coding: utf-8 -*-
"""
Public Routes Blueprint

This module contains all public-facing routes including main pages, authentication,
and sitemap functionality. These routes are accessible to all users without authentication.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, Response, abort, Flask
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from urllib.parse import urlparse
from datetime import date

from app.models import User, Post, Category
from app.forms import LoginForm


# ========================================
# Blueprint Setup
# ========================================

# Main public routes
main_bp = Blueprint('main', __name__)

# Authentication routes
auth_bp = Blueprint('auth', __name__)

# Sitemap routes
sitemap_bp = Blueprint('sitemap', __name__)


# ========================================
# Main Routes (previously main.py)
# ========================================

@main_bp.route('/')
def index():
    """主頁：顯示已發布的文章列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = Post.query.filter_by(status='published') \
                           .order_by(Post.created_at.desc()) \
                           .paginate(page=page, per_page=per_page, error_out=False)
    return render_template('main/index.html', posts=pagination.items, pagination=pagination, active_page='home')


@main_bp.route('/<slug>/', methods=['GET'])
def post(slug):
    """顯示單篇文章"""
    if not slug:
        abort(404)
    
    slug = slug.strip().lower()
    
    # Handle generated slugs for posts without slugs
    if slug.startswith('untitled-'):
        try:
            post_id = int(slug.replace('untitled-', ''))
            post = Post.query.filter_by(id=post_id).first_or_404()
        except ValueError:
            abort(404)
    else:
        post = Post.query.filter_by(slug=slug).first_or_404()
    
    # 只有已發布的文章或已登入用戶可以查看草稿
    if post.status == 'draft' and not current_user.is_authenticated:
        abort(404)
    
    return render_template('blog/post.html', post=post)


@main_bp.route('/category/<string:slug>/')
def category(slug):
    """顯示指定分類的文章"""
    category = Category.query.filter_by(slug=slug).first_or_404()

    # Redirect to lowercase URL for SEO
    if slug != slug.lower():
        return redirect(url_for('main.category', slug=slug.lower()), code=301)
    
    # Query published posts in this category with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = Post.query.join(Category) \
        .filter(
            func.lower(Category.slug) == slug.lower(),
            Post.status == 'published'
        ) \
        .order_by(Post.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    posts = pagination.items

    return render_template(
        'main/category.html',
        posts=posts,
        pagination=pagination,
        category=category,   # 傳整個 category object 給 template，比單純 name 更彈性
        active_page='category'
    )


@main_bp.route('/robots.txt')
def robots_txt():
    """提供robots.txt檔案"""
    return send_from_directory(current_app.static_folder, 'robots.txt')


# ========================================
# Authentication Routes (previously auth.py)
# ========================================

@auth_bp.route('/admin_login/', methods=['GET', 'POST'])
def admin_login():
    """管理員登入頁面"""
    
    # 如果已經登入，重定向到管理後台
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        # 記錄登入嘗試
        current_app.logger.info(f"Login attempt for email: {email}")
        
        # 查詢用戶
        user = User.query.filter_by(email=email).first()
        
        if user is None:
            current_app.logger.warning(f"登入失敗：找不到電子郵件 {email} 的使用者")
            flash('無效的電子郵件或密碼。', 'danger')
            return redirect(url_for('auth.admin_login'))
        
        if not user.check_password(password):
            current_app.logger.warning(f"登入失敗：使用者 {email} 的密碼不正確")
            flash('無效的電子郵件或密碼。', 'danger')
            return redirect(url_for('auth.admin_login'))
        
        # 登入成功
        login_user(user, remember=True)
        current_app.logger.info(f"使用者 {email} 成功登入")
        
        # 更新最後登入時間
        if hasattr(user, 'update_last_login'):
            user.update_last_login()
        
        # 處理next頁面重定向
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('dashboard.index')
            
        flash('歡迎回來！', 'success')
        return redirect(next_page)
    
    # 記錄表單驗證錯誤
    if request.method == 'POST' and not form.validate_on_submit():
        current_app.logger.warning(f"表單驗證失敗：{form.errors}")
    
    return render_template('auth/login.html', form=form, active_page='login')


@auth_bp.route('/logout/')
@login_required
def logout():
    """用戶登出"""
    user_email = current_user.email if current_user.is_authenticated else 'Unknown'
    logout_user()
    current_app.logger.info(f"使用者 {user_email} 已登出")
    flash('您已成功登出。', 'info')
    return redirect(url_for('main.index'))


# ========================================
# Sitemap Routes (previously sitemap.py)
# ========================================

@sitemap_bp.route('/sitemap.xml', methods=['GET'])
def sitemap():
    """
    生成XML網站地圖，包含靜態頁面和已發布的部落格文章
    靜態路由和文章設定可在配置中調整
    """
    pages = []
    today = date.today().isoformat()

    # 1️⃣ 靜態路由，從配置讀取
    static_routes = current_app.config.get('SITEMAP_STATIC_ROUTES', ['main.index'])
    for endpoint in static_routes:
        try:
            url = url_for(endpoint, _external=True)
            pages.append({
                'loc': url,
                'lastmod': today,
                'changefreq': 'daily',
                'priority': '1.0',
            })
        except Exception as e:
            current_app.logger.warning(f"無法為 {endpoint} 生成網站地圖項目：{e}")

    # 2️⃣ 查詢文章，加入錯誤處理
    try:
        posts = Post.query.filter_by(status='published').yield_per(100)
    except Exception as e:
        current_app.logger.error(f"無法為網站地圖取得文章：{e}")
        posts = []

    for post in posts:
        post_slug = post.slug or f'untitled-{post.id}'
        post_url = url_for('main.post', slug=post_slug, _external=True)
        updated = (post.updated_at or post.created_at).date().isoformat()

        # 3️⃣ 動態設置 changefreq 和 priority（可在 Post 模型增加屬性）
        changefreq = getattr(post, 'changefreq', 'monthly')
        priority = getattr(post, 'priority', '0.8')

        pages.append({
            'loc': post_url,
            'lastmod': updated,
            'changefreq': changefreq,
            'priority': priority,
        })

    return Response(
        render_template("sitemap.xml", pages=pages),
        mimetype='application/xml'
    )

# ========================================
# Blueprint Registration Helper
# ========================================

def register_public_blueprints(app: 'Flask') -> None:
    """
    統一註冊所有公開路由的Blueprint
    
    Args:
        app: Flask應用程式實例
    """
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(sitemap_bp)
    
    app.logger.info("所有公開路由藍圖已成功註冊")