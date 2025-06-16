from flask import render_template,flash, redirect,Blueprint, session,url_for, current_app,send_from_directory,request
from flask_login import login_required
from .forms.search_from import SearchForm,DetailForm,NewsFeedForm,SearchEmp_Id,AssetForm
from .models.Admin_models import Admin
from . import db
from .models.emp_detail_models import Employee,Asset
from .models.family_models import FamilyDetails
from .models.prev_com import PreviousCompany
from .models.education import UploadDoc, Education
from .models.attendance import Punch, LeaveApplication,LeaveBalance
from .models.news_feed import NewsFeed
from .forms.attendance import MonthYearForm,BalanceUpdateForm
from .models.signup import Signup
from datetime import datetime
import calendar
from werkzeug.security import generate_password_hash
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from werkzeug.utils import secure_filename
import os
from .common import asset_email,update_asset_email
from .forms.signup_form import SignUpForm
from .forms.Emp_details import Employee_Details


hr=Blueprint('hr',__name__)


@hr.route('/hr_dashbord',methods=['GET','POST'])
@login_required
def hr_dashbord():
    today = datetime.today()
    current_day = today.day
    current_month = today.month

    employees_with_anniversaries = Signup.query.filter(
        db.extract('month', Signup.doj) == current_month,
        db.extract('day', Signup.doj) == current_day
    ).all()
    

    employees_with_birthdays = Employee.query.filter(
        db.extract('month', Employee.dob) == current_month,
        db.extract('day', Employee.dob) == current_day
    ).all()

    return render_template('HumanResource/hr_dashboard.html',
                           employees_with_anniversaries=employees_with_anniversaries,
                           employees_with_birthdays=employees_with_birthdays)
   

 



@hr.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = SearchForm()
    if form.validate_on_submit():
        circle = form.circle.data
        emp_type = form.emp_type.data

        # Query Signup model based on circle and emp_type
        signups = Signup.query.filter_by(circle=circle, emp_type=emp_type).all()

        if not signups:
            flash('No matching entries found', category='error')
            return redirect(url_for('hr.search'))

        # Get email addresses from Signup model
        emails = [signup.email for signup in signups]
        
        # Query Admin model based on email addresses
        admins = Admin.query.filter(Admin.email.in_(emails)).all()

        if not admins:
            flash('No matching entries found in Admin records', category='error')
            return redirect(url_for('hr.search'))

        session['admin_emails'] = emails
        session['circle'] = circle
        session['emp_type'] = emp_type

        return redirect(url_for('hr.search_results'))

    return render_template('HumanResource/search_form.html', form=form)


@hr.route('/search_results', methods=['GET'])
@login_required
def search_results():
    if 'admin_emails' not in session:
        return redirect(url_for('hr.search'))

    emails = session['admin_emails']
    circle = session['circle']
    emp_type = session['emp_type']
 
    # Retrieve Admin details based on email
    admins = Admin.query.filter(Admin.email.in_(emails)).all()

    detail_form = DetailForm()
    detail_form.user.choices = [(admin.id, admin.first_name) for admin in admins]

    return render_template('HumanResource/search_result.html', admins=admins, circle=circle, emp_type=emp_type, form=detail_form)


@hr.route('/view_details', methods=['GET', 'POST'])
@login_required
def view_details():
    form = DetailForm()
    form.user.choices = [(admin.id, admin.first_name) for admin in Admin.query.all()] 

    if form.validate_on_submit():
        user_id = form.user.data
        detail_type = form.detail_type.data

        
        session['viewing_user_id'] = user_id
        session['viewing_detail_type'] = detail_type

        
        return redirect(url_for('hr.display_details'))

    return render_template('HumanResource/details.html', form=form)


@hr.route('/display_details', methods=['GET', 'POST'])
@login_required
def display_details():
    form = MonthYearForm()
    user_id = session.get('viewing_user_id')
    detail_type = session.get('viewing_detail_type')
    print(detail_type)

    if not user_id or not detail_type:
        return redirect(url_for('hr.view_details'))

    admin = Admin.query.get(user_id)
    
    details = None

    if form.validate_on_submit():
        month = int(form.month.data)
        year = int(form.year.data)
    else:
        month = datetime.now().month
        year = datetime.now().year

    if detail_type == 'Family Details':
        details = FamilyDetails.query.filter_by(admin_id=user_id).all()
    elif detail_type == 'Previous_company':
        details = PreviousCompany.query.filter_by(admin_id=user_id).all()
    elif detail_type == 'Employee Details':
        
        details = Employee.query.filter_by(admin_id=user_id).all()
        
    elif detail_type == 'Education':
        details = Education.query.filter_by(admin_id=user_id).all()
    elif detail_type == 'Attendance':
        num_days = calendar.monthrange(year, month)[1]
        details = [
            {
                'punch_date': f'{year}-{month:02d}-{day:02d}',
                'punch_in': '',
                'punch_out': '',
                'is_wfh': ''  # Default value
            } for day in range(1, num_days + 1)
        ]

        punches = Punch.query.filter(
            Punch.punch_date.between(f'{year}-{month:02d}-01', f'{year}-{month:02d}-{num_days}')
        ).filter_by(admin_id=user_id).all()

        for punch in punches:
            for detail in details:
                if detail['punch_date'] == punch.punch_date.strftime('%Y-%m-%d'):
                    detail['punch_in'] = punch.punch_in
                    detail['punch_out'] = punch.punch_out
                    detail['is_wfh'] = 'Yes' if punch.is_wfh else ''

    elif detail_type == 'Document':
        details = UploadDoc.query.filter_by(admin_id=user_id).all()
    elif detail_type == 'Leave Details':
        details = LeaveApplication.query.filter_by(admin_id=user_id).all()   
    

    if admin is None:
        return redirect(url_for('hr.view_details'))

    return render_template('HumanResource/details.html', admin=admin, details=details, detail_type=detail_type, selected_month=month, selected_year=year, form=form, datetime=datetime)





