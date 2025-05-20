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
    doc_name = StringField('Document Name *', 
                           validators=[DataRequired()], 
                           render_kw={"placeholder": "Enter Name of Document"})

    doc_number = StringField('Document Number *', 
                             validators=[DataRequired()], 
                             render_kw={"placeholder": "Enter Document Number"})

    issue_date = DateField("Issue Date *", 
                           format='%Y-%m-%d', 
                           validators=[InputRequired()])

    doc_file = FileField('Document *', 
                         validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf', 'txt', 'doc', 'docx', 'xls', 'xlsx'], 
                                                 'Allowed file types: jpg, png, jpeg, pdf, txt, doc, docx, xls, xlsx')])

    submit = SubmitField('Upload')

    
        

 
    
    



    

    
    
    


