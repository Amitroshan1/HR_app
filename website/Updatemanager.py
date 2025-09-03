import os

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app,session
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf
from werkzeug.utils import secure_filename
from .forms.search_from import SearchFormmanager
from . import db
from .common import send_claim_submission_email, get_date_range_from_month
from .common import verify_oauth2_and_send_email
from .forms.expense_form import ExpenseClaimForm
from .forms.manager import ManagerContactForm
from .forms.seperation import NocUpload
from .models.Admin_models import Admin
from .models.attendance import LeaveApplication, WorkFromHomeApplication
from .models.expense import ExpenseClaimHeader, ExpenseLineItem
from .models.manager_model import ManagerContact
from .models.seperation import Resignation, Noc, Noc_Upload
from .models.signup import Signup




manager_bp = Blueprint('manager_bp', __name__)




@manager_bp.route('/mang_search', methods=['GET', 'POST'])
@login_required
def search():
    form = SearchFormmanager()

    if form.validate_on_submit():
        circle = form.circle.data.strip() if form.circle.data else None
        emp_type = form.emp_type.data.strip() if form.emp_type.data else None
        identifier = form.identifier.data.strip() if form.identifier.data else None

        signups = []

        if circle and emp_type:
            if identifier:
                # Case 1: circle + emp_type + identifier (email/emp_id)
                signups = Signup.query.filter(
                    ((Signup.email == identifier) | (Signup.emp_id == identifier)),
                    Signup.circle == circle,
                    Signup.emp_type == emp_type
                ).all()
            else:
                # Case 2: circle + emp_type only
                signups = Signup.query.filter_by(circle=circle, emp_type=emp_type).all()
        elif identifier:
            # Case 3: identifier only (fallback, in case circle/emp_type not given)
            signups = Signup.query.filter(
                (Signup.email == identifier) | (Signup.emp_id == identifier)
            ).all()

        if not signups:
            flash("No matching Signup entries found", category="error")
            return redirect(url_for("manager_bp.search"))

        emails = [s.email for s in signups]

        admins = Admin.query.filter(Admin.email.in_(emails)).all()
        if not admins:
            flash("No matching Admin records found", category="error")
            return redirect(url_for("manager_bp.search"))

        # Save to session for manager_contact route
        session["admin_emails"] = emails
        session["circle"] = circle
        session["emp_type"] = emp_type
        session["identifier"] = identifier

        return redirect(url_for("manager_bp.manager_contact"))

    return render_template("HumanResource/searchmanager.html", form=form)



@login_required
@manager_bp.route('/manager_contact', methods=['GET', 'POST'])
def manager_contact():
    form = ManagerContactForm()

    if request.method == 'GET':
        circle = session.get('circle')
        emp_type = session.get('emp_type')
        identifier = session.get('identifier')  # may be email/emp_id from search flow

        # Prefill from identifier (email/emp_id) if present
        if identifier and '@' in identifier:
            form.user_email.data = identifier

        # Try to fetch existing record to prefill
        q = ManagerContact.query.filter_by(
            circle_name=circle, user_type=emp_type,
            user_email=form.user_email.data or None
        ).first()

        if q:
            form.circle_name.data = q.circle_name
            form.user_type.data   = q.user_type
            form.user_email.data  = q.user_email

            form.l1_name.data   = q.l1_name
            form.l1_mobile.data = q.l1_mobile
            form.l1_email.data  = q.l1_email

            form.l2_name.data   = q.l2_name
            form.l2_mobile.data = q.l2_mobile
            form.l2_email.data  = q.l2_email

            form.l3_name.data   = q.l3_name
            form.l3_mobile.data = q.l3_mobile
            form.l3_email.data  = q.l3_email
        else:
            # Prefill just the scope
            form.circle_name.data = circle
            form.user_type.data   = emp_type

    if form.validate_on_submit():
        scope = dict(
            circle_name=form.circle_name.data.strip(),
            user_type=form.user_type.data.strip(),
        )
        target_email = (form.user_email.data or None)

        # Try to find the exact row we should edit (general or specific)
        row = ManagerContact.query.filter_by(
            **scope, user_email=target_email
        ).first()

        if not row:
            # Create new row (unique index ensures we can't duplicate)
            row = ManagerContact(**scope, user_email=target_email)
            db.session.add(row)

        # Update payload (only overwrite with non-empty values if you prefer)
        row.l1_name   = form.l1_name.data or None
        row.l1_mobile = form.l1_mobile.data or None
        row.l1_email  = form.l1_email.data or None

        row.l2_name   = form.l2_name.data
        row.l2_mobile = form.l2_mobile.data
        row.l2_email  = form.l2_email.data

        row.l3_name   = form.l3_name.data
        row.l3_mobile = form.l3_mobile.data
        row.l3_email  = form.l3_email.data

        try:
            db.session.commit()
            flash('Manager contact saved successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Could not save: ' + str(e), 'danger')

        return redirect(url_for('manager_bp.manager_contact'))

    return render_template('HumanResource/manager.html', form=form)


