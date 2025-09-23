import os
from datetime import date, datetime

from flask import Blueprint, render_template, session, request, redirect, flash, url_for, current_app
from flask_login import login_required
from sqlalchemy import and_
from werkzeug.utils import secure_filename

from . import db
from .forms.search_from import SearchForm
from .models.education import Education
from .models.emp_detail_models import Employee, Asset
from .models.expense import ExpenseLineItem, ExpenseClaimHeader
from .models.query import Query, QueryReply
from .models.seperation import Resignation
from .models.signup import Signup
from .models.attendance import LeaveApplication, Punch, LeaveBalance
from .models.Admin_models import Admin
from flask_wtf import CSRFProtect


Admins_access = Blueprint('Admins_access', __name__)
@Admins_access.route('/Admin-dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    emp_type = request.args.get('emp_type')
    circle = request.args.get('circle')

    filters = {}
    if emp_type:
        filters['emp_type'] = emp_type
    if circle:
        filters['circle'] = circle

    # Filter Signup table
    users = Signup.query.filter_by(**filters).all() if filters else Signup.query.all()

    # Get matching admin emails and IDs
    admin_emails = [u.email for u in users]
    admins = Admin.query.filter(Admin.email.in_(admin_emails)).all() if admin_emails else []
    admin_count = len(admins)
    admin_ids = [a.id for a in admins]

    return render_template(
        "Admin_Access/admin_dashboard.html",
        users=users,
        admin_count=admin_count,
        admin_ids=admin_ids,
        emp_type=emp_type,
        circle=circle
    )



@Admins_access.route('/total-employee', methods=['GET'])
@login_required
def total_employee():
    # Get filter values from query params
    emp_type = request.args.get('emp_type_employee')
    circle = request.args.get('circle_employee')

    # Build filter dictionary for Signup table
    signup_filters = {}
    if emp_type:
        signup_filters['emp_type'] = emp_type
    if circle:
        signup_filters['circle'] = circle

    # Query Signup table to get emails
    if signup_filters:
        signup_users = Signup.query.filter_by(**signup_filters).all()
    else:
        signup_users = Signup.query.all()

    emails = [user.email for user in signup_users]

    # Query Employee table to get full records matching those emails
    if emails:
        employees = Employee.query.filter(Employee.email.in_(emails)).all()
    else:
        employees = []

    # Pass everything to the template
    return render_template(
        "Admin_Access/total_employee.html",
        employees=employees,  # full Employee records
        emp_type=emp_type,
        circle=circle
    )




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



@Admins_access.route('/view-employee-details/<int:admin_id>', methods=['GET'])
@login_required
def view_employee_details(admin_id):
    # Define modules with title and endpoint (Flask function name)
    modules = [
        {"title": "Employee Details", "endpoint": "Admins_access.employee_admin_access"},
        {"title": "Admin", "endpoint": "Admins_access.admin_admin_access"},
        {"title": "Asset", "endpoint": "Admins_access.asset_admin_access"},
        {"title": "Education", "endpoint": "Admins_access.education_admin_access"},
        {"title":"Leave Application", "endpoint": "Admins_access.leave_application_admin_access"},
        {"title":"Leave Balance", "endpoint": "Admins_access.leave_balance_admin_access"},
        {"title":"Claim", "endpoint": "Admins_access.claim_admin_access"}
    ]
    return render_template(
        "Admin_Access/view_employee.html",
        admin_id=admin_id,
        modules=modules
    )


def generic_inline_update(model_class, record_id, redirect_endpoint, editable_fields, file_fields=None):
    """
    model_class     -> The SQLAlchemy model class (Employee, Asset, etc.)
    record_id       -> The primary key of the record to update
    redirect_endpoint -> Flask endpoint to redirect after update
    editable_fields -> Set of fields that can be updated from request.form
    file_fields     -> Set of fields that can be updated from request.files
    """
    record = model_class.query.get_or_404(record_id)

    # Update form fields
    for field, value in request.form.items():
        if field in editable_fields:
            setattr(record, field, value)

    # Update file fields (photo, images, etc.)
    if file_fields:
        for field in file_fields:
            if field in request.files:
                file = request.files[field]
                if file and file.filename:
                    # Save the file somewhere, e.g., static/uploads/
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(current_app.root_path, 'static/uploads', filename))
                    setattr(record, field, filename)

    try:
        db.session.commit()
        flash(f"{model_class.__name__} details updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error while updating {model_class.__name__} details.", "danger")

    return redirect(url_for(redirect_endpoint, admin_id=record.admin_id))



def generic_delete(model_class, record_id):
    record = model_class.query.get_or_404(record_id)
    try:
        db.session.delete(record)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})




from flask import jsonify

# Show Employee Table (same page)
@Admins_access.route('/employee-admin-access/<int:admin_id>')
@login_required
def employee_admin_access(admin_id):
    emp_data= Employee.query.get_or_404(admin_id)
    return render_template(
        "Admin_Access/employee_admin_access.html",
        admin_id=admin_id,
        emp_data=emp_data
    )

@Admins_access.route('/employee-inline-update/<int:emp_id>', methods=['POST'])
@login_required
def employee_inline_update(emp_id):
    editable_fields = {
        "name", "photo_filename","email", "father_name", "mother_name", "marital_status",
        "spouse_name", "dob", "emp_id", "mobile", "gender", "emergency_mobile",
        "caste", "nationality", "language", "religion", "blood_group", "designation",
        "permanent_address_line1", "permanent_address_line2", "permanent_address_line3",
        "permanent_pincode", "permanent_district", "permanent_state",
        "present_address_line1", "present_address_line2", "present_address_line3",
        "present_pincode", "present_district", "present_state"
    }
    file_fields = {"photo_filename"}
    return generic_inline_update(Employee, emp_id, 'Admins_access.employee_admin_access', editable_fields,file_fields)


