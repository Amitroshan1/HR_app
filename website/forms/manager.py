from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField,FileField,PasswordField
from wtforms.validators import DataRequired, Email, Length, Optional,EqualTo
from flask_wtf.file import FileAllowed

class ManagerContactForm(FlaskForm):
    circle_name = SelectField('Circle', 
                              choices=[('', 'Choose Your Circle'), ('NHQ', 'NHQ'),
                                        ('Noida', 'Noida'), 
                                        ('Noida-Loire','Noida-Loire'),('Haryana', 'Haryana'),
                                        ('Haryana-Loyal', 'Haryana-Loyal'),
                                       ('Gurugram', 'Gurugram'), ('Gurugram-Awesome','Gurugram-Awesome'),
                                       ('Gurugram-Rabbit','Gurugram-Rabbit'),('Pune', 'Pune'), 
                                       ('Jaipur', 'Jaipur'),('Jaipur-Rabbit', 'Jaipur-Rabbit'), ('Greater Noida', 'Greater Noida'), 
                                        ('Mumbai', 'Mumbai'),('G.Noida-Rabbit','G.Noida-Rabbit'),
                                        ('Mumbai-Bonita','Mumbai-Bonita'), ('Mumbai-Rabbit','Mumbai-Rabbit'), 
                                        ('Ahmedabad', 'Ahmedabad'), 
                                       ('Bangalore', 'Bangalore'), ('Punjab', 'Punjab'),
                                       ('Punjab-Loyal', 'Punjab-Loyal'), ('Ahmedabad', 'Ahmedabad'),
                                       ('Hyderabad', 'Hyderabad'), ('Chennai', 'Chennai'), 
                                       ('Kolkata', 'Kolkata'),('Kolkata-Rabbit', 'Kolkata-Rabbit')],
                              validators=[DataRequired()])
    
    
    user_type = SelectField('Department', 
                            choices=[('','Select Employee Type'),
                                     ('Human Resource','Human Resource'),
                                     ('Accounts','Accounts'), 
                                     ('Engineering', 'Engineering'),('TEC', 'TEC'),
                                     ('Certification', 'Certification'),
                                     ('Software Development', 'Software Development'),
                                     ('IT Department', 'IT Department')],
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





class PaySlipForm(FlaskForm):
    month = SelectField('Month', choices=[
        ('January', 'January'), ('February', 'February'), ('March', 'March'), 
        ('April', 'April'), ('May', 'May'), ('June', 'June'),
        ('July', 'July'), ('August', 'August'), ('September', 'September'),
        ('October', 'October'), ('November', 'November'), ('December', 'December')
    ], validators=[DataRequired()])
    
    year = SelectField('Year', choices=[(str(year), str(year)) for year in range(2024, 2036)],
                       validators=[DataRequired()])
    
    payslip_file = FileField('Upload PaySlip', validators=[FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'png'], 'Files only!')])
    submit = SubmitField('Add PaySlip')



class ChangePasswordForm(FlaskForm):
    original_password = PasswordField('Original Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_new_password = PasswordField('Confirm New Password', 
                                         validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Change Password')

    