@login_required
@manager_bp.route('/claim-expense', methods=['GET', 'POST'])
def claim_expense():
    form = ExpenseClaimForm()
    
    if form.validate_on_submit():
        
        try:
            # Save header
            header = ExpenseClaimHeader(
                admin_id=current_user.id,
                employee_name=form.employee_name.data,
                designation=form.designation.data,
                emp_id=form.emp_id.data,
                email=form.email.data,
                project_name=form.project_name.data,
                country_state=form.country_state.data,
                travel_from_date=form.travel_from_date.data,
                travel_to_date=form.travel_to_date.data
                
            )
            db.session.add(header)
            db.session.flush()

            upload_folder = os.path.join(current_app.root_path, 'static/uploads/')
            os.makedirs(upload_folder, exist_ok=True)

            for i, item_form in enumerate(form.expenses.entries):
                filename = None
                if item_form.form.Attach_file.data:
                    file = item_form.form.Attach_file.data
                    filename = secure_filename(f"{form.emp_id.data}_{i+1}_{file.filename}")
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)

                item = ExpenseLineItem(
                    claim_id=header.id,
                    sr_no=item_form.form.sr_no.data,
                    date=item_form.form.date.data,
                    purpose=item_form.form.purpose.data,
                    amount=item_form.form.amount.data,
                    currency=item_form.form.currency.data,
                    Attach_file=filename,
                    status=item_form.form.status.data or 'Pending'
                )
                db.session.add(item)
            
            db.session.commit()
            
            try:
                
                send_claim_submission_email(header)
            except Exception as email_err:
                current_app.logger.warning(f"Email not sent: {email_err}")
                raise email_err
            
            flash('Expense claim submitted successfully! and mail sent for approval', 'success')
            return redirect(url_for('manager_bp.claim_expense'))

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", 'danger')
            current_app.logger.error(f"Error in claim_expense: {e}")
    else:
        if request.method == 'POST':
            
            raise form.errors


    # ✅ Fetch existing claims
    claims = ExpenseClaimHeader.query.order_by(ExpenseClaimHeader.id.desc()).all()
    claims_with_items = []
    for claim in claims:
        items = ExpenseLineItem.query.filter_by(claim_id=claim.id).all()
        claims_with_items.append((claim, items))
    


    return render_template('OTP/claim_expense.html', form=form, claims=claims, claims_with_items=claims_with_items)

@login_required
@manager_bp.route('/approve-line-item/<int:item_id>')
def approve_line_item(item_id):
    item = ExpenseLineItem.query.get_or_404(item_id)
    item.status = 'Approved'
    try:
        db.session.commit()
        return """
            <h1>Expense item has been <span style='color:green;'>approved</span>.</h1>
            <p>Status updated successfully.</p>
        """
    except Exception as e:
        db.session.rollback()
        return f"""
            <h1>Error</h1>
            <p>Failed to approve item: {str(e)}</p>
        """
@login_required
@manager_bp.route('/reject-line-item/<int:item_id>')
def reject_line_item(item_id):
    item = ExpenseLineItem.query.get_or_404(item_id)
    item.status = 'Rejected'
    try:
        db.session.commit()
        return """
            <h1>Expense item has been <span style='color:red;'>rejected</span>.</h1>
            <p>Status updated successfully.</p>
        """
    except Exception as e:
        db.session.rollback()
        return f"""
            <h1>Error</h1>
            <p>Failed to reject item: {str(e)}</p>
        """

