
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField
from wtforms.validators import DataRequired, Email, Length, ValidationError,Optional
from werkzeug.security import generate_password_hash, check_password_hash  # For password hashing
from website.models.signup import Signup  # Importing the Signup model

class SignUpForm(FlaskForm): 
    email = StringField(
        'Email',
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "Enter your Email"}
    )

    emp_id = StringField(
        'Employee ID',
        validators=[DataRequired(), Length(max=10)],
        render_kw={"placeholder": "Enter your Employee ID"}
    )

    first_name = StringField(
        'Full Name',
        validators=[DataRequired(), Length(min=2, max=150)],
        render_kw={"placeholder": "Enter your Full Name"}
    )

    password = PasswordField(
        'Password',
        validators=[Optional()],
        render_kw={"placeholder": "Enter your Password"}
    )

    confirm_password = PasswordField(
        'Confirm Password',
        validators=[Optional()],
        render_kw={"placeholder": "Confirm your Password"}
    )

    doj = DateField(
        'Date of Joining', 
        format='%Y-%m-%d', 
        validators=[DataRequired()]
    )

    mobile = StringField(
        'Mobile Number',
        validators=[DataRequired(), Length(min=10, max=10, message="Mobile number must be exactly 10 digits.")],
        render_kw={"placeholder": "Enter your Mobile number"}
    )

    circle = SelectField('Circle', 
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
    
    emp_type = SelectField('Employee Type', 
                            choices=[('','Select Employee Type'),
                                     ('Human Resource','Human Resource'),
                                     ('Accounts','Accounts'), 
                                     ('Engineering', 'Engineering'),('TEC', 'TEC'),
                                     ('Certification', 'Certification'),
                                     ('Software Development', 'Software Development'),
                                     ('IT Department', 'IT Department')],
                              validators=[DataRequired()])

    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        existing = Signup.query.filter_by(email=email.data).first()
        if existing and str(existing.email) != str(self.email.data):
            raise ValidationError('This email is already in use.')

    def validate_mobile(self, mobile):
        existing = Signup.query.filter_by(mobile=mobile.data).first()
        if existing and str(existing.email) != str(self.email.data):
            raise ValidationError('This mobile number is already in use.')

    def validate_emp_id(self, emp_id):
        existing = Signup.query.filter_by(emp_id=emp_id.data).first()
        if existing and str(existing.email) != str(self.email.data):
            raise ValidationError('This Employee ID is already in use.')


    def validate_password(self, password):
        """Check if the password and confirm password fields match."""
        if password.data != self.confirm_password.data:
            raise ValidationError("Passwords do not match.")

    





from flask_wtf import FlaskForm
from wtforms import SelectField, PasswordField
from wtforms.validators import DataRequired, Length

class SelectRoleForm(FlaskForm):
    emp_type = SelectField('Employee Type', 
                           choices=[('','Select Employee Type'),
                                     ('Human Resource','Human Resource'),
                                     ('Accounts','Accounts'), 
                                
                                     ('Engineering', 'Engineering'),('TEC', 'TEC'),
                                     ('Certification', 'Certification'),
                                     ('Software Development', 'Software Development'),
                                     ('IT Department', 'IT Department')],
                              validators=[DataRequired()])
    
    password = PasswordField('Password', 
                             validators=[DataRequired()])
