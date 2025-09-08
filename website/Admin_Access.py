from datetime import date

from flask import Blueprint, render_template, session, request, redirect, flash, url_for
from flask_login import login_required
from sqlalchemy import and_

from . import db
from .forms.search_from import SearchForm
from .models.signup import Signup
from .models.attendance import LeaveApplication, Punch
from .models.Admin_models import Admin
from flask_wtf import CSRFProtect

Admins_access = Blueprint('Admins_access', __name__)
@Admins_access.route('/Admin-dashboard',methods=['GET','POST'])
@login_required
def admin_dashboard():
    emp_type = request.args.get('emp_type')
    circle = request.args.get('circle')

    filters = {}
    if emp_type:
        filters['emp_type'] = emp_type
    if circle:
        filters['circle'] = circle

    if filters:
        users = Signup.query.filter_by(**filters).all()
    else:
        users = []
    for user in users:
        print(user.first_name)

    employee_count = Signup.query.count()
    total_leaves = LeaveApplication.query.count()
    print(f"Employee Count: {total_leaves}")


    return render_template('Admin_Access/admin_dashboard.html', users=users, employee_count=employee_count,total_leaves=total_leaves)

@Admins_access.route('/total-employee',methods=['GET','POST'])
@login_required
def total_employee():
    emp_type = request.args.get('emp_type_employee')
    circle = request.args.get('circle_employee')
    print(f"got the employee type: {emp_type}")
    print(f"got the circle employee: {circle}")


    filters = {}
    if emp_type:
        filters['emp_type'] = emp_type
    if circle:
        filters['circle'] = circle


    if filters:
        employees = Signup.query.filter_by(**filters).all()
    else:
        employees = Signup.query.all()

    return render_template('Admin_Access/total_employee.html', employees=employees)


@Admins_access.route('/leave-employee', methods=['GET'])
@login_required
def leave_employee():
    # Collect filters
    emp_type_leave = request.args.get('emp_leave')
    circle_leave = request.args.get('circle_leave')
    status_filter = request.args.get('status')
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    print(f"got the employee type: {emp_type_leave},got the circle leave: {circle_leave},status: {status_filter},month: {month},year: {year}")

    # Base query with extra columns
    query = (
        db.session.query(
            LeaveApplication,
            Signup.emp_type,
            Signup.circle
        )
        .join(Admin, Admin.id == LeaveApplication.admin_id)
        .join(Signup, Signup.email == Admin.email)
    )

    # Apply filters dynamically
    if emp_type_leave:
        query = query.filter(Signup.emp_type == emp_type_leave)

    if circle_leave:
        query = query.filter(Signup.circle == circle_leave)

    if month and year:
        query = query.filter(
            db.extract('month', LeaveApplication.start_date) == month,
            db.extract('year', LeaveApplication.start_date) == year
        )

    # Split by status
    pending_leaves, approved_leaves, rejected_leaves = [], [], []

    if status_filter:
        if status_filter == "Pending":
            pending_leaves = query.filter(LeaveApplication.status == "Pending").all()
        elif status_filter == "Approved":
            approved_leaves = query.filter(LeaveApplication.status == "Approved").all()
        elif status_filter == "Rejected":
            rejected_leaves = query.filter(LeaveApplication.status == "Rejected").all()
    else:
        pending_leaves = query.filter(LeaveApplication.status == "Pending").all()
        approved_leaves = query.filter(LeaveApplication.status == "Approved").all()
        rejected_leaves = query.filter(LeaveApplication.status == "Rejected").all()

    return render_template(
        "Admin_Access/leave_employee.html",
        pending_leaves=pending_leaves,
        approved_leaves=approved_leaves,
        rejected_leaves=rejected_leaves,
        emp_type_leave=emp_type_leave,
        circle_leave=circle_leave,
        status=status_filter,
        month=month,
        year=year
    )



@Admins_access.route('/approve-leave-admin/<int:leave_id>', methods=['GET'])
def approve_leave_admin(leave_id):
    # Fetch leave application by ID
    leave_app_data = LeaveApplication.query.get_or_404(leave_id)

    # Update status to Approved
    leave_app_data.status = 'Approved'
    db.session.commit()

    flash('Leave application has been approved.', 'success')
    return redirect(url_for('Admins_access.leave_employee'))


@Admins_access.route('/reject-leave-admin/<int:leave_id>', methods=['GET'])
def reject_leave_admin(leave_id):
    leave_app_data = LeaveApplication.query.get_or_404(leave_id)
    leave_app_data.status = 'Rejected'
    db.session.commit()

    flash('Leave application has been rejected.', 'danger')
    return redirect(url_for('Admins_access.leave_employee'))



@Admins_access.route('/attendance-admin', methods=['GET'])
def attendance_admin():
    emp_type = request.args.get('emp_type_attendance')
    circle = request.args.get('circle_attendance')

    # Step 1: Get Signup users based on filters
    query = Signup.query
    if emp_type:
        query = query.filter(Signup.emp_type == emp_type)
    if circle:
        query = query.filter(Signup.circle == circle)
    users = query.all()

    today = date.today()
    attendance_data = []

    for user in users:
        # Step 2: Find matching Admin using email
        admin = Admin.query.filter_by(email=user.email).first()
        if not admin:
            continue

        # Step 3: Fetch today's punch record
        punch = Punch.query.filter(
            and_(
                Punch.admin_id == admin.id,
                Punch.punch_date == today
            )
        ).first()

        # Step 4: Append attendance info

        attendance_data.append({
            "emp_id": user.emp_id,
            "name": user.first_name,
            "emp_type": user.emp_type,
            "circle": user.circle,
            "present": bool(punch),   # True if punched in today
            "punch_in": punch.punch_in if punch else "-",
            "punch_out": punch.punch_out if punch else "-",
            "today_work": punch.today_work if punch else "-",
            "is_holiday": punch.is_holiday if punch else False,
            "is_wfh": punch.is_wfh if punch else False
        })

    return render_template(
        "Admin_Access/attendance_admin.html",
        attendance_data=attendance_data
    )