from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField,SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from lxml import html

class PostForm(FlaskForm):
    title = StringField('title', validators=[DataRequired(), Length(max=200)])
    slug = StringField('slug', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Length(max=160, message='Description should be 160 characters or less.')])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Save Post')

    def validate_content(self, field):
        try:
            html.fromstring(field.data)
        except Exception as e:
            raise ValidationError('Invalid HTML format.')