# -*- coding: utf-8 -*-
"""
Dashboard Blueprint

Provides administrative routes for post management: listing, creation, editing, deletion, and preview.
All routes require authentication.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from app.models import Post, db, Category
from app.forms import PostForm, CategoryForm
from sqlalchemy.exc import IntegrityError
from app.services.statistics_service import StatisticsService
from app.services.category_service import CategoryService
from app.services.post_service import PostService


bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@bp.route('/')
@login_required
def index():
    """Dashboard 首頁，顯示統計資訊"""
    stats = StatisticsService.get_dashboard_stats()
    
    # 更新最後登入時間
    if hasattr(current_user, 'update_last_login'):
        current_user.update_last_login()
    
    return render_template('dashboard/index.html', 
                         **stats,
                         active_page='dashboard', 
                         sub_active='overview')


@bp.route('/posts/')
@login_required
def posts():
    """文章列表頁面"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 50)
    
    # 建立查詢
    query = Post.query
    
    # 篩選條件
    status_filter = request.args.get('status')
    if status_filter in ['published', 'draft']:
        query = query.filter_by(status=status_filter)
    
    search_query = request.args.get('q')
    if search_query:
        query = query.filter(Post.title.contains(search_query))
    
    # 分頁查詢
    pagination = query.order_by(Post.created_at.desc()).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    stats = StatisticsService.get_dashboard_stats()
    
    return render_template('dashboard/posts.html', 
                         posts=pagination.items, 
                         pagination=pagination,
                         **stats,
                         active_page='dashboard', 
                         sub_active='posts')


@bp.route('/new_post/', methods=['GET', 'POST'])
@login_required
def new_post():
    """建立新文章"""
    form = PostForm()
    
    # 設定分類選項
    form._update_category_choices()
    
    # 設定新文章的預設分類為 Uncategorized
    if request.method == 'GET':
        uncategorized = Category.query.filter_by(slug='uncategorized').first()
        if uncategorized:
            form.category.data = uncategorized.id
    
    if form.validate_on_submit():
        # 判斷操作類型
        action = _determine_post_action(request.form)
        
        # 準備表單數據
        form_data = {
            'title': form.title.data,
            'slug': form.slug.data,
            'thumbnail': form.thumbnail.data,
            'description': form.description.data,
            'content': form.content.data,
            'category_id': form.category.data
        }
        
        # 創建文章
        result = PostService.create_post(form_data, action)
        
        if result['success']:
            flash(result['message'], 'success')
            return _handle_post_action_redirect(request.form, result)
        else:
            if result['error_type'] == 'integrity':
                form.slug.errors.append(result['message'])
            else:
                flash(result['message'], 'danger')
    
    stats = StatisticsService.get_dashboard_stats()
    
    return render_template('dashboard/new_post.html', 
                         form=form, 
                         post=None,
                         **stats,
                         active_page='dashboard', 
                         sub_active='posts')


