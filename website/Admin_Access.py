from datetime import date

from flask import Blueprint, render_template, session, request, redirect, flash, url_for
from flask_login import login_required
from sqlalchemy import and_

from . import db
from .forms.search_from import SearchForm
from .models.expense import ExpenseLineItem, ExpenseClaimHeader
from .models.query import Query, QueryReply
from .models.seperation import Resignation
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
            "is_wfh": punch.is_wfh if punch else False,
            "punch_id": punch.id if punch else None
        })

    return render_template(
        "Admin_Access/attendance_admin.html",
        attendance_data=attendance_data)


@Admins_access.route('/queries-admin', methods=['GET'])
def queries_admin():
    # Get filters
    emp_type = request.args.get('emp_type_queries')
    circle = request.args.get('circle_queries')

    # Base Query
    query = db.session.query(Query, Signup) \
        .join(Admin, Query.admin_id == Admin.id) \
        .join(Signup, Signup.email == Admin.email)

    # Apply filters
    if emp_type:
        query = query.filter(Signup.emp_type == emp_type)
    if circle:
        query = query.filter(Signup.circle == circle)

    results = query.all()

    # Split queries by status
    new_queries = []
    open_queries = []

    for q, s in results:
        data = {
            "id": q.id,
            "title": q.title,
            "query_text": q.query_text,
            "created_at": q.created_at,
            "status": q.status,
            "photo": q.photo,
            "admin_name": q.admin.first_name,
            "admin_email": q.admin.email,
            "sent_to": q.emp_type,
            "replies_count": len(q.replies)
        }

        if q.status == "New":
            new_queries.append(data)
        else:
            open_queries.append(data)

    return render_template(
        "Admin_Access/queries_admin.html",
        new_queries=new_queries,
        open_queries=open_queries,
        selected_emp_type=emp_type,
        selected_circle=circle
    )


@Admins_access.route('/query-chat/<int:query_id>')
def view_query_chat(query_id):
    query = Query.query.get_or_404(query_id)
    replies = QueryReply.query.filter_by(query_id=query_id).order_by(QueryReply.created_at.asc()).all()
    return render_template('Admin_Access/query_chat.html', query=query, replies=replies)




@Admins_access.route('/claim_admin')
@login_required
def claim_admin():
    # Get filter values
    emp_type = request.args.get('emp_type_claim')
    circle = request.args.get('circle_claim')
    view = request.args.get('view', 'pending')  # default = pending
    print(f"emp_type_claim: {emp_type}")
    print(f"circle_claim: {circle}")
    print(f"View: {view}")

    # Base query: Join ClaimHeader with Admin + Signup
    query = db.session.query(ExpenseClaimHeader, Signup) \
        .join(Admin, ExpenseClaimHeader.admin_id == Admin.id) \
        .join(Signup, Signup.email == Admin.email)

    # Apply filters on Signup table
    if emp_type:
        query = query.filter(Signup.emp_type == emp_type)
    if circle:
        query = query.filter(Signup.circle == circle)

    results = query.all()  # returns list of (ExpenseClaimHeader, Signup)
    print("Claims count after filter:", len(results))

    # Extract only claim headers
    claims = [r[0] for r in results]

    # If view == pending, only keep claims where ANY expense is still pending
    if view == "pending":
        claims = [c for c in claims if any(item.status == "Pending" for item in c.expenses)]
        print("Claims count after pending filter:", len(claims))

    # Pre-compute overall status for table
    for claim in claims:
        if any(item.status == "Pending" for item in claim.expenses):
            claim.overall_status = "Pending"
        elif any(item.status == "Rejected" for item in claim.expenses):
            claim.overall_status = "Rejected"
        else:
            claim.overall_status = "Approved"

    return render_template(
        'Admin_Access/claim_admin.html',
        claims=claims,
        view=view,
        emp_type=emp_type,
        circle=circle
    )


@Admins_access.route('/update_claim_status/<int:item_id>/<string:action>', methods=['POST'])
@login_required
def update_claim_status(item_id, action):
    item = ExpenseLineItem.query.get_or_404(item_id)

    if action == "approve":
        item.status = "Approved"
    elif action == "reject":
        item.status = "Rejected"

    db.session.commit()
    flash(f"Expense item {item.sr_no} marked as {item.status}.", "success")
    return redirect(url_for('Admins_access.claim_admin'))


@Admins_access.route('/resignation-admin', methods=['GET'])
@login_required
def resignation_admin():
    emp_type = request.args.get('emp_type')
    circle = request.args.get('circle')
    status = request.args.get('status')

    query = (
        db.session.query(Resignation, Signup)
        .join(Admin, Resignation.admin_id == Admin.id)
        .join(Signup, Signup.email == Admin.email)   # link using email
    )

    if emp_type:
        query = query.filter(Signup.emp_type == emp_type)

    if circle:
        query = query.filter(Signup.circle == circle)

    if status:
        query = query.filter(Resignation.status == status)

    resignations = query.all()

    return render_template(
        'Admin_Access/resignation_admin.html',
        resignations=resignations
    )



@Admins_access.route('/resignation/<int:resignation_id>/<string:action>', methods=['POST'])
@login_required
def update_resignation_status(resignation_id, action):
    resignation = Resignation.query.get_or_404(resignation_id)

    if action == 'approve':
        resignation.status = 'Approved'
        flash("Resignation approved successfully!", "success")
    elif action == 'reject':
        resignation.status = 'Rejected'
        flash("Resignation rejected successfully!", "danger")

    db.session.commit()
    return redirect(url_for('Admins_access.resignation_admin'))







