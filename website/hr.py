from zoneinfo import ZoneInfo
from .utility import calculate_total_work
from flask import render_template,flash, redirect,Blueprint, session,url_for, current_app,send_from_directory,request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from website.forms.Emp_details import Employee_Details
from .forms.search_from import SearchForm,DetailForm,NewsFeedForm,SearchEmp_Id,AssetForm,PunchManuallyForm
from .models.Admin_models import Admin
from . import db
from .models.confirmation_request import HRConfirmationRequest
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
from .common import asset_email, update_asset_email, verify_oauth2_and_send_email
from .forms.signup_form import SignUpForm
from .forms.Emp_details import Employee_Details
import json
import pandas as pd
from flask import send_file,session
import io
from openpyxl.styles import Font
# from .utility import hr_manual_punch
from io import BytesIO
from datetime import datetime, date
from .utility import calculate_month_summary, generate_attendance_excel

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

@hr.route('/download_excel_hr', methods=['GET'])
@login_required
def download_excel_hr():

    # Get session data
    emails = session.get('admin_emails')
    circle = session.get('circle')
    emp_type = session.get('emp_type')

    if not emails:
        flash("Session expired. Please search again.", "error")
        return redirect(url_for("hr.search"))

    # Fetch admins
    admins = Admin.query.filter(Admin.email.in_(emails)).all()

    # Resolve month
    month_str = request.args.get("month")
    if month_str:
        try:
            year, month = map(int, month_str.split("-"))
        except:
            flash("Invalid month format. Use YYYY-MM.", "error")
            return redirect(url_for("hr.search"))
    else:
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        year, month = now.year, now.month

    # Call common Excel generator
    output = generate_attendance_excel(
        admins=admins,
        emp_type=emp_type,
        circle=circle,
        year=year,
        month=month,
        file_prefix="HR"
    )

    # Send final file
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=f"HR_Attendance_{circle}_{emp_type}_{calendar.month_name[month]}_{year}.xlsx",
        as_attachment=True
    )








