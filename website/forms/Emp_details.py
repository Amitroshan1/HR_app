from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField,SelectField,FileField,DateField
from wtforms.validators import *
from flask_wtf.file import FileAllowed




class Employee_Details(FlaskForm):
    Photo = FileField('Employee Image ', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    name = StringField('Full_Name *', 
                         validators=[DataRequired()], 
                         render_kw={"placeholder": "Enter your Name"})
    
    email = StringField('Email_Id *', 
                        validators=[DataRequired(), Email()], 
                        render_kw={"placeholder": "Enter your Email_Id"})
    
    father_name=StringField('Father Name *', 
                         validators=[DataRequired()], 
                         render_kw={"placeholder": "Enter your Father Name"})
    
    mother_name=StringField('Mother Name', 
                         validators=[DataRequired()], 
                         render_kw={"placeholder": "Enter your Mother Name"})
    

    marital_status = SelectField('Marital *', 
                            choices=[('married', 'Married'), ('unmarried', 'Unmarried')],
                              validators=[DataRequired()])
    
    spouse_name=StringField('Spouse Name', 
                         validators=[Optional()], 
                         render_kw={"placeholder": "Enter your Spouse Name"})
    
    dob=DateField("Date Of Birth *",format='%Y-%m-%d', validators=[InputRequired()])


    designation  = SelectField('Designation *', 
                            choices=[('', 'Choose Your Designation '),
                                      ('Test Engineer','Test Engineer'),
                                      ('Senior test engineer','Senior Test Engineer'),
                                      ('Qa Engineer','QA Engineer'),
                                      ('DT Engineer','DT Engineer'),
                                      ('Technical Service Engineer','Technical Service Engineer'),
                                       ('Associate Software Engineer','Associate Software Engineer'),
                                        ('Software Engineer','Software Engineer'),
                                   ('Senior Software Engineer','Senior Software Engineer'),
                                   ('Project Lead','Project Lead'),
                                   ('Project Manager','Project Manager'),
                                     ('Vice President-Sales and Operation', 'Vice President-Sales and Operation'),
                                     ('GM-Electronics Security','GM-Electronics Security'),
                                     ('Deputy Manager - Operations and Admin',"Deputy Manager - Operations and Admin"),
                                     ('Technical Accounts Manager','Technical Accounts Manager'),
                                     ('Accounts Manager','Accounts Manager'),
                                     ('Accounts Executive','Accounts Executive'),
                                     ('Senior Executive - HR','Senior Executive - HR'),
                                     ('Hr Executive','HR Executive'),
                                     ('Inventory Executive','Inventory Executive'),
                                     ('Office Boy','Office Boy'),
                                     ('Business Development Management','Business Development Management'),
                                     ('Sales executive','Sales Executive'),
                                     ('Circle Head','Circle Head'),
                                     ('Delivery Head','Delivery Head'),
                                     ('SeniorManager - Auditor','SeniorManager - Auditor'),
                                     ('Travel Executive','Travel Executive'),
                                     ('Visa Executive','Visa Executive'),
                                     ('Tender Executive','Tender Executive'),
                                     ('Project manager','Project Manager')],
                              validators=[DataRequired()])



    emp_id = StringField('Employee ID *', 
                        validators=[Optional()], 
                        render_kw={"placeholder": "Enter your Employee_ID"})
    

    mobile = StringField('Mobile Number *', 
                         validators=[DataRequired(), Length(min=10, max=10)], 
                         render_kw={"placeholder": "Enter your Mobile number"})
    
    gender = SelectField('Gender *', 
                            choices=[('Male', 'Male'), ('Female', 'Female')],
                              validators=[DataRequired()])
    
    emergency_mobile = StringField('Emergency Number *', 
                         validators=[DataRequired(), Length(min=10, max=10)], 
                         render_kw={"placeholder": "Enter your Emergency Conatct Number"})
    
    caste = SelectField('Caste *', 
                            choices=[('', 'Choose Your Caste '), 
                                     ('General', 'General'),('Obc','Obc'),('Sc','SC'),
                                     ('St',"ST")],
                              validators=[DataRequired()])
    
    nationality = StringField('Nationality *', 
                             validators=[DataRequired(), Length(min=2, max=150)], 
                             render_kw={"placeholder": "Enter your Nationality"})
    
    language = StringField('Language', 
                             validators=[DataRequired(), Length(min=2, max=150)], 
                             render_kw={"placeholder": "Enter the Language"})
    
    religion = SelectField('Religion *', 
                            choices=[('', 'Choose Your Religion '), 
                                     ('hindu', 'Hindu'),('muslim','Muslim'),
                                     ('christian','Christian'),
                                     ('Buddhism',"Buddhism"),('Sikh','Sikh'),('Jain','Jain')],
                              validators=[DataRequired()])
    
    blood_group = StringField('Blood Group *', 
                             validators=[DataRequired(), Length(min=2, max=150)], 
                             render_kw={"placeholder": "Enter your Blood Group"})
    
  
    
    permanent_address_line1 = StringField('Address Line 1 *', validators=[DataRequired()])
    permanent_address_line2 = StringField('Address Line 2')
    permanent_address_line3 = StringField('Address Line 3')
    permanent_pincode = StringField('Pincode *', validators=[DataRequired()])
    permanent_district = StringField('District *', validators=[DataRequired()])
    permanent_state = StringField('State *', validators=[DataRequired()])

    present_address_line1 = StringField('Address Line 1 *', validators=[DataRequired()])
    present_address_line2 = StringField('Address Line 2')
    present_address_line3 = StringField('Address Line 3')
    present_pincode = StringField('Pincode *', validators=[DataRequired()])
    present_district = StringField('District *', validators=[DataRequired()])
    present_state = StringField('State *', validators=[DataRequired()])

    submit = SubmitField('Save')
    
    
    
    
    
    
    

    

    

    