# Delete employee
@Admins_access.route('/employee-delete/<int:emp_id>', methods=['POST'])
@login_required
def employee_delete(emp_id):
    return generic_delete(Employee, emp_id)



@Admins_access.route('/query-admin-access/<int:admin_id>')
@login_required
def query_admin_access(admin_id):
    pass


@Admins_access.route('/admin-admin-access/<int:admin_id>')
@login_required
def admin_admin_access(admin_id):
    admin_data = Admin.query.get_or_404(admin_id)
    return render_template("Admin_Access/admin_admin_access.html",admin_id=admin_id, admin_data=admin_data)




@Admins_access.route('/asset-admin-access/<int:admin_id>')
@login_required
def asset_admin_access(admin_id):
    # Fetch all assets belonging to this admin
    asset_data = Asset.query.filter_by(admin_id=admin_id).all()
    return render_template(
        "Admin_Access/asset_admin_access.html",
        admin_id=admin_id,
        asset_data=asset_data
    )


@Admins_access.route('/asset-inline-update/<int:emp_id>', methods=['POST'])
@login_required
def asset_inline_update(emp_id):
    editable_fields = {
        "name",
        "description",
        "image_files",
        "issue_date",
        "return_date",
        "remark"
    }

    file_fields = {"image_files"}

    return generic_inline_update(Asset, emp_id, 'Admins_access.asset_admin_access', editable_fields,file_fields)

@Admins_access.route('/asset-delete/<int:emp_id>', methods=['POST'])
@login_required
def asset_delete(emp_id):
    return generic_delete(Asset, emp_id)


@Admins_access.route('/education-admin-access/<int:admin_id>')
@login_required
def education_admin_access(admin_id):
    education_data = Education.query.filter_by(admin_id=admin_id).all()
    return render_template(
        "Admin_Access/education_admin_access.html",
        admin_id=admin_id,
        education_data=education_data
    )

@Admins_access.route('/leave_application_admin_access/<int:admin_id>')
@login_required
def leave_application_admin_access(admin_id):
    leave_application_data = LeaveApplication.query.filter_by(admin_id=admin_id).all()
    return render_template(
        "Admin_Access/leave_application_admin_access.html",
        admin_id=admin_id,
        leave_application_data=leave_application_data
    )


# Delete employee
@Admins_access.route('/leave-application-delete/<int:emp_id>', methods=['POST'])
@login_required
def leave_application_delete(emp_id):
    return generic_delete(LeaveApplication, emp_id)




@Admins_access.route('/leave-balance-admin_access/<int:admin_id>')
@login_required
def leave_balance_admin_access(admin_id):
    # Step 1: Get admin by ID
    admin_data = Admin.query.get_or_404(admin_id)

    # Step 2: Find the signup user by email
    signup_user = Signup.query.filter_by(email=admin_data.email).first_or_404()

    # Step 3: Fetch leave balance using signup_id
    leave_balance_data = LeaveBalance.query.filter_by(signup_id=signup_user.id).all()

    # Step 4: Pass data to template
    return render_template(
        "Admin_Access/leave_balance_admin_access.html",
        admin_id=admin_id,
        leave_balance_data=leave_balance_data
    )



@Admins_access.route('/leave-balance-inline-update/<int:balance_id>', methods=['POST'])
@login_required
def leave_balance_inline_update(balance_id):
    record = LeaveBalance.query.get_or_404(balance_id)

    try:
        # Numeric fields
        record.privilege_leave_balance = float(request.form.get("privilege_leave_balance", record.privilege_leave_balance))
        record.casual_leave_balance = float(request.form.get("casual_leave_balance", record.casual_leave_balance))
        record.compensatory_leave_balance = float(request.form.get("compensatory_leave_balance", record.compensatory_leave_balance))

        # Date field
        last_updated_str = request.form.get("last_updated")
        if last_updated_str:
            record.last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d").date()

        db.session.commit()
        flash("Leave balance updated successfully!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error while updating leave balance: {str(e)}", "danger")

    # Find admin_id to redirect back
    signup_user = Signup.query.get_or_404(record.signup_id)
    admin = Admin.query.filter_by(email=signup_user.email).first_or_404()

    return redirect(url_for("Admins_access.leave_balance_admin_access", admin_id=admin.id))



@Admins_access.route('/leave-balance-delete/<int:balance_id>', methods=['POST'])
@login_required
def leave_balance_delete(balance_id):
    record = LeaveBalance.query.get_or_404(balance_id)

    try:
        db.session.delete(record)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)})


@Admins_access.route('/claim-admin-access/<int:admin_id>')
@login_required
def claim_admin_access(admin_id):
    # Fetch all assets belonging to this admin
    claim_data = ExpenseClaimHeader.query.filter_by(admin_id=admin_id).all()
    return render_template(
        "Admin_Access/claim_admin_access.html",
        admin_id=admin_id,
        claim_data=claim_data
    )


@Admins_access.route('/claim-line-item-status/<int:item_id>', methods=['POST'])
@login_required
def claim_line_item_status(item_id):
    item = ExpenseLineItem.query.get_or_404(item_id)

    new_status = request.form.get('status')  # "Approved" or "Rejected"
    if new_status in ["Approved", "Rejected"]:
        item.status = new_status
        try:
            db.session.commit()
            flash(f"Expense item {item.sr_no} {new_status} successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating status: {str(e)}", "danger")
    else:
        flash("Invalid status.", "danger")

    # Redirect back to the admin view of the claim
    return redirect(url_for('Admins_access.claim_admin_access', admin_id=item.claim.admin_id))

