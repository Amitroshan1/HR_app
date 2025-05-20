
from flask_wtf import FlaskForm
from wtforms import *
from wtforms.validators import DataRequired,Optional

class SearchForm(FlaskForm):
    circle = SelectField('Circle', 
                            choices=[('','Select Circle'),('NHQ', 'NHQ'),
                                    ('Noida', 'Noida'),('Punjab', 'Punjab'),
                                    ('Haryana', 'Haryana'),('Gurugram','Gurugram'),
                                    ('Pune','Pune'),('Banglore','Banglore'),
                                    ('Hydrabad','Hydrabad'),
                                    ('Chennai','Chennai'),('Kolkata','Kolkata')],
                              validators=[DataRequired()])
    
    emp_type = SelectField('Employee Type', 
                            choices=[('','Select Employee Type'),
                                     ('Human Resource','Human Resource'),
                                     ('Accounts','Accounts'), 
                                     ('Testing', 'Testing'),
                                     ('Software Development', 'Software Development'),
                                     ('It Department', 'IT Department')],
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
        ('Leave Details', 'Leave Details')
        ])
    
    submit = SubmitField('View Details')





class NewsFeedForm(FlaskForm):
    circle = SelectField('Circle', 
                            choices=[("",'Select Circle'),('All','All'),('NHQ', 'NHQ'),
                                     ('Punjab', 'Punjab'),('Haryana', 'Haryana'),
                                     ('Noida', 'Noida'),('Gurugram','Gurugram'),
                                     ('Pune','Pune'),('Banglore','Banglore'),
                                     ('Hydrabad','Hydrabad'),
                                     ('Chennai','Chennai'),('Kolkata','Kolkata')],
                              validators=[DataRequired()])
    emp_type = SelectField('Employee Type', 
                            choices=[("",'Select Employee Type'),('All','All'),
                                     ('Human Resource','Human Resource'),
                                     ('Accounts','Accounts'),
                                    ('Testing', 'Testing'),('Software Development', 'Software Development'),
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




