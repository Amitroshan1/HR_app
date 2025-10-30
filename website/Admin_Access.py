import os
from datetime import date, datetime
from flask import Blueprint, render_template, session, request, redirect, flash, url_for, current_app, jsonify
from flask_login import login_required
from sqlalchemy import and_
from werkzeug.utils import secure_filename
from . import db
from .forms.search_from import SearchForm
from .models.education import Education
from .models.emp_detail_models import Employee, Asset
from .models.expense import ExpenseLineItem, ExpenseClaimHeader
from .models.news_feed import PaySlip
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
    today = date.today()

    # --- Get filters ---
    filters = {}
    emp_type = request.args.get('emp_type')
    circle = request.args.get('circle')
    if emp_type:
        filters['emp_type'] = emp_type
    if circle:
        filters['circle'] = circle

    # --- Filter Signup & related admins ---
    users = Signup.query.filter_by(**filters).all() if filters else Signup.query.all()
    admin_emails = [u.email for u in users]
    admins = Admin.query.filter(Admin.email.in_(admin_emails)).all() if admin_emails else []
    admin_ids = [a.id for a in admins]
    admin_count = len(admins)

    # --- Initialize counts ---
    leave_count = present_count = query_count = claim_count = resignation_count = 0  # ✅ add resignation_count here

    if admin_ids:
        # --- Leaves ---
        leave_admin_ids = {
            l.admin_id for l in LeaveApplication.query.filter(
                LeaveApplication.admin_id.in_(admin_ids),
                LeaveApplication.start_date >= today
            )
        }
        leave_count = len(leave_admin_ids)

        # --- Present Employees ---
        punch_admin_ids = {
            p.admin_id for p in Punch.query.filter(
                Punch.admin_id.in_(admin_ids),
                Punch.punch_date == today,
                Punch.punch_in.isnot(None)
            )
        }
        present_count = len(punch_admin_ids)

        # --- Queries ---
        query_admin_ids = {
            q.admin_id for q in Query.query.filter(
                Query.admin_id.in_(admin_ids)
            )
        }
        query_count = len(query_admin_ids)

        # --- Expense Claims ---
        claim_admin_ids = {
            c.admin_id for c in ExpenseClaimHeader.query.filter(
                ExpenseClaimHeader.admin_id.in_(admin_ids)
            )
        }
        claim_count = len(claim_admin_ids)

        # --- RESIGNATIONS ---
        resignation_admin_ids = {
            r.admin_id for r in Resignation.query.filter(
                Resignation.admin_id.in_(admin_ids)
            )
        }
        resignation_count = len(resignation_admin_ids)

    # --- Send data to template ---
    return render_template(
        "Admin_Access/admin_dashboard.html",
        users=users,
        admin_count=admin_count,
        leave_count=leave_count,
        present_count=present_count,
        query_count=query_count,
        claim_count=claim_count,
        resignation_count=resignation_count,  # ✅ safe now
        admin_ids=admin_ids,
        emp_type=emp_type,
        circle=circle
    )




@Admins_access.route('/admin-data', methods=['GET'])
@login_required
def admin_data():
    # Get filter values
    emp_type = request.args.get('emp_type_employee')
    circle = request.args.get('circle_employee')
    view_type = request.args.get('view', 'employees')  # default is employees

    # Initialize variables
    employees = []
    todays_leaves = []
    todays_attendance = []
    employee_queries = []
    employee_claims = []
    employee_resignations = []

    # Filter Signup table
    signup_filters = {}
    if emp_type:
        signup_filters['emp_type'] = emp_type
    if circle:
        signup_filters['circle'] = circle

    signup_users = Signup.query.filter_by(**signup_filters).all() if signup_filters else Signup.query.all()
    emails = [user.email for user in signup_users]

    # Get Employee records
    if emails:
        employees = Employee.query.filter(Employee.email.in_(emails)).all()

    employee_map = {emp.admin_id: emp for emp in employees}

    if employees:
        admin_ids = list(employee_map.keys())
        today = date.today()

        # ---------------- LEAVE DATA ----------------
        leaves = LeaveApplication.query.filter(
            LeaveApplication.admin_id.in_(admin_ids),
            LeaveApplication.start_date >= today
        ).all()

        admin_leave_map = {}
        for leave in leaves:
            leave.emp_obj = employee_map.get(leave.admin_id)
            admin_leave_map.setdefault(leave.admin_id, []).append({
                "id": leave.id,
                "status": leave.status
            })

        class EmployeeLeaveWrapper:
            def __init__(self, emp_obj, leaves):
                self.emp_obj = emp_obj
                self.leaves = leaves

        todays_leaves = [
            EmployeeLeaveWrapper(employee_map[admin_id], leave_list)
            for admin_id, leave_list in admin_leave_map.items()
        ]

        # ---------------- ATTENDANCE DATA ----------------
        if view_type == 'punches':
            punches = Punch.query.filter(
                Punch.admin_id.in_(admin_ids),
                Punch.punch_date == today,
                Punch.punch_in.isnot(None)
            ).all()
            present_admin_ids = {p.admin_id for p in punches}
            todays_attendance = [employee_map[admin_id] for admin_id in present_admin_ids if admin_id in employee_map]

        # ---------------- QUERIES DATA ----------------
        if view_type == 'queries':
            queries = Query.query.filter(Query.admin_id.in_(admin_ids)).all()
            admin_query_map = {}
            for q in queries:
                q.emp_obj = employee_map.get(q.admin_id)
                admin_query_map.setdefault(q.admin_id, []).append(q)

            class EmployeeQueryWrapper:
                def __init__(self, emp_obj, queries):
                    self.emp_obj = emp_obj
                    self.queries = queries

            employee_queries = [
                EmployeeQueryWrapper(employee_map[admin_id], query_list)
                for admin_id, query_list in admin_query_map.items()
            ]
            for wrapper in employee_queries:
                print(wrapper.emp_obj.name, wrapper.queries)

        # ---------------- CLAIMS DATA ----------------
        if view_type == 'claims':
            claims = ExpenseClaimHeader.query.filter(
                ExpenseClaimHeader.admin_id.in_(admin_ids)
            ).all()
            admin_claim_map = {}
            for claim in claims:
                claim.emp_obj = employee_map.get(claim.admin_id)
                admin_claim_map.setdefault(claim.admin_id, []).append(claim)

                class EmployeeClaimWrapper:
                    def __init__(self, emp_obj, claims):
                        self.emp_obj = emp_obj
                        self.claims = claims

                employee_claims = [
                    EmployeeClaimWrapper(employee_map[admin_id], claim_list)
                    for admin_id, claim_list in admin_claim_map.items()
                ]

        # ---------------- RESIGNATIONS DATA ----------------
        if view_type == 'resignations':
            resignations = Resignation.query.filter(
                Resignation.admin_id.in_(admin_ids)
            ).all()


            for r in resignations:
                r.emp_obj = employee_map.get(r.admin_id)
                employee_resignations.append(r)
        else:
            employee_resignations = []
        print(f"Employee resignations: {employee_resignations}")

    return render_template(
        "Admin_Access/admin_data.html",
        employees=employees,
        todays_leaves=todays_leaves if view_type == 'leaves' else [],
        todays_attendance=todays_attendance if view_type == 'punches' else [],
        employee_queries=employee_queries if view_type == 'queries' else [],
        employee_claims=employee_claims if view_type == 'claims' else [],
        resignations=employee_resignations if view_type == 'resignations' else [],
        view_type=view_type,
        emp_type=emp_type,
        circle=circle,
    )


