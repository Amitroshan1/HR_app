
from wtforms import *
from flask_wtf import FlaskForm
from wtforms import ValidationError
from wtforms.validators import DataRequired,Optional as opt
from datetime import datetime



class PunchForm(FlaskForm):
    punch_in = SubmitField('Punch In')
    punch_out = SubmitField('Punch Out')
    lat = HiddenField()
    lon = HiddenField()
    wfh = BooleanField('Work From Home')



class LocationForm(FlaskForm):
    name = StringField('Location Name', validators=[DataRequired()])
    latitude = FloatField('Latitude', validators=[DataRequired()])
    longitude = FloatField('Longitude', validators=[DataRequired()])
    radius = FloatField('Radius (meters)', default=100)
    submit = SubmitField('Add Location')



class MonthYearForm(FlaskForm):
    month = SelectField('Month', choices=[(str(i), i) for i in range(1, 13)], validators=[DataRequired()])
    year = SelectField('Year', choices=[(str(i), i) for i in range(2000, datetime.now().year + 1)], validators=[DataRequired()])




class LeaveForm(FlaskForm):
    leave_type = SelectField('Leave Type',
                             choices=[('', 'Select Leave Option'),
                                      ('Privilege Leave', 'Privilege Leave'),
                                      ('Casual Leave', 'Casual Leave'),
                                      ("Half Day Leave", "Half Day Leave"),
                                      ('Compensatory Leave', 'Compensatory Leave'),
                                      ],
                             validators=[DataRequired()])
    reason= StringField('Reason For Leave * ', 
                         validators=[DataRequired()], 
                         render_kw={"placeholder": "Reason For Leave.... "})
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()])

    submit = SubmitField('Apply for Leave')






class BalanceUpdateForm(FlaskForm):
    personal_leave_balance = FloatField(
        'Personal Leave Balance', 
        validators=[opt()]
    )
    casual_leave_balance = FloatField(
        'Casual Leave Balance', 
        validators=[opt()]
    )
    submit = SubmitField('Update')

    # Add custom validator for FloatField
    def validate_personal_leave_balance(self, field):
        if not isinstance(field.data, (int, float)):
            raise ValidationError("Personal Leave Balance must be a number.")

    def validate_casual_leave_balance(self, field):
        if not isinstance(field.data, (int, float)):
            raise ValidationError("Casual Leave Balance must be a number.")


