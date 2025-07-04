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
from .models.attendance import Punch,LeaveApplication,LeaveBalance,Location
from .forms.attendance import PunchForm,LeaveForm,LocationForm
from .models.manager_model import ManagerContact
from .common import verify_oauth2_and_send_email
from .models.Admin_models import Admin
from .models.signup import Signup
from .common import is_within_allowed_location
from datetime import timedelta  

profile=Blueprint('profile',__name__)


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
        # Check if a file is uploaded
        if form.Photo.data:
            # Get the file size
            file = form.Photo.data
            file_size = file.content_length  # Get the file size in bytes

            # Check if file size exceeds 100 KB (102400 bytes)
            if file_size > 102400:  # 100 KB
                flash('File size exceeds 100 KB. Please upload a smaller file.', 'warning')
            else:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # Continue processing...
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
            # Handle case where no file was uploaded
            flash('No photo was uploaded. Please upload a photo.', 'warning')

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




def is_near_saved_location(user_lat, user_lon, locations):
    def haversine(lat1, lon1, lat2, lon2):
        # Earth radius in meters
        R = 6371000  
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
        c = 2 * asin(sqrt(a))
        return R * c

    for loc in locations:
        distance = haversine(user_lat, user_lon, loc.latitude, loc.longitude)
        if distance <= loc.radius:
            return True
    return False


def check_leave():
    today = date.today()
    leave_data = LeaveApplication.query.filter(
        LeaveApplication.admin_id == current_user.id,
        LeaveApplication.start_date <= today,
        LeaveApplication.end_date >= today
    ).all()

    for leave in leave_data:
        current_date = leave.start_date
        while current_date <= leave.end_date:
            if current_date == today:
                return True  # User is on leave
            current_date += timedelta(days=1)

    return False  # Not on leave


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
        # print(lat, lon, is_wfh)
        # Load all saved locations from the DB
        locations = Location.query.all()
        # print(locations)
        # Check if the user is near any saved location
        is_near_location = False
        if lat is not None and lon is not None:
            is_near_location = is_near_saved_location(lat, lon, locations)

        if not is_near_location and not is_wfh:
            flash("You are not near any authorized location and 'Work From Home' is not selected.", "danger")
            return redirect(url_for('profile.punch'))

        if form.punch_in.data:
            if check_leave():
                flash("You are not allowed to punch on this day because you are on leave", "danger")
                return redirect(request.url)  # Stop further execution
            # if check_leave()
            # Step 2: Handle Punch logic
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

            if not punch or not punch.punch_in:
                flash('You need to punch in first!', 'danger')
            else:
                punch.punch_out = datetime.now().time()
                db.session.commit()
                flash('Punch out time updated successfully!', 'success')

    return render_template(
        'profile/punch.html',
        form=form,
        punch=punch,
        punch_data=punch_data,
        today=today,
        selected_month=selected_month,
        selected_year=selected_year,
        calendar=calendar
    )




@profile.route('/manage-location\s', methods=['GET', 'POST'])
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

    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data
        leave_type = form.leave_type.data
        leave_days = (end_date - start_date).days + 1
        reason = form.reason.data

        extra_leave = 0  # Variable to track extra leave days

        # Validate leave balances
        if leave_type == 'Casual Leave' and leave_days > leave_balance.casual_leave_balance:
            flash('You do not have enough Casual Leave balance Try Privilege Leave.', 'danger')
            return redirect(url_for('profile.apply_leave'))

        if leave_type == 'Privilege Leave':
            if leave_days > leave_balance.privilege_leave_balance:
                extra_leave = leave_days - leave_balance.privilege_leave_balance
                leave_balance.privilege_leave_balance = 0  # Set remaining balance to 0
            else:
                leave_balance.privilege_leave_balance -= leave_days  # Deduct normally

        # Deduct Casual Leave balance if applicable
        if leave_type == 'Casual Leave':
            leave_balance.casual_leave_balance -= leave_days

        if leave_type == "Half Day Leave":
            if leave_days > 1:
                flash('Half Day Leave can only be applied for one day.', 'danger')
                return redirect(url_for('profile.apply_leave'))
            elif leave_balance.casual_leave_balance < 0.5:
                flash('You do not have enough Casual Leave balance for Half Day Leave.', 'danger')
                return redirect(url_for('profile.apply_leave'))
            leave_balance.casual_leave_balance -= 0.5

        if leave_type == "Compensatory Leave":
            if leave_days > 2:
                flash('Compensatory Leave can only be applied for Two days.', 'danger')
                return redirect(url_for('profile.apply_leave'))
        
            flash('Please ask Lead/manager for Compensatory Leave.', 'danger')
        

        # Save leave application
        leave_application = LeaveApplication(
            admin_id=emp.id,
            leave_type=leave_type,
            reason=reason,
            start_date=start_date,
            end_date=end_date,
            status='Pending'
        )
        db.session.add(leave_application)
        db.session.commit()

        # Email notification
        manager_contact = ManagerContact.query.filter_by(circle_name=employee.circle,
                                                         user_type=employee.emp_type).first()
        department_email = 'singhroshan968@gmail.com'
        cc_emails = ['singhroshan9688@gmail.com']
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
                <p style="color: red;"><strong>⚠️ Extra Leave Days Required:</strong> {extra_leave} (Not covered by Privilege Leave)</p>
                """

        body += f"""
                <p>
                <a href="http://127.0.0.1:5000/" style="background-color: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">Login to HRMS to Approve</a>
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
    print(f"succefull got the reason: {user_leaves}")
    return render_template('profile/apply_leave.html', form=form, leave_balance=leave_balance, user_leaves=user_leaves)


@profile.route('/approve-leave/<int:leave_id>', methods=['GET'])
def approve_leave(leave_id):
    leave_application = LeaveApplication.query.get_or_404(leave_id)
    leave_application.status = 'Approved'
    db.session.commit()
    flash('✅ Leave has been approved successfully.', 'success')
    return redirect(url_for('manager_bp.manager_access'))

@profile.route('/reject-leave/<int:leave_id>', methods=['GET'])
def reject_leave(leave_id):
    leave_app_data = LeaveApplication.query.get_or_404(leave_id)
    leave_app_data.status = 'Rejected'
    db.session.commit()
    flash('❌ Leave application has been rejected.', 'danger')
    return redirect(url_for('manager_bp.manager_access'))
  
    






