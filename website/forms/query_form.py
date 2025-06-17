from flask_wtf import FlaskForm
from wtforms import *
from wtforms.validators import DataRequired
from flask_wtf.file import FileAllowed

class QueryForm(FlaskForm):

    emp_type = SelectMultipleField('Department',  
                            choices=[
                                     ('Human Resource','Human Resource'),
                                     ('Accounts','Accounts'),
                                       ('IT Department', 'IT Department')],

                              validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    query_text = TextAreaField('Query', validators=[DataRequired()])
    photo = FileField('Attach File ', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    submit = SubmitField('Submit Query')


class QueryReplyForm(FlaskForm):

    reply_text = TextAreaField('Reply', validators=[DataRequired()])
    submit = SubmitField('Submit Reply')



class PasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')
