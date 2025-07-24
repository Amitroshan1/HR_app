from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, session
from .models.Admin_models import Admin
from .models.emp_detail_models import Employee
from flask_login import login_user, login_required, logout_user, current_user
from .forms.signup_form import SelectRoleForm
from datetime import datetime, timedelta, date
from .models.attendance import Punch
from .models.manager_model import ManagerContact
from .models.news_feed import NewsFeed
from .models.emp_detail_models import Asset
from .models.query import Query
from .models.signup import Signup
from werkzeug.security import check_password_hash, generate_password_hash
from . import db, login_manager
from .forms.manager import ChangePasswordForm
import os
import binascii
from .auth_helper import refresh_access_token
from datetime import datetime
import requests
from .models.manager_model import ManagerContact
from .utility import get_user_working_summary








auth = Blueprint('auth', __name__)

import logging

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


@auth.app_errorhandler(401)
def unauthorized_error(error):
    logger.error(f"Unauthorized access attempt: {error}")
    flash('You need to be logged in to access this page.', 'error')
    return redirect(url_for('auth.login'))


# Function to generate nonce
def generate_nonce():
    return binascii.hexlify(os.urandom(16)).decode()


# Redirect user to Microsoft OAuth2 login page
@auth.route('/login')
def login():
    params = {
        "client_id": current_app.config["OAUTH2_CLIENT_ID"],
        "response_type": "code",
        "redirect_uri": current_app.config["OAUTH2_REDIRECT_URI"],
        "scope": "openid email profile offline_access https://graph.microsoft.com/mail.send",
        "response_mode": "query"
    }
    auth_url = f"{current_app.config['MICROSOFT_AUTH_URL']}?{requests.compat.urlencode(params)}"
    logger.info(f"Redirecting user to OAuth login: {auth_url}")
    return redirect(auth_url)


# Handle OAuth2 callback from Microsoft
@auth.route('/callback')
def callback():
    code = request.args.get("code")
    if not code:
        logger.error("Authentication failed, no code received in callback")
        flash("Authentication failed", "danger")
        return redirect(url_for("auth.login"))

    # Exchange authorization code for access token
    token_data = {
        "client_id": current_app.config['OAUTH2_CLIENT_ID'],
        "client_secret": current_app.config['OAUTH2_CLIENT_SECRET'],
        "code": code,
        "redirect_uri": current_app.config['OAUTH2_REDIRECT_URI'],
        "grant_type": "authorization_code"
    }

    logger.info(f"Exchanging authorization code for access token: {token_data}")
    token_response = requests.post(current_app.config['MICROSOFT_TOKEN_URL'], data=token_data)
    token_json = token_response.json()

    if "access_token" not in token_json:
        logger.error(f"Failed to retrieve access token. Response: {token_json}")
        flash("Failed to retrieve access token", "danger")
        return redirect(url_for("auth.login"))

    access_token = token_json["access_token"]
    refresh_token = token_json.get("refresh_token")
    expires_in = token_json.get("expires_in", 3600)  # Default to 1 hour

    # Fetch user details from Microsoft Graph API
    headers = {"Authorization": f"Bearer {access_token}"}
    logger.info("Fetching user details from Microsoft Graph API")
    user_response = requests.get(current_app.config['MICROSOFT_USER_INFO_URL'], headers=headers)
    user_json = user_response.json()

    if "id" not in user_json:
        logger.error(f"Failed to fetch user details. Response: {user_json}")
        flash("Failed to fetch user details", "danger")
        return redirect(url_for("auth.login"))

    oauth_id = user_json["id"]
    email = user_json["mail"] or user_json["userPrincipalName"]
    first_name = user_json.get("givenName", "")

    # Check if user exists in the database
    admin = Admin.query.filter_by(oauth_id=oauth_id).first()

    if not admin:
        # If user doesn't exist, create a new one
        admin = Admin(
            oauth_id=oauth_id,
            email=email,
            first_name=first_name,
            oauth_provider="microsoft",
            oauth_token=access_token,
            oauth_refresh_token=refresh_token,
            oauth_token_expiry=datetime.now()
        )
        db.session.add(admin)
        logger.info(f"New admin user created: {email}")
    else:
        # Update tokens for existing user
        admin.oauth_token = access_token
        admin.oauth_refresh_token = refresh_token
        admin.oauth_token_expiry = datetime.now() + timedelta(seconds=expires_in)
        logger.info(f"Existing admin user updated: {email}")

    db.session.commit()

    # Log the user in
    login_user(admin)
    flash("Login successful!", "success")
    return redirect(url_for("auth.select_role"))  # Redirect to dashboard


