from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, login_required, logout_user, current_user
from website import db
from .models.signup import Signup
from .forms.signup_form import SignUpForm  # Ensure the correct form is imported
from .models.attendance import LeaveBalance

Admin_auth = Blueprint('Admin_auth', __name__)

@Admin_auth.route("/sign-up", methods=["GET", "POST"])
def admin_sign_up():
    form = SignUpForm()

    if form.validate_on_submit():
        try:
            # Collect form data
            email = form.email.data
            first_name = form.first_name.data
            mobile = form.mobile.data
            emp_id = form.emp_id.data
            user_type = form.emp_type.data
            circle = form.circle.data
            password = form.password.data
            confirm_password = form.confirm_password.data
            
            # Check if the email or employee ID already exists in the database
            if Signup.query.filter_by(email=email).first():
                flash('Email is already registered!', category='error')
                return redirect(url_for('Admin_auth.admin_sign_up'))

            if Signup.query.filter_by(emp_id=emp_id).first():
                flash('Employee ID is already in use!', category='error')
                return redirect(url_for('Admin_auth.admin_sign_up'))

            # Check if passwords match
            if password != confirm_password:
                flash('Passwords do not match!', category='error')
                return redirect(url_for('Admin_auth.admin_sign_up'))

            # Create a new Signup user and hash the password
            new_signup = Signup(
                email=email,
                first_name=first_name,
                mobile=mobile,
                emp_id=emp_id,
                emp_type=user_type,
                circle=circle,
                doj=form.doj.data
            )
            new_signup.set_password(password)  # Using set_password to hash the password

            # Add to session and commit to get the signup ID
            db.session.add(new_signup)
            db.session.commit()

            # Create a LeaveBalance record for the new signup
            new_leave_balance = LeaveBalance(signup_id=new_signup.id, privilege_leave_balance=0.0, casual_leave_balance=0.0)

            # Add leave balance to session and commit
            db.session.add(new_leave_balance)
            db.session.commit()

            # Flash a success message and redirect
            flash('Account created successfully!', category='success')
            return redirect(url_for('Admin_auth.admin_sign_up'))

        except Exception as e:
            # Rollback the transaction in case of error and flash the error message
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", category='error')

    else:
        # Handle form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", category='error')

    return render_template("admin/AdminSign_up.html", form=form)