@bp.route('/edit_post/<int:id>/', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    """編輯文章"""
    post = Post.query.get_or_404(id)
    
    # 檢查權限
    if not PostService.check_post_permission(post, current_user):
        abort(403)
    
    form = PostForm(obj=post, original_post=post)
    
    # 設定分類選項
    form._update_category_choices()
    
    # 設定當前分類
    if request.method == 'GET' and post.category_id:
        form.category.data = post.category_id
    
    if form.validate_on_submit():
        # 判斷操作類型
        action = _determine_post_action(request.form)
        
        # 準備表單數據
        form_data = {
            'title': form.title.data,
            'slug': form.slug.data,
            'thumbnail': form.thumbnail.data,
            'description': form.description.data,
            'content': form.content.data,
            'category_id': form.category.data
        }
        
        # 更新文章
        result = PostService.update_post(post, form_data, action)
        
        if result['success']:
            flash(result['message'], 'success')
            return _handle_post_action_redirect(request.form, result)
        else:
            if result['error_type'] == 'integrity':
                form.slug.errors.append(result['message'])
            flash(result['message'], 'danger')
    
    stats = StatisticsService.get_dashboard_stats()
    
    return render_template('dashboard/edit_post.html', 
                         form=form, 
                         post=post,
                         **stats,
                         active_page='dashboard', 
                         sub_active='posts')


@bp.route('/delete_post/<int:id>/', methods=['POST'])
@login_required
def delete_post(id):
    """刪除文章"""
    post = Post.query.get_or_404(id)
    
    # 檢查權限
    if not PostService.check_post_permission(post, current_user):
        abort(403)
    
    result = PostService.delete_post(post)
    flash(result['message'], 'success' if result['success'] else 'danger')
    
    return redirect(url_for('dashboard.posts'))


@bp.route('/preview_post/<int:id>/')
@login_required
def preview_post(id):
    """預覽文章"""
    post = Post.query.get_or_404(id)
    
    # 檢查權限
    if not PostService.check_post_permission(post, current_user):
        abort(403)
    
    return render_template('dashboard/preview_post.html', 
                         post=post,
                         active_page='dashboard', 
                         sub_active='posts')


@bp.route('/categories/')
@login_required
def categories():
    """分類列表頁面"""
    all_categories = Category.query.all()
    
    stats = StatisticsService.get_dashboard_stats()
    
    return render_template('dashboard/categories.html', 
                         categories=all_categories,
                         **stats,
                         active_page='dashboard', 
                         sub_active='categories')


@bp.route('/new_category/', methods=['GET', 'POST'])
@login_required
def new_category():
    """建立新分類"""
    form = CategoryForm()
    
    if form.validate_on_submit():
        cat = Category(
            name=form.name.data,
            slug=form.slug.data,
            description=form.description.data
        )
        db.session.add(cat)
        
        try:
            db.session.commit()
            
            # 清除快取（包含統計快取）
            CategoryService.clear_category_cache()
            
            flash('分類新增成功！', 'success')
            current_app.logger.info(f"分類 '{cat.name}' 由使用者 {current_user.id} 建立")
            
            return redirect(url_for('dashboard.categories'))
            
        except IntegrityError:
            db.session.rollback()
            flash('錯誤：分類名稱已存在。', 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"建立分類時發生錯誤：{e}")
            flash(f'新增失敗：{str(e)}', 'danger')
    
    stats = StatisticsService.get_dashboard_stats()
    
    return render_template('dashboard/new_category.html', 
                         form=form,
                         **stats,
                         active_page='dashboard', 
                         sub_active='categories')


@bp.route('/categories/edit/<int:id>/', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    """編輯分類"""
    category = Category.query.get_or_404(id)
    
    # 檢查是否為預設分類
    if category.is_default_category:
        flash('無法編輯預設分類 "Uncategorized"！', 'danger')
        return redirect(url_for('dashboard.categories'))
    
    form = CategoryForm(obj=category, original_category=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.slug = form.slug.data
        category.description = form.description.data
        
        try:
            db.session.commit()
            
            # 清除快取（包含統計快取）
            CategoryService.clear_category_cache()
            
            flash('分類更新成功！', 'success')
            current_app.logger.info(f"分類 {id} 由使用者 {current_user.id} 更新")
            return redirect(url_for('dashboard.categories'))
            
        except IntegrityError:
            db.session.rollback()
            flash('錯誤：分類名稱已存在，請選擇其他名稱。', 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"更新分類 {id} 時發生錯誤：{e}")
            flash(f'更新失敗：{str(e)}', 'danger')
    
    return render_template('dashboard/edit_category.html', 
                         form=form, 
                         category=category,
                         active_page='dashboard', 
                         sub_active='categories')


@bp.route('/categories/delete/<int:id>/', methods=['POST'])
@login_required
def delete_category(id):
    """刪除分類"""
    category = Category.query.get_or_404(id)
    
    try:
        # 除錯資訊
        category_name_debug = category.name or f"Category-{id}"
        current_app.logger.info(f"Attempting to delete category {id}: {category_name_debug}")
        current_app.logger.info(f"Is default category: {category.is_default_category}")
        current_app.logger.info(f"Post count: {category.post_count}")
        current_app.logger.info(f"Total post count: {category.total_post_count}")
        
        # 檢查是否為預設分類
        if category.is_default_category:
            flash('無法刪除預設分類 "Uncategorized"！', 'danger')
            current_app.logger.warning(f"阻止刪除預設分類 {id}")
            return redirect(url_for('dashboard.categories'))
        
        # 如果分類下有文章，自動移動到 Uncategorized
        if category.total_post_count > 0:
            current_app.logger.info(f"Moving {category.total_post_count} posts to Uncategorized")
            uncategorized = Category.query.filter_by(slug='uncategorized').first()
            
            if not uncategorized:
                flash('錯誤：找不到預設分類 "Uncategorized"！', 'danger')
                current_app.logger.error("找不到預設分類 'Uncategorized'！")
                return redirect(url_for('dashboard.categories'))
            
            # 將所有文章移到 Uncategorized
            moved_posts = []
            for post in category.posts:
                title = post.title or 'Untitled'
                status = post.status or 'unknown'
                current_app.logger.info(f"Moving post {post.id} '{title}' from category {category.id} to {uncategorized.id}")
                post.category_id = uncategorized.id
                moved_posts.append(f"{title} ({status})")
            
            flash(f'已將此分類下的 {category.total_post_count} 篇文章移至 "Uncategorized" 分類。', 'info')
            current_app.logger.info(f"Moved posts: {', '.join(moved_posts)}")
        
        # 執行刪除
        current_app.logger.info(f"Deleting category {id}")
        category_name = category.name or f"Category-{id}"  # 保存名稱用於日誌
        db.session.delete(category)
        db.session.commit()
        current_app.logger.info(f"Category {id} deleted successfully")
        
        # 清除快取（包含統計快取）
        CategoryService.clear_category_cache()
        
        flash('分類刪除成功！', 'success')
        current_app.logger.info(f"分類 '{category_name}' (ID: {id}) 由使用者 {current_user.id} 刪除")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"刪除分類 {id} 時發生錯誤：{str(e)}")
        flash(f"刪除失敗：{str(e)}", "danger")
    
    return redirect(url_for('dashboard.categories'))


# Helper functions
def _determine_post_action(form_data):
    """判斷文章操作類型"""
    if 'publish' in form_data:
        return 'publish'
    elif 'save' in form_data:
        return 'save'
    elif 'update' in form_data:
        return 'update'
    else:
        return 'save'  # 預設為儲存為草稿


def _handle_post_action_redirect(form_data, result):
    """處理文章操作後的重定向"""
    if 'preview' in form_data:
        return redirect(url_for('dashboard.preview_post', id=result['post_id']))
    elif 'publish' in form_data:
        post_slug = result['post_slug'] or f'untitled-{result["post_id"]}'
        return redirect(url_for('main.post', slug=post_slug))
    elif 'update' in form_data:
        # 更新已發布文章後，重定向到實際文章頁面
        post_slug = result['post_slug'] or f'untitled-{result["post_id"]}'
        return redirect(url_for('main.post', slug=post_slug))
    else:
        return redirect(url_for('dashboard.posts'))