@hr.route('/view_details', methods=['GET', 'POST'])
@login_required
def view_details():
    form = DetailForm()
    punch_form = PunchManuallyForm
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
    

    if not user_id or not detail_type:
        return redirect(url_for('hr.view_details'))

    admin = Admin.query.get(user_id)
    dict_data = None
    details = None
    dict_data=None

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

        # Get all punches for the selected month
        punches = Punch.query.filter(
            Punch.punch_date.between(f'{year}-{month:02d}-01', f'{year}-{month:02d}-{num_days}'),
            Punch.admin_id == user_id
        ).all()

        # Get all approved leaves overlapping with this month
        leaves = LeaveApplication.query.filter(
            LeaveApplication.admin_id == user_id,
            LeaveApplication.status == 'Approved',
            LeaveApplication.start_date <= f'{year}-{month:02d}-{num_days}',
            LeaveApplication.end_date >= f'{year}-{month:02d}-01'
        ).all()

        # Prepare attendance structure with a flag for leave
        details = [
            {
                'punch_date': f'{year}-{month:02d}-{day:02d}',
                'punch_in': '',
                'punch_out': '',
                'is_wfh': '',
                'on_leave': False,
                'today_work': ''
            } for day in range(1, num_days + 1)
        ]

        for punch in punches:
            for detail in details:
                if detail['punch_date'] == punch.punch_date.strftime('%Y-%m-%d'):
                    detail['punch_in'] = punch.punch_in.strftime('%H:%M:%S') if punch.punch_in else ''
                    detail['punch_out'] = punch.punch_out.strftime('%H:%M:%S') if punch.punch_out else ''
                    detail['is_wfh'] = 'Yes' if punch.is_wfh else ''
                    detail['today_work'] = punch.today_work.strftime('%H:%M:%S') if punch.today_work else ''

        # Mark leave days in details
        for leave in leaves:
            current_date = leave.start_date
            while current_date <= leave.end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                for detail in details:
                    if detail['punch_date'] == date_str:
                        detail['on_leave'] = True
                current_date += timedelta(days=1)

            # Calculate the data of month

        calcu_data = 0
        calcu_hdata = 0
        leave_days = 0

        for pdata in punches:
            if pdata.punch_date:
                if pdata.punch_in and pdata.punch_out:
                    calcu_data += 1
                elif pdata.punch_in and not pdata.punch_out:
                    calcu_data += 0.5
            if pdata.is_wfh:
                calcu_hdata += 1

        # Count leave days
        for leave in leaves:
            current_date = leave.start_date
            while current_date <= leave.end_date:
                if current_date.month == month and current_date.year == year:  # restrict only to selected month
                    leave_days += 1
                current_date += timedelta(days=1)

        dict_data = {
            "attendance": calcu_data,
            "work from home": calcu_hdata,
            "leave days": leave_days
        }
        
        session["attendance_details"] = json.dumps(details)
        session["attendance_summary"] = json.dumps(dict_data)
        session['selected_month'] = month
        session['selected_year'] = year

    elif detail_type == 'Punch In-Out':
        punch_form = PunchManuallyForm()
        selected_date = None
        punch = None

        if request.method == 'POST':
            if punch_form.validate_on_submit():
                selected_date = punch_form.date.data

                # Always fetch punch record for selected date
                punch = Punch.query.filter_by(admin_id=user_id, punch_date=selected_date).first()

                if punch_form.submit.data:
                    # Search button clicked
                    if punch:
                        flash("Existing punch record found. You can modify.", "info")
                        punch_form.punch_in.data = punch.punch_in
                        punch_form.punch_out.data = punch.punch_out
                    else:
                        flash("No record found. You can enter punch in-out manually.", "warning")
                        punch_form.punch_in.data = None
                        punch_form.punch_out.data = None

                elif punch_form.punch_submit.data:
                    # Save button clicked
                    punch_in_time = punch_form.punch_in.data
                    punch_out_time = punch_form.punch_out.data

                    # ✅ Calculate total working time
                    total_work_time = calculate_total_work(punch_in_time, punch_out_time)

                    if not punch:
                        new_punch = Punch(
                            admin_id=user_id,
                            punch_date=selected_date,
                            punch_in=punch_in_time,
                            punch_out=punch_out_time,
                            today_work=total_work_time  # ✅ store total work
                        )
                        db.session.add(new_punch)
                        flash("Punch In and Out saved.", "success")
                    else:
                        punch.punch_in = punch_in_time
                        punch.punch_out = punch_out_time
                        punch.today_work = total_work_time  # ✅ update total work
                        flash("Punch In-Out updated successfully.", "success")

                    db.session.commit()
            else:
                flash(f"Form not valid: {punch_form.errors}", "danger")

        details = punch_form


    elif detail_type == 'Document':
        details = UploadDoc.query.filter_by(admin_id=user_id).all()
    elif detail_type == 'Leave Details':
        details = LeaveApplication.query.filter_by(admin_id=user_id).all()


    if admin is None:
        return redirect(url_for('hr.view_details'))

    return render_template('HumanResource/details.html', admin=admin, details=details, detail_type=detail_type, selected_month=month, selected_year=year, form=form, datetime=datetime,dict_data=dict_data)


