from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp


post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    
    def __repr__(self):
        return f'<Tag {self.name}>'

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    published = db.Column(db.Boolean, default=False)

    tags = db.relationship('Tag', secondary=post_tags, lazy='subquery',
                         backref=db.backref('posts', lazy=True))
    
    def __repr__(self):
        return f'<Post {self.title}>'
    
class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    published = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0) 
    in_menu = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Page {self.title}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=100)])
    slug = StringField('Slug', validators=[
        DataRequired(),
        Length(min=1, max=150),
        Regexp(r'^[a-z0-9-]+$', message='Slug must contain only lowercase letters, numbers, and hyphens')
    ])
    description = TextAreaField('Description', validators=[Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    published = BooleanField('Publish')
    tags = SelectMultipleField('Tags', coerce=int)
    submit = SubmitField('Submit')

    def populate_tags(self):
        tags = Tag.query.order_by(Tag.name.asc()).all()
        self.tags.choices = [(tag.id, tag.name) for tag in tags]