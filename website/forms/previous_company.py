from flask_wtf import FlaskForm
from wtforms import StringField, DateField, IntegerField, SubmitField
from wtforms.validators import DataRequired, InputRequired, Optional

class Previous_company(FlaskForm):
    com_name = StringField('Company Name *',
                           validators=[DataRequired()],
                           render_kw={"placeholder": "Enter your Previous Company Name"})
    
    designation = StringField('Designation *',
                              validators=[DataRequired()],
                              render_kw={"placeholder": "Enter your Designation"})
    
    doj = DateField("Date Of Joining *", format='%Y-%m-%d', validators=[InputRequired()])
    
    dol = DateField("Last Date in company *", format='%Y-%m-%d', validators=[InputRequired()])
    
    reason = StringField('Reason for Leaving *',
                         validators=[DataRequired()],
                         render_kw={"placeholder": "Reason for Leaving"})
    
    salary = StringField('Salary in Previous company *',
                         validators=[DataRequired()],
                         render_kw={"placeholder": "Enter Your Salary"})
    
    uan = StringField("UAN", validators=[Optional()],
                      render_kw={"placeholder": "Enter Your UAN"})
    
    pan = StringField("PAN", validators=[DataRequired()],
                      render_kw={"placeholder": "Enter Your PAN"})
    
    contact = IntegerField('Contact Number',
                           validators=[DataRequired()],
                           render_kw={"placeholder": "Enter Contact No. of Previous Company"})
    
    name_contact = StringField("Name of the Contact", validators=[DataRequired()],
                               render_kw={"placeholder": "Enter Name of the Contact"})
    
    pf_num = StringField("PF Number", validators=[DataRequired()],
                         render_kw={"placeholder": "Enter Your PF Number "})
    
    address = StringField("Address", validators=[DataRequired()],
                          render_kw={"placeholder": "Enter the Address of Company "})
    
    submit = SubmitField('Save')