@hr.route('/download-attendance-excel')
@login_required
def download_attendance_excel():
    details_json = session.get('attendance_details')
    user_id = session.get('viewing_user_id')
    month = session.get('selected_month')
    year = session.get('selected_year')

    if not details_json:
        return "No attendance data to export.", 400

    details = json.loads(details_json)

    # Fetch employee info
    admin_data = Admin.query.filter_by(id=user_id).first()
    if not admin_data:
        return "Employee not found.", 404

    signups_data = Signup.query.filter_by(email=admin_data.email).first()
    if not signups_data:
        return "Signup record not found.", 404

    employee_name = signups_data.first_name
    circle = signups_data.circle
    emp_type = signups_data.emp_type

    num_days = calendar.monthrange(year, month)[1]

    # Prepare data in a punch_map (day → punches)
    punch_map = {}
    for d in details:
        day = datetime.strptime(d['punch_date'], "%Y-%m-%d").day
        punch_map[day] = d

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet("Attendance")
        writer.sheets["Attendance"] = worksheet

        # Styles
        border_fmt = workbook.add_format({'border': 1})
        header_fmt = workbook.add_format({
            'border': 1, 'bold': True, 'align': 'center',
            'valign': 'vcenter', 'bg_color': '#D9E1F2'
        })
        absent_fmt = workbook.add_format({'border': 1, 'bg_color': '#FFD966'})
        bold_fmt = workbook.add_format({'bold': True})

        # Employee details at top
        worksheet.write(0, 0, "Employee Name", bold_fmt)
        worksheet.write(0, 1, employee_name)
        worksheet.write(0, 3, "Employee Type", bold_fmt)
        worksheet.write(0, 4, emp_type)
        worksheet.write(1, 0, "Circle", bold_fmt)
        worksheet.write(1, 1, circle)

        # Weekday headers
        days = []
        for d in range(1, num_days + 1):
            weekday = calendar.day_abbr[date(year, month, d).weekday()][0]
            days.append(f"{d} {weekday}")

        row = 3

        in_times, out_times, totals = [], [], []

        for d in range(1, num_days + 1):
            record = punch_map.get(d)
            if record and record['punch_in'] and record['punch_out']:
                in_times.append(record['punch_in'])
                out_times.append(record['punch_out'])

                total_minutes = 0

                # Calculate worked minutes
                if record.get('today_work'):
                    try:
                        parts = record['today_work'].split(":")
                        h = int(parts[0])
                        m = int(parts[1])
                        total_minutes = h * 60 + m
                    except:
                        total_minutes = 0
                else:
                    try:
                        punch_in = datetime.strptime(record['punch_in'], "%H:%M:%S")
                        punch_out = datetime.strptime(record['punch_out'], "%H:%M:%S")
                        delta = punch_out - punch_in
                        total_minutes = delta.seconds // 60
                    except:
                        total_minutes = 0

                hours = total_minutes // 60
                minutes = total_minutes % 60

                if hours > 0 and minutes > 0:
                    totals.append(f"{hours} hrs {minutes} min")
                elif hours > 0:
                    totals.append(f"{hours} hrs")
                elif minutes > 0:
                    totals.append(f"{minutes} min")
                else:
                    totals.append("")
            else:
                in_times.append("")
                out_times.append("")
                totals.append("")

        # Days row
        worksheet.write(row, 0, "Days", header_fmt)
        for col, val in enumerate(days, start=1):
            worksheet.write(row, col, val, header_fmt)
        row += 1

        # InTime row
        worksheet.write(row, 0, "InTime", header_fmt)
        for col, val in enumerate(in_times, start=1):
            fmt = absent_fmt if val == "" else border_fmt
            worksheet.write(row, col, val, fmt)
        row += 1

        # OutTime row
        worksheet.write(row, 0, "OutTime", header_fmt)
        for col, val in enumerate(out_times, start=1):
            fmt = absent_fmt if val == "" else border_fmt
            worksheet.write(row, col, val, fmt)
        row += 1

        # Total row
        worksheet.write(row, 0, "Total", header_fmt)
        for col, val in enumerate(totals, start=1):
            fmt = absent_fmt if val == "" else border_fmt
            worksheet.write(row, col, val, fmt)
        row += 2

        # Adjust column width
        worksheet.set_column(0, num_days, 15)

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        download_name=f'Attendance_{circle}_{emp_type}_{month}_{year}.xlsx',
        as_attachment=True
    )









