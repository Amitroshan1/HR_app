import os

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf

from.forms.seperation import ResignationForm
from .models.seperation import Resignation, Noc,Noc_Upload
from . import db
from .models.Admin_models import Admin
from .models.signup import Signup
from .common import send_resignation_email,send_rollback_resignation_email,noc_store
from .models.manager_model import ManagerContact
from datetime import date, timedelta    
from .forms.seperation import NocForms
from .common import send_noc_email
from flask import send_file

offboard = Blueprint('offboard', __name__)


@offboard.route('/seperation', methods=['GET', 'POST'])
@login_required
def apply_resignation():
    form = ResignationForm()
    user = Admin.query.get(current_user.id)
    signup_date = Signup.query.filter_by(email=user.email).first()
    manager = ManagerContact.query.filter_by(
        circle_name=signup_date.circle,
        user_type=signup_date.emp_type
    ).first()
    today = date.today().isoformat()
    reg_data = Resignation.query.filter_by(admin_id=current_user.id).first()

    if reg_data:
        if request.method == 'POST':
            flash("You have already submitted a resignation request.", "info")
        return render_template(
            'offboard/seperation.html',
            form=form,
            user=user,
            signup_date=signup_date,
            reg_data=reg_data,
            manager=manager,
            today=today
        )

    if form.validate_on_submit():
        resignation = Resignation(
            admin_id=current_user.id,
            resignation_date=form.resignation_date.data,
            reason=form.reason.data
        )

        # Try sending the email before committing to DB
        try:
            mail_sent = send_resignation_email(user, resignation, signup_date, manager)
            if mail_sent:
                db.session.add(resignation)
                db.session.commit()
                flash('Your resignation has been submitted and Mail is sent.', 'success')
                return redirect(url_for('offboard.apply_resignation'))
            else:
                flash("Resignation email could not be sent. Please try again later.", "error")
        except Exception:
            flash("Unable to submit resignation. Please check your internet connection or contact IT support.", "error")


    return render_template(
        'offboard/seperation.html',
        form=form,
        user=user,
        signup_date=signup_date,
        reg_data=None,
        manager=manager,
        today=today
    )



@offboard.route('/rollback_resignation', methods=['GET'])
@login_required
def rollback_resignation():
    resignation = Resignation.query.filter_by(admin_id=current_user.id).first()
    
    if not resignation:
        flash('No resignation found to rollback.', 'error')
        return redirect(url_for('offboard.apply_resignation'))

    try:
        email_sent = send_rollback_resignation_email(current_user)
        if email_sent:
            db.session.delete(resignation)
            db.session.commit()
            flash('Your resignation has been rolled back successfully.', 'success')
        else:
            flash("Could not send rollback notification. Please try again later.", "error")
    except Exception:
        flash("Unable to rollback resignation. Please check your internet connection or contact IT support.", "error")

    return redirect(url_for('offboard.apply_resignation'))


# --noc-route--
@offboard.route('/apply_noc', methods=['GET', 'POST'])
@login_required
def apply_noc():
    form = NocForms()
    user = Admin.query.get(current_user.id)
    signup_date = Signup.query.filter_by(email=user.email).first()
    today = date.today().isoformat()

    # ✅ Check if NOC already exists
    noc_data = Noc.query.filter_by(admin_id=current_user.id).first()

    # ✅ Fetch latest resignation details
    resignation = Resignation.query.filter_by(admin_id=current_user.id).order_by(
        Resignation.applied_on.desc()
    ).first()
    uploaded_nocs = Noc_Upload.query.filter_by(admin_id=current_user.id).all()

    if noc_data:
        if request.method == 'POST':
            flash("You have already submitted a NOC request.", "info")
        return render_template(
            "offboard/noc.html",
            form=form,
            user=user,
            signup_date=signup_date,
            noc_data=noc_data,
            resignation=resignation,
            today=today,
            uploaded_nocs=uploaded_nocs
        )

    if form.validate_on_submit():
        # ✅ Save new NOC request
        new_noc = Noc(
            admin_id=current_user.id,
            noc_date=form.noc_form_date.data,
            status="Pending"
        )
        db.session.add(new_noc)
        db.session.commit()

        # ✅ Fetch manager emails dynamically
        manager_contacts = ManagerContact.query.filter_by(circle_name=signup_date.circle).all()
        manager_emails = []
        for m in manager_contacts:
            if m.l1_email:
                manager_emails.append(m.l1_email)
            if m.l2_email:
                manager_emails.append(m.l2_email)

        # ✅ Send email with resignation info
        send_noc_email(user, form.emp_type.data, form.noc_form_date.data, manager_emails, resignation)

        flash("NOC request submitted and email sent to HR with CC to selected departments.", "success")
        return redirect(url_for("offboard.apply_noc"))

    return render_template(
        "offboard/noc.html",
        form=form,
        user=user,
        signup_date=signup_date,
        noc_data=None,
        resignation=resignation,
        today=today,
        uploaded_nocs=uploaded_nocs
    )



@offboard.route('/hr-noc', methods=['GET', 'POST'])
@login_required
def hr_noc():
    csrf_token = generate_csrf()
    if request.method == 'POST':
        admin_id = request.form.get('admin_id')
        file = request.files.get('noc_file')
        if admin_id and file:
            success, message = noc_store(admin_id, file, current_user.email)
            flash(message, "success" if success else "error")
            return redirect(url_for("offboard.hr_noc"))
    noc_data = Noc.query.all()

    return render_template('offboard/hr_noc_upload.html',noc_data=noc_data,csrf_token=csrf_token)


@offboard.route('/acc-noc', methods=['GET', 'POST'])
@login_required
def acc_noc():
    csrf_token = generate_csrf()
    if request.method == 'POST':
        admin_id = request.form.get('admin_id')
        file = request.files.get('noc_file')
        if admin_id and file:
            success, message = noc_store(admin_id, file, current_user.email)
            
            flash(message, "success" if success else "error")
            return redirect(url_for("offboard.acc_noc"))
    noc_data = Noc.query.all()
    return render_template('offboard/acc_noc_upload.html',noc_data=noc_data,csrf_token=csrf_token)


@offboard.route("/download_noc/<int:file_id>")
@login_required
def download_noc(file_id):
    noc_file = Noc_Upload.query.get_or_404(file_id)

    if noc_file.admin_id != current_user.id:
        flash("Unauthorized!", "danger")
        return redirect(url_for("offboard.apply_noc"))

    # ✅ FIX: remove duplicate "website"
    upload_folder = os.path.join(current_app.root_path, "static", "uploads")
    full_path = os.path.join(upload_folder, noc_file.file_path)

   

    if not os.path.exists(full_path):
        flash(f"File not found: {full_path}", "danger")
        return redirect(url_for("offboard.apply_noc"))

    return send_file(full_path, as_attachment=True)