def refresh_access_token(admin):
    if not admin.oauth_refresh_token:
        logger.error("No refresh token available, user needs to log in again")
        flash("Session expired. Please log in again.", "danger")
        return None

    token_data = {
        "client_id": current_app.config['OAUTH2_CLIENT_ID'],
        "client_secret": current_app.config['OAUTH2_CLIENT_SECRET'],
        "refresh_token": admin.oauth_refresh_token,
        "grant_type": "refresh_token"
    }

    token_response = requests.post(current_app.config['MICROSOFT_TOKEN_URL'], data=token_data)
    token_json = token_response.json()

    if "access_token" not in token_json:
        logger.error(f"Failed to refresh token: {token_json}")
        flash("Session expired. Please log in again.", "danger")
        return None

    # Update admin's OAuth data in the database
    admin.oauth_token = token_json["access_token"]
    admin.oauth_refresh_token = token_json.get("refresh_token", admin.oauth_refresh_token)
    admin.oauth_token_expiry = datetime.now() + timedelta(seconds=token_json.get("expires_in", 3600))
    db.session.commit()

    return admin.oauth_token


def get_authenticated_headers(admin):
    """Ensure token is valid before making API requests."""
    if admin.oauth_token_expiry and admin.oauth_token_expiry <= datetime.now():
        logger.info("Token expired, refreshing...")
        new_token = refresh_access_token(admin)
        if new_token:
            logger.info("Token refreshed successfully")
            return {"Authorization": f"Bearer {new_token}"}
        else:
            logger.error("Failed to refresh token, user must log in again")
            return None  # Indicate that the user must re-authenticate

    return {"Authorization": f"Bearer {admin.oauth_token}"}


@login_manager.user_loader
def load_admin(admin_id):
    return Admin.query.get(int(admin_id))


@auth.route('/select_role', methods=['GET', 'POST'])
@login_required
def select_role():
    form = SelectRoleForm()  # A form for selecting Emp_type and password

    if form.validate_on_submit():
        selected_role = form.emp_type.data  # Get the selected Emp_type
        entered_password = form.password.data  # Get the entered password  # Debugging print statement
        user = current_user  # Get the current user

        # Debugging logs
        current_app.logger.debug(f'User ID: {user.id}, Selected Role: {selected_role}')

        # Get the current user's email ID
        user_email = user.email  # Assuming the user model has an email attribute

        # Query the admin/signup record based on the user's email
        admin = Signup.query.filter_by(
            email=user_email).first()  # Debugging print statement to check if admin is fetched correctly

        if admin:
            # Check if the Emp_type matches the selected role
            if admin.emp_type == selected_role:
                # If the role matches, check if the password is correct
                if admin.check_password(entered_password):  # Assuming check_password is defined in the Signup model
                    # If password matches, redirect to the homepage for that role
                    return redirect(
                        url_for('auth.E_homepage'))  # Assuming E_homepage is defined correctly in your auth blueprint
                else:
                    flash('Incorrect password. Please try again.', category='error')
                    return redirect(url_for('auth.select_role'))  # Redirect to role selection page
            else:
                flash('The selected role does not match your assigned role. Please contact HR.', category='error')
                return redirect(url_for('auth.select_role'))  # Redirect to role selection page
        else:
            flash('Your email is not found in the system. Please contact HR.', category='error')
            return redirect(url_for('auth.select_role'))  # Redirect to role selection page

    # Debugging template rendering
    current_app.logger.debug('Rendering select_role.html')

    return render_template('employee/select_role.html', form=form)