@hr.route('/update-employee/<emp_id>', methods=['GET', 'POST'])
@login_required
def update_employee(emp_id):
    emp = Employee.query.filter_by(emp_id=emp_id).first_or_404()
    form = Employee_Details(obj=emp)

    if form.validate_on_submit():
        form.populate_obj(emp)

        if form.Photo.data:
            filename = secure_filename(form.Photo.data.filename)
            photo_path = os.path.join(current_app.static_folder, 'uploads', filename)
            form.Photo.data.save(photo_path)
            emp.photo_filename = filename

        db.session.commit()
        flash("Employee details updated.", "success")
        return redirect(url_for('hr.display_details'))

    return render_template('HumanResource/update_employee.html', form=form, emp=emp)

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
    form.user_name.validators = [DataRequired(),Length(min=2, max=20)]
    form.email.validators = [DataRequired(), Email()]
    form.emp_id.validators = [DataRequired(), Length(max=10)]
    form.mobile.validators = [DataRequired(), Length(min=10, max=10)]

    if form.validate_on_submit():
        if form.password.data:
            employee.password = generate_password_hash(form.password.data)

        employee.user_name = form.user_name.data
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
    
    employee = Signup.query.filter_by(email=email).first()
    if not employee:
        
        flash('Employee not found.', 'error')
        return redirect(url_for('hr.update_signup'))

    db.session.delete(employee)
    db.session.commit()
    
    flash(f'Employee {email} deleted successfully.', 'success')
    return redirect(url_for('hr.update_signup'))


@hr.route('/hr-confirmation-requests')
@login_required
def hr_confirmation_requests():
    """
    Display all confirmation requests for HR users.
    The HR role is verified by matching the logged-in user's email
    with the Signup table and checking emp_type == 'Human Resource'.
    """

    # 1️⃣ Fetch logged-in user email
    user_email = current_user.email

    # 2️⃣ Match email with Signup table to get emp_type
    hr_user = Signup.query.filter_by(email=user_email).first()

    # 3️⃣ Validate HR access
    if not hr_user or hr_user.emp_type != 'Human Resource':
        flash("Access denied. Only Human Resource users can view this page.", "danger")
        return redirect(url_for('views.home'))  # change 'views.home' to your home route

    # 4️⃣ Fetch all HR confirmation requests (most recent first)
    requests = (
        HRConfirmationRequest.query
        .order_by(HRConfirmationRequest.created_at.desc())
        .all()
    )

    # 5️⃣ Render HR confirmation requests page
    return render_template(
        'HumanResource/hr_confirmation_requests.html',
        requests=requests
    )




@hr.route('/hr/confirmation-requests')
@login_required
def view_hr_confirmation_requests():
    """Displays all confirmation requests visible to HR"""
    requests = HRConfirmationRequest.query.order_by(HRConfirmationRequest.created_at.desc()).all()
    return render_template('HumanResource/hr_confirmation_requests.html', requests=requests)


@hr.route('/hr/confirmation-request/<int:request_id>/update', methods=['POST'])
@login_required
def update_hr_confirmation_request(request_id):
    """HR approves or rejects employee confirmation"""
    req = HRConfirmationRequest.query.get_or_404(request_id)
    action = request.form.get('action')
    review = request.form.get('review')

    if action == 'approve':
        req.status = 'Approved'
    elif action == 'reject':
        req.status = 'Rejected'
    else:
        flash("Invalid action", "danger")
        return redirect(url_for('hr_bp.view_hr_confirmation_requests'))

    req.manager_review = review
    db.session.commit()

    # Send email to employee notifying HR decision
    employee = Signup.query.get(req.employee_id)
    if employee:
        subject = f"🎯 Confirmation Status: {req.status}"
        body = f"""
        <p>Dear {employee.first_name},</p>
        <p>Your employment confirmation has been reviewed by HR And your manager/tl.</p>
        <p><strong>Status:</strong> {req.status}</p>
        <p><strong>HR Comments:</strong> {review or 'No comments provided'}</p>
        <p>Thank you,<br><strong>HR Team</strong></p>
        """

        verify_oauth2_and_send_email(
            user=current_user,
            subject=subject,
            body=body,
            recipient_email=employee.email
        )

    flash(f"Request {action}d successfully!", "success")
    return redirect(url_for('hr.view_hr_confirmation_requests'))