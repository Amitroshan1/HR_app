from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from datetime import datetime,timedelta
from flask_wtf.csrf import CSRFProtect
from flask_apscheduler import APScheduler
from urllib.parse import urlparse, urljoin
import datetime
from authlib.integrations.flask_client import OAuth
from datetime import timedelta, datetime
from pytz import timezone
import logging
import os
from flask_session import Session 
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta






dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

# Initialize extensions
oauth = OAuth()
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()
csrf = CSRFProtect()
scheduler = APScheduler()
Session = Session()


class Config:
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=50)

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target)) 
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc



def update_leave_balances():
    """ Updates leave balances monthly for employees after 6 months of joining. """
    from .models.attendance import LeaveBalance
    from .models.Admin_models import Admin  
    from .models.signup import Signup 

    with scheduler.app.app_context():
        leave_balances = LeaveBalance.query.all()
        if not leave_balances:
            print("No leave balances found in the database.")
            return

        today = datetime.now().date()

        for balance in leave_balances:
            signup = Signup.query.filter_by(id=balance.signup_id).first()
            # print(f"Processing leave balance for signup ID: {balance.signup_id}, Admin ID: {signup.email if signup else 'None'}")
            admin = Admin.query.filter_by(email=signup.email).first() if signup else None
            # print(f"Found admin: {admin.email if admin else 'None'} for signup ID: {signup.id if signup else 'None'}")  
            if not admin:
                continue  # Skip if admin not found

            if not signup or not signup.doj:
                continue  # Skip if signup or DoJ not found

            doj = signup.doj

            # Skip if employee hasn't completed 6 months
            if today < doj + relativedelta(months=6):
                continue

            # If never updated, initialize to 6 months after DoJ
            if not balance.last_updated:
                balance.last_updated = doj + relativedelta(months=6)

            # Calculate how many full months passed since last update
            months_passed = (today.year - balance.last_updated.year) * 12 + (today.month - balance.last_updated.month)

            if months_passed >= 1:
                for _ in range(min(months_passed, 1)):

                    balance.privilege_leave_balance += 1.08
                    balance.casual_leave_balance += 0.67

                # Update last_updated to today to reflect actual update date
                balance.last_updated = today
                # print(f"Updated leave for: {signup.email}, Months: {months_passed}, New Last Updated: {today}")

        try:
            db.session.commit()
            print("Leave balances updated successfully.")
        except Exception as e:
            print(f"Database commit failed: {str(e)}")


from datetime import datetime, timedelta
import pytz

def send_reminder_emails():
    from .models.query import Query
    from .common import verify_oauth2_and_send_email
    
    

    # IST timezone
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    with scheduler.app.app_context():
        # Get all open queries
        queries = Query.query.filter_by(status='open').all()
        print(f"Found {len(queries)} open queries")

        for query in queries:
            # Make sure query.created_at is timezone-aware in IST
            if query.created_at.tzinfo is None:
                last_activity_time = ist.localize(query.created_at)
            else:
                last_activity_time = query.created_at.astimezone(ist)

            # Calculate time since last activity (query creation or reply)
            time_since_last_activity = now - last_activity_time
            

            # If 3 days or more have passed since last activity, send reminder to that particular employee's
            if time_since_last_activity >= timedelta(days=3):
                departments = query.emp_type.split(', ')
                

                # Assign department email (example)
                if 'Human Resource' in departments:
                    department_email = 'hr@saffotech.com'
                elif 'Accounts' in departments:
                    department_email = 'accounts@saffotech.com'
               

                cc = None

                admin_email = query.admin.email
                

                subject = f"Reminder: No response to query '{query.title}' in 3 days"
                body = f"""
                Query Title: {query.title}
                Department(s): {query.emp_type}
                Last Activity At: {last_activity_time.strftime('%Y-%m-%d %H:%M:%S')}
                
                This query has not received any reply or update within 3 days. Please respond ASAP.
                """

                verify_oauth2_and_send_email(admin_email, subject, body, department_email, cc)



def leave_reminder_email():
    from .models.attendance import LeaveApplication
    from .models.Admin_models import Admin
    from .models.signup import Signup
    from .models.manager_model import ManagerContact
    from .common import verify_oauth2_and_send_email

   

    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    with scheduler.app.app_context():
        leaves = LeaveApplication.query.filter_by(status="Pending").all()
        print(f"Found {len(leaves)} leaves..")
        for leave in leaves:

            if leave.created_at.tzinfo is None:
                last_activity_query_time = ist.localize(leave.created_at)
            else:
                last_activity_query_time = leave.created_at.astimezone(ist) #when qyery is create that time will store

            time_since_last_query_activity = now - last_activity_query_time
            # print(f"The leave_app id is {leave.id} and age since last activity: {time_since_last_query_activity}")
            if time_since_last_query_activity >= timedelta(days=3):
                user_email = leave.admin.email
                # print(f"successful get the user email {user_email}")
                signup_data = Signup.query.filter_by(email=user_email).first()
                # print(f"Successful got the signup data {signup_data}")
                if signup_data:
                    emp_type = signup_data.emp_type
                    circle = signup_data.circle
                    # print(f"Employee Type: {emp_type}")
                    # print(f"Circle: {circle}")
                else:
                    print("No signup data found.")
                    emp_type = None
                    circle = None
                manager_data = ManagerContact.query.filter_by(circle_name = circle,user_type=emp_type,).first()
                if manager_data:
                    l2_leader = manager_data.l2_email
                    l3_leader = manager_data.l3_email
                    # print(f"Get the data of l2 {l2_leader}")
                    # print(f"Get the data of l3 {l3_leader}")

                cc = l2_leader
                subject = f"Reminder: No response to leave application ' in 3 days"
                body = f"""
                Hello,

                This is a reminder that a leave application has been pending without any response or update for the past 3 days.

                Timely action on such requests ensures smooth workflow and employesatisfaction. Please review and take the necessary action as soon as possible.

                If you have already addressed this, kindly ignore this message.

                Thank you,
                HR & Admin Team
                """
                verify_oauth2_and_send_email(user_email, subject, body, l3_leader, [cc])
                
                
        

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URI")

