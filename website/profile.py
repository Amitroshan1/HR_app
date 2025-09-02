from flask import render_template, flash, redirect,Blueprint, request, url_for, current_app as app,session
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import os
from .models.family_models import FamilyDetails
from .forms.Emp_details import Employee_Details
from .models.emp_detail_models import Employee
from . import db
from datetime import datetime,date
import calendar
from math import radians, cos, sin, asin, sqrt
from .forms.education import EducationForm,UploadDocForm
from .models.education import Education,UploadDoc
from .forms.family_details import Family_details
from .forms.previous_company import Previous_company
from .models.prev_com import PreviousCompany
from .models.attendance import Punch,LeaveApplication,LeaveBalance,Location,WorkFromHomeApplication
from .forms.attendance import PunchForm,LeaveForm,LocationForm,WorkFromHomeForm
from .models.manager_model import ManagerContact
from .common import verify_oauth2_and_send_email, store_today_work
from .models.Admin_models import Admin
from .models.signup import Signup
from .common import is_within_allowed_location,send_wfh_approval_email_to_managers
from datetime import timedelta
from .utility import punch_time,add_comp_off
from sqlalchemy.exc import SQLAlchemyError

import logging

profile=Blueprint('profile',__name__)




# Configure logging for your app
logging.basicConfig(
    level=logging.DEBUG,  # <-- change to INFO in production
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@profile.route('/emp_details',methods=['GET','POST'])
@login_required
def emp_profile():
    form=Employee_Details()
    return render_template("profile/emp_det.html",form=form)


@profile.route('/emp_det2', methods=['GET', 'POST'])
@login_required
def empl_det():
    employee = Employee.query.filter_by(admin_id=current_user.id).first()
    form = Employee_Details(obj=employee)

    if form.validate_on_submit():
        try:
            # Check if a file is uploaded
            if form.Photo.data:
                file = form.Photo.data
                file_size = file.content_length

                # Validate file size
                if file_size and file_size > 10240000:  # 100 KB
                    flash('File size exceeds 100 KB. Please upload a smaller file.', 'warning')
                else:
                    filename = secure_filename(file.filename)
                    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                    # Save file safely
                    try:
                        file.save(upload_path)
                    except PermissionError:
                        flash('Permission denied: Cannot save uploaded Photo. Please rename the photo.', 'danger')
                        return redirect(url_for('profile.empl_det'))
                    except Exception as e:
                        flash(f'Unexpected error saving file: {str(e)}', 'danger')
                        return redirect(url_for('profile.empl_det'))

                    # Save or update employee data
                    if employee:
                        form.populate_obj(employee)
                        employee.photo_filename = filename
                        db.session.commit()
                        flash('Employee details updated successfully!', 'success')
                    else:
                        new_employee = Employee(
                            admin_id=current_user.id,
                            photo_filename=filename,
                            name=form.name.data,
                            email=form.email.data,
                            father_name=form.father_name.data,
                            mother_name=form.mother_name.data,
                            marital_status=form.marital_status.data,
                            spouse_name=form.spouse_name.data,
                            dob=form.dob.data,
                            emp_id=form.emp_id.data,
                            designation=form.designation.data,
                            mobile=form.mobile.data,
                            gender=form.gender.data,
                            emergency_mobile=form.emergency_mobile.data,
                            caste=form.caste.data,
                            nationality=form.nationality.data,
                            language=form.language.data,
                            religion=form.religion.data,
                            blood_group=form.blood_group.data,
                            permanent_address_line1=form.permanent_address_line1.data,
                            permanent_address_line2=form.permanent_address_line2.data,
                            permanent_address_line3=form.permanent_address_line3.data,
                            permanent_pincode=form.permanent_pincode.data,
                            permanent_district=form.permanent_district.data,
                            permanent_state=form.permanent_state.data,
                            present_address_line1=form.present_address_line1.data,
                            present_address_line2=form.present_address_line2.data,
                            present_address_line3=form.present_address_line3.data,
                            present_pincode=form.present_pincode.data,
                            present_district=form.present_district.data,
                            present_state=form.present_state.data
                        )
                        db.session.add(new_employee)
                        db.session.commit()
                        flash('Employee details saved successfully!', 'success')
            else:
                flash('No photo was uploaded. Please upload a photo.', 'warning')

        except Exception as e:
            # Catch-all error handler for anything unexpected
            flash(f"Something went wrong: {str(e)}", 'danger')

        return redirect(url_for('profile.empl_det'))

    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", category='error')

    return render_template('profile/emp_det.html', form=form)





@profile.route('/family_det')
@login_required
def fam_det():
    family_members = FamilyDetails.query.filter_by(admin_id=current_user.id).all()
    return render_template('profile/E_Family_details.html',family_members = family_members)





@profile.route('/family_details', methods=['GET', 'POST'])
@login_required
def family_details():
    form = Family_details()
    
    if form.validate_on_submit():
        photo_filename = None
        if form.Photo.data:
            photo_filename = secure_filename(form.Photo.data.filename)
            form.Photo.data.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

        new_family_member = FamilyDetails(
            admin_id=current_user.id,
            photo_filename=photo_filename,
            name=form.name.data,
            email=form.email.data,
            dob=form.dob.data,
            age=int(form.age.data),
            relation=form.relation.data,
            occupation=form.occupation.data,
            income=form.Income.data,
            address=form.Address.data,
            remarks  =form.Remarks.data,
            
        )
        
        db.session.add(new_family_member)
        db.session.commit()
        
        flash('Family member details saved successfully!', 'success')
        return redirect(url_for('profile.fam_det'))
   
    return render_template('profile/form_E_FAM.html', form=form)





@profile.route('/previous_company', methods=['GET', 'POST'])
@login_required
def previous_company():
    form = Previous_company()
    if form.validate_on_submit():
        new_company = PreviousCompany(
            admin_id=current_user.id,
            com_name=form.com_name.data,
            designation=form.designation.data,
            doj=form.doj.data,
            dol=form.dol.data,
            reason=form.reason.data,
            salary=form.salary.data,
            uan=form.uan.data,
            pan=form.pan.data,
            contact=form.contact.data,
            name_contact=form.name_contact.data,
            pf_num=form.pf_num.data,
            address=form.address.data
        )
        db.session.add(new_company)
        db.session.commit()
        flash('Previous company details saved successfully!', 'success')
        return redirect(url_for('profile.previous_company'))

    previous_companies = PreviousCompany.query.filter_by(admin_id=current_user.id).all()
    return render_template('profile/previous_company.html', form=form, previous_companies=previous_companies)




@profile.route('/education', methods=['GET', 'POST'])
@login_required
def education():
    form = EducationForm()
    education = Education.query.filter_by(admin_id=current_user.id).all()

    if form.validate_on_submit():
        if form.doc_file.data:
            filename = secure_filename(form.doc_file.data.filename)
            form.doc_file.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None

        new_education = Education(
            admin_id=current_user.id,
            qualification=form.qualification.data,
            institution=form.institution.data,
            board=form.board.data,
            start=form.start.data,
            end=form.end.data,
            marks=form.marks.data,
            doc_file=filename
        )
        db.session.add(new_education)
        db.session.commit()
        flash('Education details added successfully!', 'success')
        return redirect(url_for('profile.education'))

    return render_template('profile/education.html', form=form, education=education)





@profile.route('/delete_education/<int:education_id>', methods=['POST'])
@login_required
def delete_education(education_id):
    education = Education.query.get_or_404(education_id)
    if education.admin_id != current_user.id:
        flash('You do not have permission to delete this item.', 'danger')
        return redirect(url_for('profile.education'))
    
    db.session.delete(education)
    db.session.commit()
    flash('Education detail deleted successfully!', 'success')
    return redirect(url_for('profile.education'))





@profile.route('/upload_doc', methods=['GET', 'POST'])
@login_required
def upload_docs():
    form = UploadDocForm()
    upload_doc = UploadDoc.query.filter_by(admin_id=current_user.id).all()

    if form.validate_on_submit():
        if form.doc_file.data:
            filename = secure_filename(form.doc_file.data.filename)
            form.doc_file.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None

        new_upload_doc = UploadDoc(
            admin_id=current_user.id,
            doc_name=form.doc_name.data,
            doc_number=form.doc_number.data,
            issue_date=form.issue_date.data,
            doc_file=filename
        )
        db.session.add(new_upload_doc)
        db.session.commit()
        flash('Document uploaded successfully!', 'success')
        return redirect(url_for('profile.upload_docs'))

    return render_template('profile/upload_doc.html', form=form, upload_doc=upload_doc)





@profile.route('/delete_document/<int:doc_id>', methods=['POST'])
@login_required
def delete_document(doc_id):
    document = UploadDoc.query.get_or_404(doc_id)
    if document.admin_id != current_user.id:
        flash('You do not have permission to delete this item.', 'danger')
        return redirect(url_for('profile.upload_docs'))
    
   
    if document.doc_file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.doc_file)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.session.delete(document)
    db.session.commit()
    flash('Document deleted successfully!', 'success')
    return redirect(url_for('profile.upload_docs'))




