from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from bleach import clean
from app.models import Post, Tag, db, Category
from app.forms import PostForm

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/')
@login_required
def index():
    return render_template('dashboard/index.html')

@bp.route('/posts')
@login_required
def posts():
    all_posts = Post.query.all()
    return render_template('dashboard/posts.html', posts=all_posts)

@bp.route('/new_post', methods=['GET', 'POST'])
@login_required
def new_post():

    form = PostForm()
    form.populate_tags_and_categories() 

    if request.method == 'POST' and form.validate_on_submit():

        post = Post(
            title=form.title.data,
            slug=form.slug.data.lower(),
            description=form.description.data,
            content=form.content.data,
            published=form.published.data
        
        )
        if form.tags.data:
            post.tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()

        if form.categories.data:
            post.categories = Category.query.filter(Category.id.in_(form.categories.data)).all()

        try:
            db.session.add(post)
            db.session.commit()
            flash('Article saved successfully！', 'success')
            
            if post.published:
                return redirect(url_for('main.dynamic_page', slug=post.slug))
            else:
                return redirect(url_for('dashboard.posts_edit'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create article: {str(e)}', 'error')

    return render_template('dashboard/new_post.html', form=form)