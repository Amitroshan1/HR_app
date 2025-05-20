from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from datetime import timedelta
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
    """ Updates leave balances for employees every 6 months. """
    from .models.attendance import LeaveBalance
    from .models.Admin_models import Admin  
    from .models.signup import Signup 

    with scheduler.app.app_context():
        leave_balances = LeaveBalance.query.all()
        if not leave_balances:
            print("No leave balances found in the database.")
            return

        for balance in leave_balances:
            admin = Admin.query.filter_by(id=balance.admin_id).first() 
            signup = Signup.query.filter_by(email=admin.email).first()
            if admin and signup.Doj:
                doj = signup.Doj
                six_months_after_doj = doj + timedelta(days=6*30) 
                
                if datetime.now().date() >= six_months_after_doj:
                    balance.privilege_leave_balance += 1.08
                    balance.casual_leave_balance += 0.67

        try:
            db.session.commit()
            print("Database commit successful.")
        except Exception as e:
            print(f"Database commit failed: {str(e)}")



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

    app.register_blueprint(profile, url_prefix='/')
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(Admin_auth, url_prefix='/')
    app.register_blueprint(hr, url_prefix='/')
    app.register_blueprint(manager_bp, url_prefix='/')
    app.register_blueprint(Accounts, url_prefix='/')
    app.register_blueprint(auth_helper, url_prefix='/')

    # Scheduler job
    scheduler.add_job(
    id='update_leave_balances',
    func=update_leave_balances,
    trigger='cron',
    day='25-31',      # Runs only between the 25th and 31st
    hour=17,
    minute=55,
    day_of_week='mon' # Ensures it runs only on Mondays
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
