from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from bleach import clean
from app.models import Post, db
from app.forms import PostForm
from sqlalchemy.exc import IntegrityError
import bleach

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/')
@login_required
def index():
    return render_template('dashboard/index.html')

@bp.route('/posts')
@login_required
def posts():
    all_posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('dashboard/posts.html', posts=all_posts)

@bp.route('/new_post', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()

    if form.validate_on_submit():
        post = Post(
            title=form.title.data,
            slug=form.slug.data.lower(),
            description=form.description.data,
            content=bleach.clean(form.content.data, tags=['p', 'strong', 'h1', 'h2', 'ul', 'ol', 'li', 'a'], attributes={'a': ['href']}),
        )

        db.session.add(post)
        try:
            db.session.commit()
            flash('Post created successfully!', 'success')
            return redirect(url_for('main.post', slug=post.slug))
        except IntegrityError as e:
            db.session.rollback()
            form.slug.errors.append("This slug is already in use. Please choose a different one.")
            flash('Error: Could not create post. Please check the form.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: Could not create post due to an unexpected error: {str(e)}', 'error')

    return render_template('dashboard/new_post.html', form=form)

@bp.route('/edit_post/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):

    post = Post.query.get_or_404(id)
    form = PostForm()

    if form.validate_on_submit():
        # 更新文章資料
        post.title = form.title.data
        post.slug = form.slug.data.lower()
        post.description = form.description.data
        post.content = bleach.clean(form.content.data, tags=['p', 'strong', 'h1', 'h2', 'ul', 'ol', 'li', 'a'], attributes={'a': ['href']})

        try:
            db.session.commit()
            flash('Post updated successfully!', 'success')
            return redirect(url_for('dashboard.posts'))
        
        except IntegrityError:
            db.session.rollback()
            form.slug.errors.append("This slug is already in use. Please choose a different one.")
            flash('Error: Could not update post. Please check the form.', 'error')

        except Exception as e:
            db.session.rollback()
            flash(f'Error: Could not update post: {str(e)}', 'error')

    if request.method == 'GET':
        form.title.data = post.title
        form.slug.data = post.slug
        form.description.data = post.description
        form.content.data = post.content
    
    return render_template('dashboard/edit_post.html', form=form, post=post)

@bp.route('/delete_post/<int:id>', methods=['GET'])
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)

    try:
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted successfully!', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Error: Could not delete post due to database constraints.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: Could not delete post: {str(e)}', 'error')
    return redirect(url_for('dashboard.posts'))