@manager_bp.route('/manager_access', methods=['GET', 'POST'])
@login_required
def manager_access():
    csrf_token = generate_csrf()
    current_email = current_user.email

    # 🔍 Step 1: Get departments handled by manager
    manager_data = ManagerContact.query.filter(
        (ManagerContact.l1_email == current_email) |
        (ManagerContact.l2_email == current_email) |
        (ManagerContact.l3_email == current_email)
    ).all()

    users_type_list = [m.user_type for m in manager_data]
    circle_name_list = [m.circle_name for m in manager_data]


    # 🔍 Step 2: Get HRs based on type + circle
    signup_data = Signup.query.filter(
        Signup.emp_type.in_(users_type_list),
        Signup.circle.in_(circle_name_list)
    ).all()

    email_list = [i.email for i in signup_data]
    data_admin = Admin.query.filter(Admin.email.in_(email_list)).all()
    admin_ids = [a.id for a in data_admin]



    # 🗓️ Step 3: Get month from form and generate date range
    selected_month = request.form.get('selected_month')
    start_date, end_date = get_date_range_from_month(selected_month)

    # 🔍 Step 4: Filter pending leaves
    # 🔍 Step 4: Filter pending leaves
    leave_apps = LeaveApplication.query.filter(
        LeaveApplication.admin_id.in_(admin_ids),
        LeaveApplication.status == 'Pending'
    ).all()


    if start_date and end_date:
        leave_another = LeaveApplication.query.filter(
            LeaveApplication.admin_id.in_(admin_ids),
            LeaveApplication.status != 'Pending',
            LeaveApplication.start_date.between(start_date, end_date)
        ).all()
    else:
        leave_another = []


    # ✅ Final Render
    return render_template(
        'Manager/manager.html',
        users_type_list=users_type_list,
        circle_name_list=circle_name_list,
        signup_data=signup_data,
        leave_apps=leave_apps,
        leave_another=leave_another,
        selected_month=selected_month
    )


@manager_bp.route('wfh_approval', methods=['GET', 'POST'])
def wfh_approval():
    csrf_token = generate_csrf()
    current_email = current_user.email
    manager_data = ManagerContact.query.filter(
        (ManagerContact.l1_email == current_email) |
        (ManagerContact.l2_email == current_email) |
        (ManagerContact.l3_email == current_email)
    ).all()

    emp_type = [manager.user_type for manager in manager_data]
    circle_type = [manager.circle_name for manager in manager_data]
    # print(f"emp_type: {emp_type}, circle_type: {circle_type}")

    signups_data = Signup.query.filter(
        Signup.emp_type.in_(emp_type),
        Signup.circle.in_(circle_type),
    ).all()

    sing_emails = [signup.email for signup in signups_data]
    admin_data = Admin.query.filter(Admin.email.in_(sing_emails)).all()
    admin_ids = [admin.id for admin in admin_data]


    selected_month = request.form.get('selected_month')
    print(f"Got the selected month: {selected_month}")
    start_date, end_date = get_date_range_from_month(selected_month)
    print(f"Got the start date: {start_date} and end date: {end_date}")

    wfh_data = WorkFromHomeApplication.query.filter(
        WorkFromHomeApplication.admin_id.in_(admin_ids),
        WorkFromHomeApplication.status == 'Pending').all()


    if start_date and end_date:
        wfh_another = WorkFromHomeApplication.query.filter(
        WorkFromHomeApplication.admin_id.in_(admin_ids),
        WorkFromHomeApplication.status!='Pending',
        WorkFromHomeApplication.start_date.between(start_date, end_date)).all()
    else:
        wfh_another = []

    return render_template('Manager/wfh_approval.html',admin_data=admin_data,wfh_data=wfh_data,wfh_another=wfh_another)