# Check if critical env variables are set
    if not app.config['SECRET_KEY'] or not app.config['SQLALCHEMY_DATABASE_URI']:
        raise ValueError("Missing required environment variables. Check your .env file.")


# ✅ Flask-Session Configuration (MySQL)
    app.config['SESSION_TYPE'] = 'sqlalchemy'
    app.config['SESSION_SQLALCHEMY_TABLE'] = 'session'
    app.config['SESSION_SQLALCHEMY'] = db
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True  # Secure the session cookies
    app.config['SESSION_KEY_PREFIX'] = 'saffo_session_'
    app.config['SESSION_SERIALIZATION_FORMAT'] = "json"



    
  
    # OAuth2 Configuration
    app.config['SESSION_COOKIE_SECURE'] = True  
    app.config['SESSION_COOKIE_HTTPONLY'] = True

    app.config['OAUTH2_CLIENT_ID'] = os.getenv("OAUTH2_CLIENT_ID")
    app.config['OAUTH2_CLIENT_SECRET'] = os.getenv("OAUTH2_CLIENT_SECRET")
    app.config['OAUTH2_REDIRECT_URI'] = os.getenv("OAUTH2_REDIRECT_URI")
    app.config['OAUTH2_SCOPE'] = [
        "openid", "email", "profile", "offline_access",
        "https://graph.microsoft.com/mail.send",
        "https://graph.microsoft.com/User.Read"
    ]
    # Ensure required env variables are set
    if not all([app.config['OAUTH2_CLIENT_ID'], app.config['OAUTH2_CLIENT_SECRET'], app.config['OAUTH2_REDIRECT_URI']]):
        raise ValueError("Missing OAuth2 environment variables. Please check your .env file.")


    # ✅ Fix OAuth URLs
    app.config['MICROSOFT_AUTH_URL'] = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    app.config['MICROSOFT_TOKEN_URL'] = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    app.config['MICROSOFT_USER_INFO_URL'] = "https://graph.microsoft.com/v1.0/me"

    # Additional configurations
    app.config['UPLOAD_FOLDER'] = 'website/static/uploads'
    app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'png', 'jpeg', 'pdf', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'jfif'}
    app.config['WTF_CSRF_ENABLED'] = True

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    scheduler.init_app(app)
    Session.init_app(app)


    # Import models before initializing migrate
    from .models.Admin_models import Admin
    from .models.emp_detail_models import Employee
    from .models.family_models import FamilyDetails
    from .models.prev_com import PreviousCompany
    from .models.education import UploadDoc, Education
    from .models.attendance import Punch, LeaveBalance, LeaveApplication
    from .models.manager_model import ManagerContact
    from .models.query import Query, QueryReply
    from .models.signup import Signup
    from .models.news_feed import NewsFeed, PaySlip
    from .models.otp import OTP

    migrate.init_app(app, db)  # Now models are loaded, safe to initialize

    with app.app_context():
        db.create_all()

    # Initialize OAuth with the app
    oauth.init_app(app)

    # ✅ Fix OAuth registration
    oauth.register(
        name='microsoft',
        client_id=app.config['OAUTH2_CLIENT_ID'],
        client_secret=app.config['OAUTH2_CLIENT_SECRET'],
        access_token_url=app.config['MICROSOFT_TOKEN_URL'],
        authorize_url=app.config['MICROSOFT_AUTH_URL'],
        client_kwargs={'scope': " ".join(app.config['OAUTH2_SCOPE'])}
    )

    # Register blueprints
    from .views import views
    from .auth import auth
    from .Amdin_auth import Admin_auth
    from .profile import profile
    from .hr import hr
    from .Updatemanager import manager_bp
    from .Aoocunts import Accounts
    from .auth_helper import auth_helper
    from .otp import forgot_password

    app.register_blueprint(profile, url_prefix='/')
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(Admin_auth, url_prefix='/')
    app.register_blueprint(hr, url_prefix='/')
    app.register_blueprint(manager_bp, url_prefix='/')
    app.register_blueprint(Accounts, url_prefix='/')
    app.register_blueprint(auth_helper, url_prefix='/')
    app.register_blueprint(forgot_password, url_prefix='/')
    

    scheduler.add_job(
        id='update_leave_balances',
        func=update_leave_balances,
        trigger='cron',
        day='last',
        hour=8,
        minute=23,
    )


    scheduler.add_job(
        id='send_reminder_emails_job',
        func=send_reminder_emails,  # your function name here
        trigger='interval',
        days=3  # runs every day; adjust as needed
    )
    
    scheduler.add_job(
    id='leave_reminder_email()',
    func=leave_reminder_email,  # your function name here
    trigger='interval',
    days = 3 # runs every day; adjust as needed
)





    # After request hook to set cache control
    @app.after_request
    def add_header(response):
        response.cache_control.no_store = True
        return response

    # Start scheduler
    scheduler.start()

    return app

# ✅ Fix logging setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info("Flask application initialized successfully")