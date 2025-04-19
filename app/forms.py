from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired, Length
from app.models import Tag, Category

class PostForm(FlaskForm):
    title = StringField('title', validators=[DataRequired(), Length(max=200)])
    slug = StringField('slug', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('description')
    content = TextAreaField('content', validators=[DataRequired()])
    tags = SelectMultipleField('tags', coerce=int)
    categories = SelectMultipleField('categories', coerce=int)
    published = BooleanField('published')
    
    def populate_tags_and_categories(self):
        self.tags.choices = [(tag.id, tag.name) for tag in Tag.query.all()]
        self.categories.choices = [(cat.id, cat.name) for cat in Category.query.all()]