@manager_bp.route('/claim_approval', methods=['GET', 'POST'])
def claim_approval():
    csrf_token = generate_csrf()
    current_email = current_user.email

    # Fetch manager-related user types and circles
    manager_data = ManagerContact.query.with_entities(
        ManagerContact.user_type, ManagerContact.circle_name
    ).filter(
        (ManagerContact.l1_email == current_email) |
        (ManagerContact.l2_email == current_email) |
        (ManagerContact.l3_email == current_email)
    ).all()

    # Extract distinct user types and circles
    user_types = {m.user_type for m in manager_data}
    circle_names = {m.circle_name for m in manager_data}

    # Get all HR emails based on user_type and circle
    email_list = Signup.query.with_entities(Signup.email).filter(
        Signup.emp_type.in_(user_types),
        Signup.circle.in_(circle_names)
    ).all()
    emails = [email for (email,) in email_list]

    # Get matching admin IDs
    admin_ids = []
    if emails:
        admin_ids = Admin.query.with_entities(Admin.id).filter(Admin.email.in_(emails)).all()
        admin_ids = [admin_id for (admin_id,) in admin_ids]

        start_date = None
        end_date = None
        selected_month = request.form.get('selected_month')
        if selected_month:
            start_date, end_date = get_date_range_from_month(selected_month)

        claims = []
        if admin_ids:
            claims = (
                ExpenseClaimHeader.query
                .filter(
                    ExpenseClaimHeader.admin_id.in_(admin_ids),
                    ExpenseClaimHeader.travel_from_date.between(start_date, end_date)
                )
                .order_by(ExpenseClaimHeader.travel_from_date.desc())
                .all()
            )

    return render_template('Manager/manager_claims.html', claim_data=claims)



@manager_bp.route('/view_items/<int:claim_id>', methods=['GET', 'POST'])
def view_items(claim_id):
    claim = ExpenseClaimHeader.query.get_or_404(claim_id)
    items = ExpenseLineItem.query.filter_by(claim_id=claim_id).all()


    # Split pending and non-pending items
    pending_items = [item for item in items if item.status == "Pending"]
    not_pending_items = [item for item in items if item.status != "Pending"]



    return render_template(
        'Manager/view_items.html',
        claim_item_data=pending_items,
        claim=claim,
        not_pending_items=not_pending_items
    )

# @manager_bp.route('/send_claim_email/<int:claim_id>', methods=['GET', 'POST'])
# def send_claim_email(claim_id):
#     claim = ExpenseClaimHeader.query.get_or_404(claim_id)
#     items = ExpenseLineItem.query.filter_by(claim_id=claim_id).all()

#     subject = f"Expense Claim Submitted by {claim.employee_name}"

#     # Reusable inline styles
#     table_style = "border-collapse: collapse; width: 100%; font-size: 14px;"
#     th_style = "background-color: #f2f2f2; text-align: left;"
#     td_style = "padding: 6px; border: 1px solid #ccc;"

#     body = f"""
#     <html>
#     <body style="font-family: Arial, sans-serif; color: #333;">
#         <p>Hi,</p>
#         <p>An expense claim has been submitted. Below are the details:</p>

#         <h4>Claim Summary:</h4>
#         <table style="{table_style}">
#             <tr><td style="{td_style}"><strong>Employee ID:</strong></td><td style="{td_style}">{claim.emp_id}</td></tr>
#             <tr><td style="{td_style}"><strong>Employee Name:</strong></td><td style="{td_style}">{claim.employee_name}</td></tr>
#             <tr><td style="{td_style}"><strong>Designation:</strong></td><td style="{td_style}">{claim.designation}</td></tr>
#             <tr><td style="{td_style}"><strong>Project Name:</strong></td><td style="{td_style}">{claim.project_name}</td></tr>
#             <tr><td style="{td_style}"><strong>Location:</strong></td><td style="{td_style}">{claim.country_state}</td></tr>
#             <tr><td style="{td_style}"><strong>Travel Dates:</strong></td><td style="{td_style}">{claim.travel_from_date} to {claim.travel_to_date}</td></tr>
#         </table>

#         <h4 style="margin-top: 20px;">Expense Line Items:</h4>
#         <table style="{table_style}">
#             <thead>
#                 <tr style="{th_style}">
#                     <th style="{td_style}">Date</th>
#                     <th style="{td_style}">Description</th>
#                     <th style="{td_style}">Amount</th>
#                     <th style="{td_style}">Currency</th>
#                     <th style="{td_style}">Attachment</th>
#                     <th style="{td_style}">Status</th>
#                 </tr>
#             </thead>
#             <tbody>
#     """
#     for item in items:
#         file_link = (
#             f'<a href="{url_for("static", filename="uploads/" + item.Attach_file, _external=True)}" '
#             f'target="_blank" style="color: #007bff;">Download File</a>'
#             if item.Attach_file else "No attachment"
#         )
#         body += f"""
#             <tr>
#                 <td style="{td_style}">{item.date}</td>
#                 <td style="{td_style}">{item.purpose}</td>
#                 <td style="{td_style}">{item.amount}</td>
#                 <td style="{td_style}">{item.currency}</td>
#                 <td style="{td_style}">{file_link}</td>
#                 <td style="{td_style}">{item.status}</td>
#             </tr>
#         """

