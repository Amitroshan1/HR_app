from flask import Blueprint, render_template, request, redirect, url_for, flash
from . import db
from datetime import datetime, timedelta
import random
import pytz
from .forms.otp import RequestOTPForm,ResetPasswordForm,VerifyOTPForm
from .models.otp import OTP
from .models.signup import Signup
from werkzeug.security import generate_password_hash
from .common import verify_oauth2_and_send_email
from flask_login import current_user, login_required



forgot_password = Blueprint('forgot_password',__name__)




def send_otp_email(recipient_email, otp):
    subject = "Your OTP Code"
    body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h2 style="color: #2c3e50;">Password Reset OTP</h2>
                <p>Your <strong>OTP</strong> for password reset is:</p>
                <p style="font-size: 24px; font-weight: bold; color: #d35400;">{otp}</p>
                <p>This OTP is valid for <strong>10 minutes</strong> only.</p>
                <p style="color: #e74c3c;"><strong>Please do not share this code with anyone.</strong></p>
                </div>
            </body>
            </html>
            """

    # Get an Admin user with valid refresh token
    admin_sender = "nphatak@saffotech.com"
    

    return verify_oauth2_and_send_email(admin_sender, subject, body, recipient_email)
#   verify_oauth2_and_send_email(user, subject, body, recipient_email, cc_emails=None)


@forgot_password.route('/forgot_password', methods=['GET'])
@login_required
def forgot_password_reset():

    # 1. Get current logged-in user’s email
    email = current_user.email  # or: session["email"]

    # 2. Generate OTP
    otp_code = f"{random.randint(100000, 999999)}"

    try:
        # 3. Send OTP
        email_sent = send_otp_email(email, otp_code)

        if email_sent:
            # 4. Save OTP in database
            otp = OTP(email=email, otp_code=otp_code)
            db.session.add(otp)
            db.session.commit()

            # 5. Redirect to verification page
            flash("OTP has been sent to your email.", "success")
            return redirect(url_for('forgot_password.verify_otp', email=email))

        else:
            flash("Failed to send OTP. Please try again.", "danger")
            return redirect(url_for('auth.select_role'))

    except Exception:
        flash("Error sending OTP. Please try again later.", "danger")
        return redirect(url_for('auth.select_role'))



@forgot_password.route('/verify_otp/<email>',methods=['GET','POST'])
def verify_otp(email):
    form = VerifyOTPForm()
    if form.validate_on_submit():
        user_otp = form.otp.data
        india_timezone = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(india_timezone)
        ten_minutes_ago = now_ist - timedelta(minutes=10)

        otp_record = OTP.query.filter_by(email=email, otp_code=user_otp, is_used=False).filter(OTP.created_at >= ten_minutes_ago).first()
        if otp_record:
            otp_record.is_used = True
            db.session.commit()
            flash("OTP verified Please reset your password.",'success')
            return redirect(url_for('forgot_password.reset_password', email=email))
        else:
            flash("Invalid or expired OTP","danger")
    return render_template('OTP/verify.html', form=form)




@forgot_password.route('/reset-password/<email>', methods = ['GET','POST'])
def reset_password(email):
    form = ResetPasswordForm()
    if form.validate_on_submit():
        new_password = form.new_password.data
        hashed_password = generate_password_hash(new_password)
        user = Signup.query.filter_by(email = email).first()
        if user:
            user.password = hashed_password
            db.session.commit()

            flash("Your password has been updated.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash("User not found.", "danger")
    return render_template('OTP/reset.html', form=form)