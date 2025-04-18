from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from bleach import clean
from app.models import Post, Tag, db, PostForm

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/')
@login_required
def index():
    return render_template('dashboard/index.html')

@bp.route('/new_post', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    form.populate_tags()

    if request.method == 'POST':
        if 'content' in request.form:
            form.content.data = request.form['content']
    
        if form.validate_on_submit():
            # 檢查 slug 是否已存在
            existing_post = Post.query.filter_by(slug=form.slug.data).first()
            if existing_post:
                flash('This slug is already in use. Please choose a different one.', 'error')
                return render_template('dashboard/new_post.html', form=form)

            # 過濾 CKEditor 的 HTML 內容
            allowed_tags = [
                'p', 'br', 'strong', 'em', 'u', 's',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'a', 'blockquote', 'code', 'pre',
                'ul', 'ol', 'li', 'table', 'tr', 'td', 'th'
            ]
            allowed_attributes = {
                'a': ['href', 'title'],
                'table': ['border']
            }
            safe_content = clean(form.content.data, tags=allowed_tags, attributes=allowed_attributes)
            
            # 創建新文章
            post = Post(
                title=form.title.data,
                slug=form.slug.data.lower(),  # 確保 slug 是小寫
                description=form.description.data,
                content=safe_content,
                published=form.published.data
            )
            post.tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()
            
            try:
                db.session.add(post)
                db.session.commit()
                print(f"Post saved with slug: {post.slug}")
            except Exception as e:
                db.session.rollback()
                flash(f'Error saving post: {str(e)}', 'error')
                return render_template('new_post.html', form=form)
            
            # 提交後重定向
            if post.published:
                flash('文章已成功發布！', 'success')
                return redirect(url_for('main.dynamic_page', slug=post.slug))
            else:
                flash('文章已保存為草稿。', 'info')
                return redirect(url_for('dashboard.post_preview', slug=post.slug))
        
    return render_template('new_post.html', form=form)

@bp.route('/preview/<slug>')
@login_required
def post_preview(slug):
    print(f"Previewing post with slug: {slug}")  # 添加日誌
    post = Post.query.filter_by(slug=slug).first_or_404()
    return render_template('dashboard/post_preview.html', post=post)