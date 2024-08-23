from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, Optional

class ManagerContactForm(FlaskForm):
    circle_name = SelectField('Circle', 
                              choices=[('', 'Choose Your Circle'), ('nhq', 'NHQ'), ('noida', 'Noida'), ('haryana', 'Haryana'),
                                       ('gurugram', 'Gurugram'), ('pune', 'Pune'), ('bangalore', 'Bangalore'), ('punjab', 'Punjab'),
                                       ('hyderabad', 'Hyderabad'), ('chennai', 'Chennai'), ('kolkata', 'Kolkata')],
                              validators=[DataRequired()])
    
    user_type = SelectField('Department', 
                            choices=[('', 'Select Department'), ('hr', 'Human Resource'), ('finance', 'Accounts & Finance'), 
                                     ('employee', 'Software'),('it department','IT Department')],
                            validators=[DataRequired()])
    
    l1_name = StringField('L1 Name', validators=[Optional()])
    l1_mobile = StringField('L1 Mobile', validators=[Optional(), Length(min=10, max=10)])
    l1_email = StringField('L1 Email', validators=[Optional(), Email()])
    l2_name = StringField('L2 Name', validators=[DataRequired()])
    l2_mobile = StringField('L2 Mobile', validators=[DataRequired(), Length(min=10, max=10)])
    l2_email = StringField('L2 Email', validators=[DataRequired(), Email()])
    l3_name = StringField('L3 Name', validators=[DataRequired()])
    l3_mobile = StringField('L3 Mobile', validators=[DataRequired(), Length(min=10, max=10)])
    l3_email = StringField('L3 Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Submit')




    
