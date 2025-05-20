from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models.manager_model import ManagerContact
from .forms.manager import ManagerContactForm  
from website import db

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

