from flask import Blueprint, render_template, request, redirect, url_for
from app.models import Post, Page, Tag
from app import db

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@bp.route('/tag/<slug>')
def tag(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    posts = tag.posts
    return render_template('tag.html', tag=tag, posts=posts)

@bp.route('/<slug>')
def dynamic_page(slug):
    page = Page.query.filter_by(slug=slug).first()
    if page:
        return render_template('page.html', page=page)
    
    post = Post.query.filter_by(slug=slug).first_or_404()
    return render_template('post.html', post=post)