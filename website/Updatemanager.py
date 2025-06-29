from flask import Blueprint, render_template, request, flash, redirect, url_for,current_app
from .models.manager_model import ManagerContact
from .models.expense import ExpenseClaimHeader, ExpenseLineItem
from .forms.expense_form import ExpenseClaimForm
from .forms.manager import ManagerContactForm  
from website import db
import os
from werkzeug.utils import secure_filename



manager_bp = Blueprint('manager_bp', __name__)


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







@manager_bp.route('/claim-expense', methods=['GET', 'POST'])
def claim_expense():
    form = ExpenseClaimForm()
    if form.validate_on_submit():
        try:
            # Create header entry
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
            db.session.flush()  # get header.id

            upload_folder = os.path.join(current_app.root_path, 'static/uploads/')
            os.makedirs(upload_folder, exist_ok=True)

            # Loop through line items
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
                    Attach_file=filename  # Add this column in model
                )
                db.session.add(item)

            db.session.commit()
            flash('Expense claim submitted successfully!', 'success')
            return redirect(url_for('manager_bp.claim_expense'))

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", 'danger')
            current_app.logger.error(f"Error in claim_expense: {e}")

    return render_template('OTP/claim_expense.html', form=form)
