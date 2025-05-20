from flask_wtf import FlaskForm
from wtforms import *
from wtforms.validators import DataRequired

class QueryForm(FlaskForm):

    emp_type = SelectMultipleField('Department',  
                            choices=[
                                     ('Human Resource','Human Resource'),
                                     ('Accounts','Accounts'),
                                       ('IT Department', 'IT Department')],

                              validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    query_text = TextAreaField('Query', validators=[DataRequired()])
    submit = SubmitField('Submit Query')


class QueryReplyForm(FlaskForm):

    reply_text = TextAreaField('Reply', validators=[DataRequired()])
    submit = SubmitField('Submit Reply')



class PasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')
