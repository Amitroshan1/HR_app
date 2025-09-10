from flask_wtf import FlaskForm
from wtforms import *
from wtforms.validators import *
from flask_wtf.file import FileAllowed


class EducationForm(FlaskForm):

    qualification = StringField('Qualification *', 
                         validators=[DataRequired()], 
                         render_kw={"placeholder": "Enter your Qualification"})
    
    institution = StringField('Institution Name *', 
                         validators=[DataRequired()], 
                         render_kw={"placeholder": "Enter your Institution"})
    
    board = StringField('University/Board *', 
                         validators=[DataRequired()], 
                         render_kw={"placeholder": "Enter your University/Board"})
    
    start = DateField("From Date *",format='%Y-%m-%d', validators=[InputRequired()])

    end = DateField("To Date *",format='%Y-%m-%d', validators=[InputRequired()])

    marks = StringField('Marks Percentage/ CGPA *', 
                        validators=[DataRequired()], 
                        render_kw={"placeholder": "Enter your Percentage/CGPA"})
    
    doc_file = FileField('Certificate *', 
                         validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf', 'txt', 'doc', 'docx', 'xls', 'xlsx'], 'Allowed file types: jpg, png, jpeg, pdf, txt, doc, docx, xls, xlsx')])
    
    submit = SubmitField('Submit')





class UploadDocForm(FlaskForm):
    # Aadhaar
    aadhaar_front = FileField('Aadhaar Card (Front)', 
                              validators=[FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 
                              'Allowed file types: jpg, jpeg, png, pdf')])
    aadhaar_back = FileField('Aadhaar Card (Back)', 
                             validators=[FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 
                             'Allowed file types: jpg, jpeg, png, pdf')])

    # PAN
    pan_front = FileField('PAN Card (Front)', 
                          validators=[FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 
                          'Allowed file types: jpg, jpeg, png, pdf')])
    pan_back = FileField('PAN Card (Back)', 
                         validators=[FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 
                         'Allowed file types: jpg, jpeg, png, pdf')])

    # Appointment Letter
    appointment_letter = FileField('Appointment Letter', 
                                   validators=[FileAllowed(['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx'], 
                                   'Allowed file types: jpg, jpeg, png, pdf, doc, docx')])

    # Passbook
    passbook_front = FileField('Passbook/Cheque Book', 
                               validators=[FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 
                               'Allowed file types: jpg, jpeg, png, pdf')])
    

    submit = SubmitField('Upload Documents')


    
        

 
    
    



    

    
    
    


