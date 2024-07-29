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
                            choices=[('choose your Designation', 'Choose Your Designation '),
                                      ('test Engineer','Test Engineer'),
                                      ('senior test engineer','Senior Test Engineer'),
                                      ('qa Engineer','QA Engineer'),
                                      ('dt','DT Engineer'),
                                      ('technical service Engineer','Technical Service Engineer'),
                                       ('associate software Engineer','Associate Software Engineer'),
                                        ('software engineer','Software Engineer'),
                                         ('senior software engineer','Senior Software Engineer'),
                                         ('project lead','Project Lead'),
                                         ('project manager','Project Manager'),
                                     ('vice President-Sales and operation', 'Vice President-Sales and Operation'),
                                     ('GM- electronics security','GM- Electronics Security'),
                                     ('deputy manager - Operations and Admin',"Deputy Manager - Operations and Admin"),
                                     ('technical accounts Manager','Technical Accounts Manager'),
                                     ('accounts Manager','Accounts Manager'),
                                     ('accounts executive','Accounts Executive'),
                                     ('senior Executive - HR','Senior Executive - HR'),
                                     ('hr Executive','HR Executive'),
                                     ('inventory Executive','Inventory Executive'),
                                     ('office Boy','Office Boy'),
                                     ('business Development Management','Business Development Management'),
                                     ('sales executive','Sales Executive'),
                                     ('circle Head','Circle Head'),
                                     ('delivery Head','Delivery Head'),
                                     ('seniorManager - Auditor','SeniorManager - Auditor'),
                                     ('travel Executive','Travel Executive'),
                                     ('visa Executive','Visa Executive'),
                                     ('Tender Executive','Tender Executive'),
                                     ('project manager','Project Manager')],
                              validators=[DataRequired()])



    emp_id = StringField('Employee ID *', 
                        validators=[Optional()], 
                        render_kw={"placeholder": "Enter your Employee_ID"})
    

    mobile = StringField('Mobile Number *', 
                         validators=[DataRequired(), Length(min=10, max=10)], 
                         render_kw={"placeholder": "Enter your Mobile number"})
    
    gender = SelectField('Gender *', 
                            choices=[('male', 'Male'), ('female', 'Female')],
                              validators=[DataRequired()])
    
    emergency_mobile = StringField('Emergency Number *', 
                         validators=[DataRequired(), Length(min=10, max=10)], 
                         render_kw={"placeholder": "Enter your Emergency Conatct Number"})
    
    caste = SelectField('Caste *', 
                            choices=[('choose your caste', 'Choose Your Caste '), ('general', 'General'),('obc','Obc'),('sc','SC'),
                                     ('st',"ST")],
                              validators=[DataRequired()])
    
    nationality = StringField('Nationality *', 
                             validators=[DataRequired(), Length(min=2, max=150)], 
                             render_kw={"placeholder": "Enter your Nationality"})
    
    language = StringField('Language', 
                             validators=[DataRequired(), Length(min=2, max=150)], 
                             render_kw={"placeholder": "Enter the Language"})
    
    religion = SelectField('Religion *', 
                            choices=[('choose your religion', 'Choose Your Religion '), ('hindu', 'Hindu'),('muslim','Muslim'),('christian','Christian'),
                                     ('buddhism',"Buddhism"),('sikh','Sikh'),('jain','Jain')],
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
    
    
    
    
    
    
    

    

    

    