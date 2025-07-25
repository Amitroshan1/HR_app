
from flask_wtf import FlaskForm
from wtforms import DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, ValidationError
from datetime import date

class ResignationForm(FlaskForm):
    resignation_date = DateField('Resignation Date', validators=[DataRequired()], format='%Y-%m-%d')
    reason = TextAreaField('Reason for Resignation', validators=[DataRequired()])
    submit = SubmitField('Submit Resignation')

    # Optional: Prevent selecting a past date
    def validate_resignation_date(self, field):
        if field.data != date.today():
            raise ValidationError("Resignation date must be today's date.")
