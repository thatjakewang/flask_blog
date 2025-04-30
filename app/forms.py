from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField,PasswordField
from wtforms.validators import DataRequired, Length, Regexp, ValidationError,Email
from lxml import html
from lxml.etree import ParserError
import bleach
from bleach.sanitizer import Cleaner

class PostForm(FlaskForm):

    cleaner = Cleaner(
        tags=['p', 'strong', 'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3'],
        attributes={'a': ['href', 'title']},
        strip=True
    )

    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    slug = StringField('Slug', validators=[
        DataRequired(),
        Length(max=60),
        Regexp(r'^[a-z0-9-]+$')
    ])
    description = TextAreaField('Description', validators=[Length(max=160)])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Save Post')

    def validate_slug(self, field):
        from app.models import Post
        if Post.query.filter_by(slug=field.data).first():
            raise ValidationError('別名已存在。')

    def validate_content(self, field):
        try:
            html.fromstring(field.data)
            field.data = self.cleaner.clean(field.data)
        except ParserError:
            raise ValidationError('Invalid HTML format.')
        except Exception as e:
            current_app.logger.error(f"Content validation error{e}")
            raise ValidationError('無法處理內容。')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')