#     body += f"""
#             </tbody>
#         </table>

#         <p style="margin-top: 20px;">Click below to review the claim:</p>
#         <p>
#             <a href="https://solviotec.com/"
#                style="background-color: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">
#                Login to HRMS
#             </a>
#         </p>

#         <p>Thanks & Regards,<br>HRMS System</p>
#     </body>
#     </html>
#     """

#     # Recipient emails
#     to_email = "chauguleshubham390@gmail.com"
#     cc_emails = ["examattend87@gmail.com"]

#     # Send email
#     verify_oauth2_and_send_email(current_user, subject, body, to_email, cc_emails)

#     flash('Email sent successfully!', 'success')
#     return redirect(url_for('manager_bp.view_items', claim_id=claim_id))



@manager_bp.context_processor
def inject_badge_counts():
    count_new_wfhs = 0
    count_new_leaves = 0
    claim_item_counts = {}

    if current_user.is_authenticated:
        current_email = current_user.email

        manager_data = ManagerContact.query.filter(
            (ManagerContact.l1_email == current_email) |
            (ManagerContact.l2_email == current_email) |
            (ManagerContact.l3_email == current_email)
        ).all()

        if manager_data:
            emp_types = {m.user_type for m in manager_data}
            circles = {m.circle_name for m in manager_data}

            emails = [e[0] for e in db.session.query(Signup.email).filter(
                Signup.emp_type.in_(emp_types),
                Signup.circle.in_(circles)
            ).all()]

            admin_ids = [a[0] for a in db.session.query(Admin.id).filter(
                Admin.email.in_(emails)
            ).all()]

            if admin_ids:
                # WFH count
                count_new_wfhs = WorkFromHomeApplication.query.filter(
                    WorkFromHomeApplication.admin_id.in_(admin_ids),
                    WorkFromHomeApplication.status == 'Pending'
                ).count()

                # Leave count
                count_new_leaves = LeaveApplication.query.filter(
                    LeaveApplication.admin_id.in_(admin_ids),
                    LeaveApplication.status == 'Pending'
                ).count()

                # Get all headers
                headers = ExpenseClaimHeader.query.filter(
                    ExpenseClaimHeader.admin_id.in_(admin_ids)
                ).all()

                header_ids = [h.id for h in headers]

                # Get all pending items grouped by claim_id
                from sqlalchemy import func
                pending_items = db.session.query(
                    ExpenseLineItem.claim_id,
                    func.count(ExpenseLineItem.id)
                ).filter(
                    ExpenseLineItem.claim_id.in_(header_ids),
                    ExpenseLineItem.status == 'Pending'
                ).group_by(ExpenseLineItem.claim_id).all()

                # Build dictionary: {claim_id: pending_count}
                claim_item_counts = {claim_id: count for claim_id, count in pending_items}

                has_pending_items = bool(count_new_wfhs > 0 or claim_item_counts)
                print(has_pending_items)

    return dict(
        count_new_wfhs=count_new_wfhs,
        count_new_leaves=count_new_leaves,
        claim_item_counts=claim_item_counts,
        has_pending_items=bool(count_new_wfhs > 0 or claim_item_counts)
    )



@manager_bp.route('/separation-approval', methods=['GET', 'POST'])
def separation_approval():
    print("good running")
    pending_separations = []
    not_pending_separations = []

    if current_user.is_authenticated:
        current_email = current_user.email

        # Fetch manager data in a single query
        manager_data = ManagerContact.query.filter(
            (ManagerContact.l1_email == current_email) |
            (ManagerContact.l2_email == current_email) |
            (ManagerContact.l3_email == current_email)
        ).all()

        emp_types = list({m.user_type for m in manager_data})
        circles = list({m.circle_name for m in manager_data})



        # Get all matching signup emails
        signup_emails = db.session.query(Signup.email).filter(
            Signup.emp_type.in_(emp_types),
            Signup.circle.in_(circles)
        ).all()

        email_list = [email[0] for email in signup_emails]

        # Get admin IDs directly
        admin_ids = db.session.query(Admin.id).filter(Admin.email.in_(email_list)).all()
        admin_ids = [aid[0] for aid in admin_ids]

        if admin_ids:
            # Fetch all separations in one go
            all_separations = Resignation.query.filter(
                Resignation.admin_id.in_(admin_ids)
            ).all()

            # Separate pending and not pending in Python
            pending_separations = [r for r in all_separations if r.status == 'Pending']
            not_pending_separations = [r for r in all_separations if r.status != 'Pending']

    return render_template(
        'Manager/separation_approval.html',
        pending_separations=pending_separations,
        not_pending_separations=not_pending_separations
    )


