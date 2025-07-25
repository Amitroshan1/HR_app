from flask import Blueprint,render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from.forms.seperation import ResignationForm
from .models.seperation import Resignation
from . import db
from .models.Admin_models import Admin
from .models.signup import Signup
from .common import send_resignation_email,send_rollback_resignation_email
from .models.manager_model import ManagerContact
from datetime import date, timedelta    


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