def haversine(user_lat, user_lon, saved_lat, saved_lon):
    """
    Calculate distance between two (lat, lon) points in meters.
    """
    # Earth radius in meters
    R = 6371000  

    logger.debug(f"[HAVERSINE INPUT] user=({user_lat}, {user_lon}), saved=({saved_lat}, {saved_lon})")

    # Convert degrees to radians
    dlat = radians(saved_lat - user_lat)
    dlon = radians(saved_lon - user_lon)

    a = sin(dlat / 2) ** 2 + cos(radians(user_lat)) * cos(radians(saved_lat)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    distance = R * c

    logger.debug(f"[HAVERSINE RESULT] Distance={distance:.2f}m")
    return distance


def is_near_saved_location(user_lat, user_lon, locations):
    logger.debug(f"[DEBUG] User location: lat={user_lat}, lon={user_lon}")

    for loc in locations:
        distance = haversine(user_lat, user_lon, loc.latitude, loc.longitude)
        logger.debug(f"[CHECK] Location(id={loc.id}, name={loc.name}) "
                     f"Lat={loc.latitude}, Lon={loc.longitude}, "
                     f"Radius={loc.radius}, Distance={distance:.2f}m")

        if distance <= loc.radius:
            logger.info(f"✅ User is within radius of location {loc.name}")
            return True

    logger.warning("❌ No matching location found")
    return False

def check_leave():
    today = date.today()
    leave_data = LeaveApplication.query.filter(
        LeaveApplication.admin_id == current_user.id,
        LeaveApplication.start_date <= today,
        LeaveApplication.end_date >= today,
        LeaveApplication.status == 'Approved'
    ).all()

    for leave in leave_data:
        current_date = leave.start_date
        while current_date <= leave.end_date:
            if current_date == today:
                return True  # User is on leave
            current_date += timedelta(days=1)

    return False  # Not on leave

def check_wfh():
    today = date.today()
    approved = WorkFromHomeApplication.query.filter(
        WorkFromHomeApplication.admin_id == current_user.id,
        WorkFromHomeApplication.start_date <= today,
        WorkFromHomeApplication.end_date >= today,
        WorkFromHomeApplication.status == 'Approved'
    ).first()
    return True if approved else False







@profile.route('/punch', methods=['GET', 'POST'])
@login_required
def punch():
    form = PunchForm()
    today = date.today()

    punch = Punch.query.filter_by(admin_id=current_user.id, punch_date=today).first()
    selected_month = request.args.get('month', today.month, type=int)
    selected_year = request.args.get('year', today.year, type=int)

    
    calendar.setfirstweekday(calendar.MONDAY)
    first_day = date(selected_year, selected_month, 1)
    last_day = first_day.replace(day=calendar.monthrange(selected_year, selected_month)[1])

    punches = Punch.query.filter(
        Punch.admin_id == current_user.id,
        Punch.punch_date.between(first_day, last_day)
    ).all()

    punch_data = {p.punch_date: p for p in punches}

    if form.validate_on_submit():
        lat = request.form.get('lat', type=float)
        lon = request.form.get('lon', type=float)
        is_wfh = request.form.get('wfh') == 'on'

        logger.debug(f"Punch attempt by user {current_user.email}: lat={lat}, lon={lon}, WFH={is_wfh}")

        locations = Location.query.all()
        logger.debug(f"Loaded {len(locations)} saved locations from DB")

        is_near_location = False
        if lat is not None and lon is not None:
            is_near_location = is_near_saved_location(lat, lon, locations)

        logger.debug(f"is_near_location result: {is_near_location}")

        if not is_near_location and not is_wfh:
            logger.warning(f"User {current_user.email} tried punching outside location without WFH")
            flash("You are not near any authorized location and 'Work From Home' is not selected.", "danger")
            return redirect(url_for('profile.punch'))

        if form.punch_in.data:
            if check_leave():
                flash("You are not allowed to punch on this day because you are on leave", "danger")
                return redirect(request.url)  # Stop further execution
            elif is_wfh and not check_wfh():
                flash("WFM Mode access is restricted until your request is approved.", "danger")
                return redirect(request.url)
            elif punch and punch.punch_in:
                flash('Already punched in today!', 'danger')
            else:
                if not punch:
                    punch = Punch(
                        admin_id=current_user.id,
                        punch_date=today,
                        is_wfh=is_wfh,
                        lat=lat,
                        lon=lon
                    )
                punch.punch_in = datetime.now().time()
                punch.is_wfh = is_wfh
                punch.lat = lat
                punch.lon = lon

                db.session.add(punch)
                db.session.commit()
                flash('Punched in successfully!', 'warning')


        elif form.punch_out.data:

            if check_leave():

                flash("You are not allowed to punch on this day because you are on leave", "danger")

                return redirect(request.url)

            elif is_wfh and not check_wfh():

                flash("WFM Mode access is restricted until your request is approved.", "danger")

                return redirect(request.url)

            if not punch or not punch.punch_in:

                flash('You need to punch in first!', 'danger')

            else:

                # Set punch-out time

                punch.punch_out = datetime.now().time()
                punch_time(current_user.id)  # Update today's work time
                db.session.commit()

                # ✅ Check if today is Sunday
                if datetime.today().weekday() == 6:  # Sunday
                    user = Signup.query.filter_by(email=current_user.email).first()
                    add_comp_off(user.id)
                    print("Comp Off added for Sunday work!")
                flash(f'Punch out successful! Work duration recorded: {punch.today_work}', 'success')

    
    # Suppose punch.total_work is datetime.time (HH:MM:SS)
    if punch and punch.today_work:
        total_work_time = punch.today_work
        total_work_td = timedelta(
            hours=total_work_time.hour,
            minutes=total_work_time.minute,
            seconds=total_work_time.second
        )

        is_full_day = total_work_td >= timedelta(hours=8, minutes=15)  # 8 hours and 30 minutes
    else:
        is_full_day = False


    
    last_day = calendar.monthrange(selected_year, selected_month)[1]

    leave_records = LeaveApplication.query.filter(
        LeaveApplication.admin_id == current_user.id,
        LeaveApplication.start_date <= date(selected_year, selected_month, last_day),
        LeaveApplication.end_date >= date(selected_year, selected_month, 1),
        LeaveApplication.status == 'Approved'
    ).all()

    # Collect all leave days
    leave_days = set()
    for leave in leave_records:
        current_day = leave.start_date
        while current_day <= leave.end_date:
            leave_days.add(current_day)
            current_day += timedelta(days=1)

    return render_template(
        'profile/punch.html',
        form=form,
        punch=punch,
        punch_data=punch_data,
        today=today,
        selected_month=selected_month,
        selected_year=selected_year,
        calendar=calendar,
        is_full_day=is_full_day,
        leave_days=leave_days
    )



  # adjust the import path if needed

@profile.route('/submit-wfh', methods=['GET', 'POST'])
@login_required
def submit_wfh():
    form = WorkFromHomeForm()
    

    if form.validate_on_submit():
        
        wfh_application = WorkFromHomeApplication(
            admin_id=current_user.id,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reason=form.reason.data,
            status='Pending',
            created_at=datetime.now()
        )
        db.session.add(wfh_application)
        db.session.commit()
        

        try:
            success = send_wfh_approval_email_to_managers(current_user, wfh_application)
            if success:
                flash('WFH request submitted and email sent for approval.', 'success')
            else:
                flash('WFH submitted, but failed to send approval email.', 'warning')
        except Exception as e:
            app.logger.error(f"Email send failed: {e}")
            flash('WFH submitted, but error occurred while sending approval email.', 'danger')

        return redirect(url_for('profile.submit_wfh'))

    if request.method == 'POST':
        flash(f"Form validation failed: {form.errors}", "danger")

    user_wfh_applications = WorkFromHomeApplication.query.filter_by(
        admin_id=current_user.id
    ).order_by(WorkFromHomeApplication.created_at.desc()).all()

    return render_template(
        'profile/submit_wfh.html',
        form=form,
        wfh_applications=user_wfh_applications
    )


@profile.route('/manage-location', methods=['GET', 'POST'])
@login_required
def manage_locations():
    form = LocationForm()
    locations = Location.query.all()

    if form.validate_on_submit():
        new_loc = Location(
            name=form.name.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            radius=form.radius.data
        )
        db.session.add(new_loc)
        db.session.commit()
        flash('Location added successfully!', 'success')
        return redirect(url_for('profile.manage_locations'))

    return render_template('HumanResource/manage_locations.html', form=form, locations=locations)


@profile.route('/delete-location/<int:location_id>', methods=['POST'])
@login_required
def delete_location(location_id):
    loc = Location.query.get_or_404(location_id)
    db.session.delete(loc)
    db.session.commit()
    flash('Location deleted successfully!', 'warning')
    return redirect(url_for('profile.manage_locations'))


@profile.route('/apply-leave', methods=['GET', 'POST'])
@login_required  # Ensure the user is logged in
def apply_leave():
    """ Route to apply for leave with OAuth2 authentication and email notification """

    # Ensure user is authenticated
    if not current_user.is_authenticated:
        flash("Please log in using Microsoft OAuth.", "danger")
        return redirect(url_for("auth.E_homepage"))

    user_email = current_user.email  # Fetch email directly from the authenticated user

    # Fetch employee record from the database
    emp = Admin.query.filter_by(email=user_email).first()
    employee = Signup.query.filter_by(email=user_email).first()
    if not employee:
        flash("Employee record not found.", "danger")
        return redirect(url_for("auth.logout"))

    leave_balance = LeaveBalance.query.filter_by(signup_id=employee.id).first()
    form = LeaveForm()


    deducted_days = 0.0  # This will store how much was actually cut from balances
    extra_leave = 0.0

    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data
        leave_type = form.leave_type.data
        leave_days = (end_date - start_date).days + 1
        reason = form.reason.data

     # Variable to track extra leave days

         # Still useful for alerts or UI

        # Privilege Leave
        if leave_type == 'Privilege Leave':
            if leave_days > leave_balance.privilege_leave_balance:
                extra_leave = leave_days - leave_balance.privilege_leave_balance
                deducted_days = leave_balance.privilege_leave_balance
                leave_balance.privilege_leave_balance = 0
            else:
                deducted_days = leave_days
                leave_balance.privilege_leave_balance -= leave_days

        # Casual Leave
        elif leave_type == 'Casual Leave':
            if leave_days > 2:
                flash('You cannot apply for more than 2 days of Casual Leave.', 'warning')
                return redirect(url_for('profile.apply_leave'))

            if leave_days > leave_balance.casual_leave_balance:
                flash('Not enough Casual Leave. Please apply under Privilege Leave instead.', 'danger')
                return redirect(url_for('profile.apply_leave'))

            deducted_days = leave_days
            leave_balance.casual_leave_balance -= leave_days

        # Half Day Leave
        elif leave_type == "Half Day Leave":
            if leave_days > 1:
                flash('Half Day Leave can only be applied for one day.', 'danger')
                return redirect(url_for('profile.apply_leave'))

            deducted_days = 0.5
            if leave_balance.casual_leave_balance >= 0.5:
                leave_balance.casual_leave_balance -= 0.5
            elif leave_balance.privilege_leave_balance >= 0.5:
                leave_balance.privilege_leave_balance -= 0.5
                flash('0.5 day deducted from Privilege Leave due to insufficient Casual Leave.', 'info')
            else:
                flash('Not enough balance. 0.5 day marked as Extra Leave.', 'warning')
                extra_leave = 0.5

        # Compensatory Leave
        elif leave_type == "Compensatory Leave":
            if not leave_balance or leave_balance.compensatory_leave_balance <= 0:
                flash('You do not have any Compensatory Leave balance available.', 'danger')
                return redirect(url_for('profile.apply_leave'))

            if leave_days > 2:
                flash('You can apply for a maximum of 2 Compensatory Leave days at once.', 'danger')
                return redirect(url_for('profile.apply_leave'))

            if leave_days > leave_balance.compensatory_leave_balance:
                flash(f'You only have {leave_balance.compensatory_leave_balance} Compensatory Leave days available.', 'danger')
                return redirect(url_for('profile.apply_leave'))

            leave_balance.compensatory_leave_balance -= leave_days
            flash('Please ask Lead/Manager for approval of Compensatory Leave.', 'info')

        db.session.commit()



        # Save leave application
        leave_application = LeaveApplication(
            admin_id=emp.id,
            leave_type=leave_type,
            reason=reason,
            start_date=start_date,
            end_date=end_date,
            status='Pending',
            deducted_days=deducted_days        )
        db.session.add(leave_application)
        db.session.commit()

        # Email notification
        manager_contact = ManagerContact.query.filter_by(circle_name=employee.circle,
                                                         user_type=employee.emp_type).first()
        department_email = 'hr@saffotech.com'
        cc_emails = []
        if manager_contact:
            cc_emails += [manager_contact.l2_email, manager_contact.l3_email]

        subject = f"New Leave Application: {leave_type}"
        body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <p>Hi,</p>
                <p>Greetings!</p>
                <p>Dear Sir/Madam,</p>

                <p>Please find the details of the leave application below:</p>

                <table style="border-collapse: collapse; width: 100%; font-size: 14px; line-height: 1.2;">
                <tr>
                    <td style="padding: 4px 2px; margin: 0;"><strong>Employee Name:</strong></td>
                    <td style="padding: 4px 8px; margin: 0;">{employee.first_name}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 8px; margin: 0;"><strong>Leave Type:</strong></td>
                    <td style="padding: 4px 8px; margin: 0;">{leave_type}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 8px; margin: 0;"><strong>Reason:</strong></td>
                    <td style="padding: 4px 8px; margin: 0;">{reason}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 8px; margin: 0;"><strong>Start Date:</strong></td>
                    <td style="padding: 4px 8px; margin: 0;">{start_date}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 8px; margin: 0;"><strong>End Date:</strong></td>
                    <td style="padding: 4px 8px; margin: 0;">{end_date}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 8px; margin: 0;"><strong>Total Days:</strong></td>
                    <td style="padding: 4px 8px; margin: 0;">{leave_days}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 8px; margin: 0;"><strong>Privilege Leave Balance After Deduction:</strong></td>
                    <td style="padding: 4px 8px; margin: 0;">{leave_balance.privilege_leave_balance}</td>
                </tr>
                </table>
            """

        if extra_leave > 0:
                body += f"""
                <p style="color: red;"><strong>⚠️ Extra Leave Days taken :</strong> {extra_leave} (Not covered by Privilege Leave)</p>
                """

        body += f"""
                <p>
                <a href="https://solviotec.com/" style="background-color: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">Login to HRMS to Approve</a>
                </p>

                <p>Thanks & Regards,<br>
                {employee.first_name}</p>
            </body>
            </html>
            """
        verify_oauth2_and_send_email(emp, subject, body, department_email, cc_emails)
        flash('Your leave application has been submitted & Mail Sent for approval.', 'success')
        return redirect(url_for('profile.apply_leave'))

    user_leaves = LeaveApplication.query.filter_by(admin_id=emp.id).all()

    return render_template('profile/apply_leave.html', form=form,
                            leave_balance=leave_balance,
                            deducted_days=deducted_days,
                            user_leaves=user_leaves)


@profile.route('/approve-leave/<int:leave_id>', methods=['GET'])
def approve_leave(leave_id):
    leave_application = LeaveApplication.query.get_or_404(leave_id)
    leave_application.status = 'Approved'
    db.session.commit()
    flash('Leave application has been approved.', 'success')
    return redirect(url_for('manager_bp.manager_access'))


@profile.route('/reject-leave/<int:leave_id>', methods=['GET'])
def reject_leave(leave_id):
    try:
        leave_app_data = LeaveApplication.query.get_or_404(leave_id)

        # Avoid double rejection
        if leave_app_data.status == 'Rejected':
            flash("This leave application has already been rejected.", 'warning')
            return redirect(url_for('manager_bp.manager_access'))

        # Get Admin and Signup info
        admin = Admin.query.get(leave_app_data.admin_id)
        signup = Signup.query.filter_by(email=admin.email).first()
        leave_balance = LeaveBalance.query.filter_by(signup_id=signup.id).first()

        # Get deducted days safely
        deducted_days = leave_app_data.deducted_days or 0.0

        # Restore only what was actually deducted
        if deducted_days > 0:
            leave_balance.restore_leave(leave_app_data.leave_type, deducted_days)

        # Update leave status
        leave_app_data.status = 'Rejected'
        db.session.commit()

        flash('❌ Leave application has been rejected and leave balance restored.', 'danger')

    except SQLAlchemyError as db_err:
        db.session.rollback()
        flash(f"Database error: {str(db_err)}", 'danger')
    except Exception as e:
        flash(f"Unexpected error: {str(e)}", 'danger')

    return redirect(url_for('manager_bp.manager_access'))






@profile.route('/approve-wfh/<int:wfh_id>', methods=['GET'])
def approve_wfh(wfh_id):
    wfh_app_data = WorkFromHomeApplication.query.get_or_404(wfh_id)
    wfh_app_data.status = 'Approved'
    db.session.commit()
    flash('Work From Home Application has been approved.', 'success')
    return redirect(url_for('manager_bp.wfh_approval'))





@profile.route('/reject-wfh/<int:wfh_id>', methods=['GET'])
def reject_wfh(wfh_id):
    wfh_app_data = WorkFromHomeApplication.query.get_or_404(wfh_id)
    wfh_app_data.status = 'Rejected'
    db.session.commit()
    flash('Work From Home Application has been rejected.', 'success')
    return redirect(url_for('manager_bp.wfh_approval'))




 




