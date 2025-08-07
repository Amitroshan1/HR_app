
from flask_wtf import FlaskForm
from wtforms import DateField, TextAreaField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, ValidationError
from datetime import date
from flask_wtf.file import FileField, FileAllowed, FileRequired


class ResignationForm(FlaskForm):
    resignation_date = DateField('Resignation Date', validators=[DataRequired()], format='%Y-%m-%d')
    reason = TextAreaField('Reason for Resignation', validators=[DataRequired()])
    submit = SubmitField('Submit Resignation')

    # Optional: Prevent selecting a past date
    def validate_resignation_date(self, field):
        if field.data != date.today():
            raise ValidationError("Resignation date must be today's date.")


class NocForms(FlaskForm):
    noc_form_date = DateField('NOC Date: ', validators=[DataRequired()], format='%Y-%m-%d')
    emp_type = SelectMultipleField('Department',
                                   choices=[
                                       ('Human Resource', 'Human Resource'),
                                       ('Accounts', 'Accounts'),
                                       ('Manager','Manager'),
                                       ('IT Department', 'IT Department')],

                                   validators=[DataRequired()])
    sent_email = SubmitField('Send Email')


class NocUpload(FlaskForm):

    noc_file = FileField('Upload PaySlip',
                             validators=[FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'png'], 'Files only!')])
    submit = SubmitField('Add NOC')