@auth.route('/E_homepage')
@login_required
def E_homepage():
    emails_data = [
        email
        for manager in ManagerContact.query.all()
        for email in [manager.l1_email, manager.l2_email, manager.l3_email]
        if email
    ]
    flag = False
    if current_user.email in emails_data:
        flag = True
    # print("flag status: ", flag)

    # Get employee record for current user
    employee = Employee.query.filter_by(admin_id=current_user.id).first()
    data =get_user_working_summary(current_user.id, datetime.now().year, datetime.now().month)
    print(f"Working summary data: {data}")

    if not employee:
        flash("No employee record found for the current user.")
        return render_template("employee/E_homepage.html")

    # Get Signup record from email to get emp_type
    emp = Signup.query.filter_by(email=employee.email).first()
    if emp is None:
        flash("offical mail is not same in employee details,Plz contact HR.", "danger")
        return redirect(url_for('auth.logout'))


    count_new_queries = Query.query.filter_by(emp_type=emp.emp_type, status='New').count()

    # Get DOJ from Signup model
    DOJ = emp.doj if emp else None

    # Get today's punch-in and punch-out time
    today = date.today()
    punch = Punch.query.filter_by(admin_id=current_user.id, punch_date=today).first()
    punch_in_time = punch.punch_in if punch else None
    punch_out_time = punch.punch_out if punch else None

    # Get emp_type and circle from Signup model
    emp_type = emp.emp_type if emp else None
    circle = emp.circle if emp else None


    # Get manager contact information based on circle and emp_type
    manager_contact = ManagerContact.query.filter_by(circle_name=circle, user_type=emp_type).first()

    # Get news feeds based on circle and emp_type
    news_feeds = NewsFeed.query.filter(
        (NewsFeed.circle == circle) & (NewsFeed.emp_type == emp_type) |
        (NewsFeed.circle == 'All') & (NewsFeed.emp_type == 'All') |
        (NewsFeed.circle == circle) & (NewsFeed.emp_type == 'All') |
        (NewsFeed.circle == 'All') & (NewsFeed.emp_type == emp_type)
    ).order_by(NewsFeed.created_at.desc()).all()

    # Get queries relevant to emp_type
    all_queries = Query.query.all()
    queries_for_emp_type = [query for query in all_queries if emp_type in query.emp_type.split(',')]

    # Determine if there are any notifications for the current emp_type
    show_notification = bool(queries_for_emp_type)

    # Pass necessary data to the template
    return render_template("employee/E_homepage.html",
                           employee=employee,
                           punch_in_time=punch_in_time,
                           punch_out_time=punch_out_time,
                           manager_contact=manager_contact,
                           news_feeds=news_feeds,
                           DOJ=DOJ,
                           flag=flag,
                           data=data,  # Pass the working summary data
                           show_notification=show_notification,
                           queries_for_emp_type=queries_for_emp_type,
                           emp_type=emp_type, count_new_queries=count_new_queries)  # Pass emp_type to the template


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.select_role'))


@auth.route('/my_assets', methods=['GET'])
@login_required
def my_assets():
    emp_id = current_user.id

    assets = Asset.query.filter_by(admin_id=emp_id).all()

    if not assets:
        flash('No assets found for your account.', 'info')

    return render_template('employee/my_assets.html', assets=assets)


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        original_password = form.original_password.data
        new_password = form.new_password.data

        admin = Signup.query.filter_by(email=current_user.email).first()
        # Verify original password
        if current_user.email == admin.email:

            if not admin.check_password(original_password):
                flash('Original password is incorrect', 'danger')
                return redirect(url_for('auth.change_password'))

        # Update the password
        admin.set_password(new_password)
        db.session.commit()

        flash('Your password has been updated successfully', 'success')
        return redirect(url_for('auth.change_password'))  # Redirect to profile or wherever you like

    return render_template('profile/change_password.html', form=form)

@auth.app_context_processor
def inject_badge_counts():
    try:
        count_new_claims = ExpenseLineItem.query.filter_by(status='New').count()
        count_new_wfhs = WorkFromHome.query.filter_by(status='New').count()
    except Exception as e:
        # Fallback to 0 if DB is not ready or error occurs
        current_app.logger.warning(f"Badge count injection failed: {e}")
        count_new_claims = 0
        count_new_wfhs = 0

    return dict(
        count_new_claims=count_new_claims,
        count_new_wfhs=count_new_wfhs
    )
