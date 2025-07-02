from flask_wtf import FlaskForm
from wtforms import FileField, StringField, DateField, TextAreaField, FloatField, SelectField, FieldList, FormField, IntegerField
from wtforms.validators import DataRequired, Length,Optional

class ExpenseItemForm(FlaskForm):
    sr_no = IntegerField('Sr. No.', validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    purpose = TextAreaField('Purpose/Description', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    currency = SelectField('Currency', choices=[('INR', 'INR'), ('USD', 'USD'), ('EUR', 'Euro')], validators=[DataRequired()])
    Attach_file = FileField("Attach File",validators=[Optional()]) # Assuming file path or name is stored as a string
    status = StringField('Status', default='Pending')  # Added status field



class ExpenseClaimForm(FlaskForm):
    employee_name = StringField('Employee Name', validators=[DataRequired()])
    designation = StringField('Designation', validators=[DataRequired()])
    emp_id = StringField('Employee ID', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Length(max=120)])
    project_name = StringField('Project Name', validators=[DataRequired()])
    country_state = StringField('Country/State', validators=[DataRequired()])
    travel_from_date = DateField('Travel From', validators=[DataRequired()])
    travel_to_date = DateField('Travel To', validators=[DataRequired()])
    expenses = FieldList(FormField(ExpenseItemForm), min_entries=1)