@manager_bp.route('/accept_item/<int:item_id>', methods=['GET', 'POST'])
def accept(item_id):
    item = ExpenseLineItem.query.get_or_404(item_id)
    item.status = "Approved"
    db.session.commit()
    return redirect(url_for('manager_bp.view_items',claim_id=item.claim_id))


@manager_bp.route('/reject_item/<int:item_id>', methods=['GET', 'POST'])
def reject(item_id):
    item = ExpenseLineItem.query.get_or_404(item_id)
    item.status = "Rejected"
    db.session.commit()
    return redirect(url_for('manager_bp.view_items', claim_id=item.claim_id))




@manager_bp.route('/resign-accept/<int:resign_id>', methods=['GET', 'POST'])
def resign_accept(resign_id):

    item = Resignation.query.get_or_404(resign_id)

    item.status = "Approved"
    db.session.commit()

    return redirect(url_for('manager_bp.separation_approval'))


@manager_bp.route('/resign-reject/<int:resign_id>', methods=['GET', 'POST'])
def resign_reject(resign_id):

    item = Resignation.query.get_or_404(resign_id)

    item.status = "Rejected"
    db.session.commit()

    return redirect(url_for('manager_bp.separation_approval'))



@manager_bp.route('/noc_approval', methods=['GET', 'POST'])
def noc_approval():
    current_email = current_user.email
    manager_data = ManagerContact.query.filter(
        (ManagerContact.l1_email == current_email) |
        (ManagerContact.l2_email == current_email) |
        (ManagerContact.l3_email == current_email)
    ).all()
    print(f"manager_data: {manager_data}")

    emp_types = list({m.user_type for m in manager_data})
    circles = list({m.circle_name for m in manager_data})
    print(f"circles: {circles}")
    print(f"emp_types: {emp_types}")

    # Get all matching signup emails
    signup_emails = Signup.query.filter(Signup.emp_type.in_(emp_types),Signup.circle.in_(circles)).all()

    email_list = [email.email for email in signup_emails]
    print(f"signup_emails: {email_list}")
    # Get admin IDs directly
    admin_ids = db.session.query(Admin.id).filter(Admin.email.in_(email_list)).all()
    admin_ids = [aid[0] for aid in admin_ids]
    print(admin_ids)
    noc_data = Noc.query.filter(Noc.admin_id.in_(admin_ids)).all()
    for i in noc_data:
        print(f"got date: {i.noc_date}")

    return render_template('Manager/noc_approval.html', admin_ids=admin_ids, noc_data=noc_data)


@manager_bp.route('/noc_upload/<int:admin_id>', methods=['GET', 'POST'])
def noc_upload(admin_id):
    form = NocUpload()

    try:
        employee = Admin.query.get_or_404(admin_id)
    except Exception:
        flash("Employee details not found.", 'error')
        return redirect(url_for('manager_bp.noc_approval'))

    uploader_data = Signup.query.filter_by(email=current_user.email).first()



    if request.method == 'POST':
        print(f"reuqest method: {request.method}")
        print(f"form validated: {form.validate_on_submit()}")
        print(f"form data: {form.data}")

    file_path = None
    filename = None

    try:
        # Handle optional file upload
        if form.noc_file.data:
            filename = secure_filename(form.noc_file.data.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            form.noc_file.data.save(file_path)

            # Save to database
            new_payslip = Noc_Upload(
                admin_id=employee.id,
                file_path=filename,
                emp_type_uploader = uploader_data.emp_type
            )
            db.session.add(new_payslip)
            db.session.commit()
            return redirect(url_for('manager_bp.noc_upload'))

    except Exception as e:
        flash(f"Error occurred: {str(e)}", 'error')
        return redirect(url_for('manager_bp.noc_approval'))



    return render_template('Manager/noc_upload.html', admin_id=admin_id,form=form)

