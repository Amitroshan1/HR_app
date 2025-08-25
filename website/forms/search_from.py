
from flask_wtf import FlaskForm
from wtforms import *
from wtforms.validators import DataRequired,Optional

class SearchForm(FlaskForm):
    circle = SelectField('Circle', 
                            choices=[('', 'Choose Your Circle'), ('NHQ', 'NHQ'),
                                        ('Noida', 'Noida'), 
                                        ('Noida-Loire','Noida-Loire'),('Haryana', 'Haryana'),
                                        ('Haryana-Loyal', 'Haryana-Loyal'),
                                       ('Gurugram', 'Gurugram'), ('Gurugram-Awesome','Gurugram-Awesome'),
                                       ('Gurugram-Rabbit','Gurugram-Rabbit'),('Pune', 'Pune'), 
                                       ('Jaipur', 'Jaipur'), ('Jaipur-Rabbit', 'Jaipur-Rabbit'), ('Greater Noida', 'Greater Noida'), 
                                        ('Mumbai', 'Mumbai'),('G.Noida-Rabbit','G.Noida-Rabbit'),
                                        ('Mumbai-Bonita','Mumbai-Bonita'),('Mumbai-Victory','Mumbai-Victory'), ('Mumbai-Rabbit','Mumbai-Rabbit'), 
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
                                
                                     ('Engineering', 'Engineering'),
                                        ('TEC', 'TEC'),
                                     ('Certification', 'Certification'),
                                     ('Software Development', 'Software Development'),
                                     ('IT Department', 'IT Department')],
                              validators=[DataRequired()])
    
    submit = SubmitField('Search')



class DetailForm(FlaskForm):
    user = SelectField('User', choices=[], coerce=int)
    detail_type = SelectField('Detail Type', choices=[
        ('','Select Employee Details'),
        ('Family Details', 'Family Details'),
        ('Employee Details','Employee Details'),
        ('Document','Document'),
        ('Previous_company', 'Previous Company'),
        ('Education', 'Education'),
        ('Attendance', 'Attendance'),
        ('Leave Details', 'Leave Details'),
        ('Punch In-Out', 'Punch In-Out')
        ])
    
    submit = SubmitField('View Details')





class NewsFeedForm(FlaskForm):
    circle = SelectField('Circle', 
                            choices=[('', 'Choose Your Circle'),('ALL','ALL'), ('NHQ', 'NHQ'),
                                        ('Noida', 'Noida'), 
                                        ('Noida-Loire','Noida-Loire'),('Haryana', 'Haryana'),
                                        ('Haryana-Loyal', 'Haryana-Loyal'),
                                       ('Gurugram', 'Gurugram'), ('Gurugram-Awesome','Gurugram-Awesome'),
                                       ('Gurugram-Rabbit','Gurugram-Rabbit'),('Pune', 'Pune'), 
                                       ('Jaipur', 'Jaipur'),('Jaipur-Rabbit', 'Jaipur-Rabbit'), ('Greater Noida', 'Greater Noida'), 
                                        ('Mumbai', 'Mumbai'),('G.Noida-Rabbit','G.Noida-Rabbit'),
                                        ('Mumbai-Bonita','Mumbai-Bonita'),('Mumbai-Victory','Mumbai-Victory'),('Mumbai-Rabbit','Mumbai-Rabbit'), 
                                        ('Ahmedabad', 'Ahmedabad'), 
                                       ('Bangalore', 'Bangalore'), ('Punjab', 'Punjab'),
                                       ('Punjab-Loyal', 'Punjab-Loyal'), ('Ahmedabad', 'Ahmedabad'),
                                       ('Hyderabad', 'Hyderabad'), ('Chennai', 'Chennai'), 
                                       ('Kolkata', 'Kolkata'),('Kolkata-Rabbit', 'Kolkata-Rabbit')],
                              validators=[DataRequired()])
    
    emp_type = SelectField('Employee Type', 
                            choices=[('','Select Employee Type'),('ALL','ALL'),
                                     ('Human Resource','Human Resource'),
                                     ('Accounts','Accounts'), 
                                     
                                     ('Engineering', 'Engineering'),
                                     ('TEC', 'TEC'),
                                     ('Certification', 'Certification'),
                                     ('Software Development', 'Software Development'),
                                     ('IT Department', 'IT Department')],
                              validators=[DataRequired()])
    
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    file = FileField('File')
    submit = SubmitField('Post')


class SearchEmp_Id(FlaskForm):
    emp_id = StringField('Employee ID', validators=[DataRequired()])
    submit = SubmitField('Search')


from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, MultipleFileField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Optional



class AssetForm(FlaskForm):
    name = StringField('Asset Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    images = MultipleFileField('Upload Images', validators=[Optional()])  # ✅ Correctly define `images`
    issue_date = DateField('Issue Date', format='%Y-%m-%d')
    return_date = DateField('Return Date', format='%Y-%m-%d', validators=[Optional()])
    remark = TextAreaField('Remarks', validators=[Optional()])
    submit = SubmitField('Add Asset')


class PunchManuallyForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    punch_in = TimeField('Punch In', format='%H:%M:%S', validators=[Optional()])
    punch_out = TimeField('Punch Out', format='%H:%M:%S', validators=[Optional()])
    submit = SubmitField('Search')
    punch_submit = SubmitField('Save')




class SearchFormmanager(FlaskForm):
    circle = SelectField(
        'Circle',
        choices=[
            ('', 'Choose Your Circle'),
            ('NHQ', 'NHQ'),
            ('Noida', 'Noida'),
            ('Noida-Loire', 'Noida-Loire'),
            ('Haryana', 'Haryana'),
            ('Haryana-Loyal', 'Haryana-Loyal'),
            ('Gurugram', 'Gurugram'),
            ('Gurugram-Awesome', 'Gurugram-Awesome'),
            ('Gurugram-Rabbit', 'Gurugram-Rabbit'),
            ('Pune', 'Pune'),
            ('Jaipur', 'Jaipur'),
            ('Jaipur-Rabbit', 'Jaipur-Rabbit'),
            ('Greater Noida', 'Greater Noida'),
            ('Mumbai', 'Mumbai'),
            ('G.Noida-Rabbit', 'G.Noida-Rabbit'),
            ('Mumbai-Bonita', 'Mumbai-Bonita'),
            ('Mumbai-Victory', 'Mumbai-Victory'),
            ('Mumbai-Rabbit', 'Mumbai-Rabbit'),
            ('Ahmedabad', 'Ahmedabad'),
            ('Bangalore', 'Bangalore'),
            ('Punjab', 'Punjab'),
            ('Punjab-Loyal', 'Punjab-Loyal'),
            ('Hyderabad', 'Hyderabad'),
            ('Chennai', 'Chennai'),
            ('Kolkata', 'Kolkata'),
            ('Kolkata-Rabbit', 'Kolkata-Rabbit')
        ]
    )

    emp_type = SelectField(
        'Employee Type',
        choices=[
            ('', 'Select Employee Type'),
            ('Human Resource', 'Human Resource'),
            ('Accounts', 'Accounts'),
            ('Engineering', 'Engineering'),
            ('TEC', 'TEC'),
            ('Certification', 'Certification'),
            ('Software Development', 'Software Development'),
            ('IT Department', 'IT Department')
        ]
    )

    identifier = StringField(  # <-- for email or emp_id input
        'Employee Email / ID (optional)'
    )

    submit = SubmitField('Search')
