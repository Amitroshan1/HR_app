from flask_wtf import FlaskForm
from wtforms import *
from wtforms.validators import *
from flask_wtf.file import FileAllowed





class Family_details(FlaskForm):

    Photo = FileField('Family Member Image *', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])

    name = StringField('Full_Name *', 
                         validators=[DataRequired()], 
                         render_kw={"placeholder": "Enter Name of Member"})
    
    email = StringField('Email_Id', 
                        validators=[Optional()], 
                        render_kw={"placeholder": "Enter Email_Id of Member"})
    

    dob=DateField("Date Of Birth",format='%Y-%m-%d', validators=[InputRequired()])

    age=IntegerField('Age *', 
                         validators=[DataRequired()], 
                         render_kw={"placeholder": "Enter  Age of Member"})
    
    relation = StringField('Relation *', 
                         validators=[DataRequired()], 
                         render_kw={"placeholder": "Enter Relation with Memeber"})
    
    occupation = StringField('Occupation *', 
                         validators=[DataRequired()], 
                         render_kw={"placeholder": "Enter Occupation of Member"})
    
    Income = StringField('Annual Income ', 
                         validators=[Optional()], 
                         render_kw={"placeholder": "Enter Annual Income Of Member"})
    
    Address = StringField('Address Of Member *', 
                         validators=[DataRequired()], 
                         render_kw={"placeholder": "Enter Address of Member"})
    
    Remarks= StringField('Remarks ', 
                         validators=[Optional()], 
                         render_kw={"placeholder": "Add Some More details.... "})
    
    
    
    submit = SubmitField('Save')
    


    
    