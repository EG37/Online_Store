from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, StringField
from wtforms.validators import DataRequired


class SearchForm(FlaskForm):
    name = StringField('Наименование товара', validators=[DataRequired()])
    category = SelectField('Категория', choices=[])
    submit = SubmitField('Поиск')