@Admins_access.route('/employee/<int:admin_id>/details', methods=['GET'])
@login_required
def view_employee_details(admin_id):
    today = date.today()

    emp = Employee.query.filter_by(admin_id=admin_id).first_or_404()
    leaves = LeaveApplication.query.filter(LeaveApplication.admin_id==admin_id, LeaveApplication.start_date >= today).all()
    punches = Punch.query.filter_by(admin_id=admin_id).all()
    payslips = PaySlip.query.filter_by(admin_id=admin_id).all()
    assets = Asset.query.filter_by(admin_id=admin_id).all()
    claims = ExpenseClaimHeader.query.filter_by(admin_id=admin_id).all()
    queries = Query.query.filter_by(admin_id=admin_id).all()
    resignations = Resignation.query.filter_by(admin_id=admin_id).all()   # ✅ new

    mode = request.args.get("mode", "all").lower()

    if mode in ["leave", "leaves"]:
        active_tab = "leaves"
    elif mode in ["queries", "query"]:
        active_tab = "queries"
    elif mode == "punches":
        active_tab = "punches"
    elif mode == "payslips":
        active_tab = "payslips"
    elif mode == "assets":
        active_tab = "assets"
    elif mode == "claims":
        active_tab = "claims"
    elif mode in ["resignations", "resignations"]:   # ✅ new
        active_tab = "resignations"
    else:
        active_tab = "None"

    emp_data = {
        "emp": emp,
        "leaves": leaves,
        "punches": punches,
        "payslips": payslips,
        "assets": assets,
        "claims": claims,
        "queries": queries,
        "resignations": resignations
    }

    return render_template(
        "Admin_Access/view_employee_details.html",
        data=emp_data,
        active_tab=active_tab
    )


@Admins_access.route('/update-status/<model_name>/<int:record_id>/<column>/<value>')
@login_required
def update_status(model_name, record_id, column, value):
    # Map allowed models
    model_mapping = {
        'claim_item': ExpenseLineItem,
        'LeaveApplication': LeaveApplication,
        'Query': Query,
        'Resignation': Resignation
    }

    if model_name not in model_mapping:
        flash(f"Invalid model: {model_name}", "danger")
        return redirect(request.referrer or url_for('Admins_access.dashboard'))

    Model = model_mapping[model_name]
    record = Model.query.get_or_404(record_id)

    if model_name == 'Query' and column == 'reply':
        # Create new QueryReply
        from flask_login import current_user
        reply = QueryReply(
            query_id=record.id,
            admin_id=current_user.id,
            reply_text=value,
            user_type='Admin'
        )
        db.session.add(reply)
        db.session.commit()
        return {
            "success": True,
            "reply_text": reply.reply_text,
            "user_type": reply.user_type
        }

    # Regular column update
    if not hasattr(record, column):
        flash(f"Invalid column: {column}", "danger")
        return redirect(request.referrer or url_for('Admins_access.dashboard'))

    setattr(record, column, value)
    db.session.commit()

    flash(f"{model_name} ID {record.id} updated: {column} = {value}", "success")
    return redirect(request.referrer or url_for('Admins_access.view_employee_details', admin_id=getattr(record, 'admin_id', 1)))

