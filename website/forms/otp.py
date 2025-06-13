from flask_wtf import FlaskForm
from wtforms import StringField,SubmitField,PasswordField
from wtforms.validators import DataRequired,Email,Length


class RequestOTPForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(),Email()])
    submit = SubmitField('Send OTP')

class VerifyOTPForm(FlaskForm):
    otp = StringField('Enter OTP', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Verify OTP')

class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[DataRequired()])
    submit = SubmitField('Reset Password')