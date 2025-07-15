from pickletools import read_stringnl_noescape

from flask import Blueprint, render_template, request, flash, redirect, url_for,current_app

from .models.Admin_models import Admin
from .models.manager_model import ManagerContact
from .models.expense import ExpenseClaimHeader, ExpenseLineItem
from .forms.expense_form import ExpenseClaimForm
from .forms.manager import ManagerContactForm  
from website import db
import os
from werkzeug.utils import secure_filename
from .common import send_claim_submission_email
from flask_login import current_user, login_required
from .models.signup import Signup
from .models.attendance import LeaveApplication,WorkFromHomeApplication
from .models.expense import ExpenseClaimHeader,ExpenseLineItem

manager_bp = Blueprint('manager_bp', __name__)

@login_required
@manager_bp.route('/manager_contact', methods=['GET', 'POST'])
def manager_contact():
    form = ManagerContactForm()
    if form.validate_on_submit():
        existing_contact = ManagerContact.query.filter_by(circle_name=form.circle_name.data, user_type=form.user_type.data).first()
        if existing_contact:
            existing_contact.l1_name = form.l1_name.data if form.l1_name.data else None
            existing_contact.l1_mobile = form.l1_mobile.data if form.l1_mobile.data else None
            existing_contact.l1_email = form.l1_email.data if form.l1_email.data else None
            existing_contact.l2_name = form.l2_name.data
            existing_contact.l2_mobile = form.l2_mobile.data
            existing_contact.l2_email = form.l2_email.data
            existing_contact.l3_name = form.l3_name.data
            existing_contact.l3_mobile = form.l3_mobile.data
            existing_contact.l3_email = form.l3_email.data
            db.session.commit()
            flash('Manager contact updated successfully', 'success')
        else:
            new_contact = ManagerContact(
                circle_name=form.circle_name.data,
                user_type=form.user_type.data,
                l1_name=form.l1_name.data if form.l1_name.data else None,
                l1_mobile=form.l1_mobile.data if form.l1_mobile.data else None,
                l1_email=form.l1_email.data if form.l1_email.data else None,
                l2_name=form.l2_name.data,
                l2_mobile=form.l2_mobile.data,
                l2_email=form.l2_email.data,
                l3_name=form.l3_name.data,
                l3_mobile=form.l3_mobile.data,
                l3_email=form.l3_email.data
            )
            db.session.add(new_contact)
            db.session.commit()
            flash('Manager contact added successfully', 'success')
        return redirect(url_for('manager_bp.manager_contact'))
    return render_template('HumanResource/manager.html', form=form)






@login_required
@manager_bp.route('/claim-expense', methods=['GET', 'POST'])
def claim_expense():
    form = ExpenseClaimForm()
    if form.validate_on_submit():
        print("Form submitted successfully")
        try:
            # Save header
            header = ExpenseClaimHeader(
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
    current_email = current_user.email

    # Get all departments the manager is handling
    manager_data = ManagerContact.query.filter(
        (ManagerContact.l1_email == current_email) |
        (ManagerContact.l2_email == current_email) |
        (ManagerContact.l3_email == current_email)
    ).all()

    # Collect user types and circles (may contain duplicates, so use set if needed)
    users_type_list = [m.user_type for m in manager_data]
    circle_name_list = [m.circle_name for m in manager_data]

    # Get all HRs based on user_type and circle
    signup_data = Signup.query.filter(
        Signup.emp_type.in_(users_type_list),
        Signup.circle.in_(circle_name_list)
    ).all()

    # Extract email list
    email_list = [i.email for i in signup_data]

    # Get matching Admins
    data_admin = Admin.query.filter(Admin.email.in_(email_list)).all()
    admin_ids = [a.id for a in data_admin]

    # Get Leave Applications
    leave_apps = LeaveApplication.query.filter(LeaveApplication.admin_id.in_(admin_ids),LeaveApplication.status=='Pending').all()
    leave_data = [i for i in leave_apps]

    # for get not pending data means approved and rejected
    leave_another = LeaveApplication.query.filter(LeaveApplication.admin_id.in_(admin_ids),LeaveApplication.status!='Pending').all()


    return render_template(
        'Manager/manager.html',
        users_type_list=users_type_list,
        circle_name_list=circle_name_list,
        signup_data = signup_data,
        leave_apps=leave_apps,
        leave_another = leave_another

    )
@manager_bp.route('wfh_approval', methods=['GET', 'POST'])
def wfh_approval():
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

    wfh_data = WorkFromHomeApplication.query.filter(
        WorkFromHomeApplication.admin_id.in_(admin_ids),
        WorkFromHomeApplication.status=='Pending',
    ).all()

    wfh_another = WorkFromHomeApplication.query.filter(
        WorkFromHomeApplication.admin_id.in_(admin_ids),
        WorkFromHomeApplication.status!='Pending',
    ).all()




    return render_template('Manager/wfh_approval.html',admin_data=admin_data,wfh_data=wfh_data,wfh_another=wfh_another)


@manager_bp.route('/claim_approval', methods=['GET', 'POST'])
def claim_approval():
    claims = ExpenseClaimHeader.query.order_by(
        ExpenseClaimHeader.travel_from_date.desc()
    ).all()
    return render_template('Manager/manager_claims.html', claim_data=claims)


@manager_bp.route('/view_items/<int:claim_id>', methods=['GET', 'POST'])
def view_items(claim_id):
    print(f"view claims: {claim_id}")
    claim = ExpenseClaimHeader.query.get_or_404(claim_id)
    print(claim.id)


    # Filter items in one go
    items = ExpenseLineItem.query.filter_by(claim_id=claim_id).all()
    for i in items:
        print(f" view3 item: {i.claim_id}")

    # Split pending and non-pending items
    pending_items = [item for item in items if item.status == "Pending"]

    not_pending_items = [item for item in items if item.status != "Pending"]

    return render_template(
        'Manager/view_items.html',
        claim_item_data=pending_items,
        claim=claim,
        not_pending_items=not_pending_items
    )


@manager_bp.route('/accept_item/<int:item_id>', methods=['GET', 'POST'])
def accept(item_id):
    print(f"accept item: {item_id}")
    item = ExpenseLineItem.query.get_or_404(item_id)

    item.status = "Approved"
    db.session.commit()
    print(f"item id got accepted: {item.claim_id}")
    return redirect(url_for('manager_bp.view_items',claim_id=item.claim_id))


@manager_bp.route('/reject_item/<int:item_id>', methods=['GET', 'POST'])
def reject(item_id):
    print(f"reject item: {item_id}")
    item = ExpenseLineItem.query.get_or_404(item_id)
    print(f"Item ID: {item.id}, Belongs to Claim ID: {item.claim_id}, Status: {item.status}")

    item.status = "Rejected"
    db.session.commit()
    return redirect(url_for('manager_bp.view_items', claim_id=item.claim_id))