# for update leave balance search
@hr.route('/employee_list', methods=['GET', 'POST'])
@login_required
def employee_list():
    form = SearchForm()
    employees = []

    if form.validate_on_submit():
        emp_type = form.emp_type.data
        circle = form.circle.data

       
        session['emp_type'] = emp_type
        session['circle'] = circle

        
        employees = Signup.query.filter_by(emp_type=emp_type, circle=circle).all()

    else:
        
        emp_type = session.get('emp_type')
        circle = session.get('circle')

        if emp_type and circle:
            employees = Signup.query.filter_by(emp_type=emp_type, circle=circle).all()

    return render_template('HumanResource/emp_list.html', form=form, employees=employees)


@hr.route('/leave_balance/<int:employee_id>', methods=['GET', 'POST'])
def leave_balance(employee_id):
    """
    Display and update the leave balance for an employee by employee_id.
    """
    try:
        
        leave_balance = LeaveBalance.query.filter_by(signup_id=employee_id).first()
        employee = Signup.query.get(employee_id)  # Fetch employee instead of admin

        if leave_balance is None or employee is None:
            flash('Leave balance or employee not found for the given employee ID.', 'error')
            return redirect(url_for('hr.employee_list'))

        form = BalanceUpdateForm()

        if request.method == 'POST' and form.validate_on_submit():
            
            if form.personal_leave_balance.data is not None:
                leave_balance.privilege_leave_balance = form.personal_leave_balance.data
                print(form.personal_leave_balance.data)

            if form.casual_leave_balance.data is not None:
                leave_balance.casual_leave_balance = form.casual_leave_balance.data

            try:
                db.session.commit()
                flash('Leave balance updated successfully!', 'success')
            except Exception as e:
                flash(f"Database commit failed: {e}", 'error')

            return redirect(url_for('hr.leave_balance', employee_id=employee_id))
        

        # Pre-fill form values when loading the page
        if request.method == 'GET':
            form.personal_leave_balance.data = leave_balance.privilege_leave_balance
            form.casual_leave_balance.data = leave_balance.casual_leave_balance

        return render_template(
            'HumanResource/update_leave_balance.html',
            form=form,
            leave_balance=leave_balance,
            employee=employee  # Pass employee to the template
        )

    except Exception as e:
        flash(f"An error occurred: {e}", 'error')
        return redirect(url_for('hr.employee_list'))



@hr.route('/news_feed/add', methods=['GET', 'POST'])
@login_required
def add_news_feed():
    form = NewsFeedForm()
    if form.validate_on_submit():
        file = form.file.data
        file_path = None
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

       
        news_feed = NewsFeed(
            title=form.title.data,
            content=form.content.data,
            file_path=filename if file else None,
            circle=form.circle.data,
            emp_type=form.emp_type.data
        )
        db.session.add(news_feed)
        db.session.commit()
        flash('News feed added successfully!', 'success')
        return redirect(url_for('hr.add_news_feed'))

    return render_template('HumanResource/add_news_feed.html', form=form)



@hr.route('/news_feed/<int:news_feed_id>')
@login_required
def view_news_feed(news_feed_id):
    news_feed = NewsFeed.query.get_or_404(news_feed_id)
    return render_template('employee/view_news_feed.html', news_feed=news_feed)



