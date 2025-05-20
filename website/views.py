from flask import render_template, request, flash, redirect,Blueprint, url_for, current_app as app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import os
from  .models.family_models import FamilyDetails
from .forms.family_details import Family_details
from . import views
from .forms.Emp_details import Employee_Details
from .models.emp_detail_models import Employee
from . import db

views=Blueprint('views',__name__)


@views.route('/')
def home():
    return render_template('home.html')