@hr.route('/uploads/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

   


@hr.route('/search_employee', methods=['GET', 'POST'])
@login_required
def search_employee():
    form = SearchEmp_Id()
    employee = None

    if form.validate_on_submit():
        emp_id = form.emp_id.data
        employee = Signup.query.filter_by(emp_id=emp_id).first()

        if employee is None:
            flash('Employee not found!', 'danger')
        else:
            return render_template('HumanResource/asset_search.html', form=form, employee=employee)

    return render_template('HumanResource/asset_search.html', form=form, employee=employee)


@hr.route('/add_asset/<int:admin_id>', methods=['GET', 'POST'])
@login_required
def add_asset(admin_id):
    asset_form = AssetForm()
    employee = Admin.query.get(admin_id)

    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for('hr.search_employee'))  # Redirect if employee does not exist

    if asset_form.validate_on_submit():
        uploaded_filenames = []
        if asset_form.images.data:
            for file in asset_form.images.data:
                if file.filename:  # Ensure the file is not empty
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    uploaded_filenames.append(filename)

        new_asset = Asset(
            name=asset_form.name.data,
            description=asset_form.description.data,
            admin_id=employee.id,
            issue_date=asset_form.issue_date.data,
            return_date=asset_form.return_date.data if asset_form.return_date.data else None,
            remark=asset_form.remark.data  # ✅ Save the remark field
        )
        new_asset.set_image_files(uploaded_filenames)  # ✅ Store images as a comma-separated string

        db.session.add(new_asset)
        db.session.commit()
        flash('Asset added successfully!', 'success')
        asset_email(employee.email, employee.first_name)

        return redirect(url_for('hr.add_asset', admin_id=admin_id))

    assets = employee.assets  # ✅ Get employee assets

    return render_template(
        'HumanResource/assets.html',
        asset_form=asset_form,
        employee=employee,
        assets=assets
    )

@hr.route('/update_asset/<int:asset_id>', methods=['GET', 'POST'])
@login_required
def update_asset(asset_id):
    asset = Asset.query.get(asset_id)
    if not asset:
        flash("Asset not found.", "danger")
        return redirect(url_for('hr.add_asset', admin_id=1))  # Redirect to a safe page

    asset_form = AssetForm()

    if request.method == 'GET':
        asset_form.name.data = asset.name
        asset_form.description.data = asset.description
        asset_form.issue_date.data = asset.issue_date
        asset_form.return_date.data = asset.return_date
        asset_form.remark.data = asset.remark  # ✅ Pre-fill the remark field

    if asset_form.validate_on_submit():
        uploaded_filenames = asset.get_image_files()  # ✅ Keep existing images

        if asset_form.images.data:
            for file in asset_form.images.data:
                if file.filename:  # ✅ Ensure file is not empty
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    uploaded_filenames.append(filename)

        asset.name = asset_form.name.data
        asset.description = asset_form.description.data
        asset.set_image_files(uploaded_filenames)  # ✅ Store updated images
        asset.issue_date = asset_form.issue_date.data
        asset.return_date = asset_form.return_date.data if asset_form.return_date.data else None
        asset.remark = asset_form.remark.data  # ✅ Update remark field

        db.session.commit()
        flash('Asset updated successfully!', 'success')
        update_asset_email(asset.admin.email, asset.admin.first_name)

        return redirect(url_for('hr.add_asset', admin_id=asset.admin_id))

    return render_template(
        'HumanResource/assets_update.html',
        asset_form=asset_form,
        asset=asset
    )




@hr.route('/update_Signup', methods=['GET', 'POST'])
@login_required
def update_signup():
    form = SearchForm()
    employees = []

    if form.validate_on_submit():
        emp_type = form.emp_type.data
        circle = form.circle.data

       
        session['emp_type'] = emp_type
        session['circle'] = circle

        
        employees = Signup.query.filter_by(emp_type=emp_type, circle=circle).all()

    else:
        
        emp_type = session.get('emp_type')
        circle = session.get('circle')

        if emp_type and circle:
            employees = Signup.query.filter_by(emp_type=emp_type, circle=circle).all()

    return render_template('HumanResource/update_sighnup.html', form=form, employees=employees)


@hr.route('/edit_signup/<string:email>', methods=['GET', 'POST'])
@login_required
def edit_signup(email):
    employee = Signup.query.filter_by(email=email).first_or_404()
    form = SignUpForm(obj=employee)

    # Disable unique field validators temporarily
    form.email.validators = [DataRequired(), Email()]
    form.emp_id.validators = [DataRequired(), Length(max=10)]
    form.mobile.validators = [DataRequired(), Length(min=10, max=10)]

    if form.validate_on_submit():
        if form.password.data:
            employee.password = generate_password_hash(form.password.data)
        
        employee.emp_id = form.emp_id.data
        employee.first_name = form.first_name.data
        employee.doj = form.doj.data
        employee.mobile = form.mobile.data
        employee.circle = form.circle.data
        employee.emp_type = form.emp_type.data

        db.session.commit()
        flash('Employee record updated successfully.', 'success')
        return redirect(url_for('hr.update_signup'))

    return render_template('HumanResource/edit_signup.html', form=form, email=email)




@hr.route('/delete_signup/<string:email>', methods=['POST'])
@login_required
def delete_signup(email):
    print(f"[DEBUG] Request to delete: {email}")
    employee = Signup.query.filter_by(email=email).first()
    if not employee:
        print("[DEBUG] No employee found.")
        flash('Employee not found.', 'error')
        return redirect(url_for('hr.update_signup'))

    db.session.delete(employee)
    db.session.commit()
    print("[DEBUG] Deleted successfully.")
    flash(f'Employee {email} deleted successfully.', 'success')
    return redirect(url_for('hr.update_signup'))
