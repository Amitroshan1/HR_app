from io import BytesIO
from flask import send_file
import pandas as pd
from flask import render_template, flash, redirect, Blueprint, request, url_for, current_app as app, session, Response
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
from .common import verify_oauth2_and_send_email
from .models.Admin_models import Admin
from .models.signup import Signup
from .common import send_wfh_approval_email_to_managers
from datetime import timedelta
from .utility import punch_time,add_comp_off
from sqlalchemy.exc import SQLAlchemyError



import logging

profile=Blueprint('profile',__name__)




# Configure logging for your app
logging.basicConfig(
    level=logging.DEBUG,  
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
            # ✅ If user uploads a new photo
            if form.Photo.data:
                file = form.Photo.data

                # Get file size
                file.seek(0, os.SEEK_END)  # move cursor to end
                file_size = file.tell()     # get size in bytes
                file.seek(0)                # reset cursor to beginning

                size_kb = round(file_size / 1024, 2)
                flash(f'File size: {size_kb} KB', 'info')

                # Validate file size (max 100 KB)
                if file_size > 102400:
                    flash('⚠️ File size exceeds 100 KB. Please upload a smaller photo.', 'warning')
                    return redirect(url_for('profile.empl_det'))

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
                    flash('Employee details updated successfully (new photo uploaded)!', 'success')
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
                # ✅ If no photo uploaded
                if not employee:
                    flash('Photo is required for new employee.', 'warning')
                else:
                    form.populate_obj(employee)
                    db.session.commit()
                    flash('Employee details updated successfully (photo unchanged).', 'success')

        except Exception as e:
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
    upload_doc = UploadDoc.query.filter_by(admin_id=current_user.id).first()

    if form.validate_on_submit():
        files = {}

        # Iterate over all form fields
        for field in ['aadhaar_front', 'aadhaar_back',
                      'pan_front', 'pan_back',
                      'appointment_letter',
                      'passbook_front']:
            file_data = getattr(form, field).data
            if file_data:
                filename = secure_filename(file_data.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_data.save(file_path)
                files[field] = filename

        if not upload_doc:
            # Create new entry
            upload_doc = UploadDoc(admin_id=current_user.id, **files)
            db.session.add(upload_doc)
            flash("Documents uploaded successfully!", "success")
        else:
            # Update existing entry
            for field, filename in files.items():
                setattr(upload_doc, field, filename)
            flash("Documents updated successfully!", "success")

        db.session.commit()
        return redirect(url_for('profile.upload_docs'))

    return render_template('profile/upload_doc.html', form=form, upload_doc=upload_doc, getattr=getattr  )





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

    # Get today's punch if exists
    punch = Punch.query.filter_by(admin_id=current_user.id, punch_date=today).first()

    # Selected month/year for calendar
    selected_month = request.args.get('month', today.month, type=int)
    selected_year = request.args.get('year', today.year, type=int)

    calendar.setfirstweekday(calendar.MONDAY)
    first_day = date(selected_year, selected_month, 1)
    last_day = first_day.replace(day=calendar.monthrange(selected_year, selected_month)[1])

    # Get all punches for the selected month
    punches = Punch.query.filter(
        Punch.admin_id == current_user.id,
        Punch.punch_date.between(first_day, last_day)
    ).all()

    # Prepare daily color data
    punch_data = {}
    for p in punches:
        color = 'bg-white'  # default
        if p.punch_in and p.punch_out and p.today_work:
            # Convert today_work string "HH:MM:SS" to timedelta
            try:
                h, m, s = map(int, str(p.today_work).split(':'))
                total_td = timedelta(hours=h, minutes=m, seconds=s)
            except:
                total_td = timedelta(seconds=0)

            if total_td >= timedelta(hours=8, minutes=30):
                color = 'present'   # Green Full Day
            elif total_td >= timedelta(hours=4):
                color = 'halfday'   # Yellow Half Day
            else:
                color = 'pending'   # Red Pending
        elif p.punch_in and not p.punch_out:
            color = 'pending'       # Red if punched in but not out
        punch_data[p.punch_date] = {'punch': p, 'color': color}

    # Punch In / Out logic
    if form.validate_on_submit():
        lat = request.form.get('lat', type=float)
        lon = request.form.get('lon', type=float)
        is_wfh = request.form.get('wfh') == 'on'

        locations = Location.query.all()
        is_near_location = False
        if lat is not None and lon is not None:
            is_near_location = is_near_saved_location(lat, lon, locations)

        if not is_near_location and not is_wfh:
            flash("You are not near any authorized location and 'Work From Home' is not selected.", "danger")
            return redirect(url_for('profile.punch'))

        # Punch In
        if form.punch_in.data:
            if check_leave():
                flash("You are not allowed to punch on this day because you are on leave", "danger")
                return redirect(request.url)
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
                return redirect(url_for('profile.punch'))


        # Punch Out
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
                punch.punch_out = datetime.now().time()
                punch_time(current_user.id)  # update today_work
                db.session.commit()

                if datetime.today().weekday() == 6:  # Sunday comp off
                    user = Signup.query.filter_by(email=current_user.email).first()
                    add_comp_off(user.id)
                    print("Comp Off added for Sunday work!")

                flash(f'Punch out successful! Work duration recorded: {punch.today_work}', 'success')
                return redirect(url_for('profile.punch'))

    # Get leave records for selected month
    last_day_num = calendar.monthrange(selected_year, selected_month)[1]
    leave_records = LeaveApplication.query.filter(
        LeaveApplication.admin_id == current_user.id,
        LeaveApplication.start_date <= date(selected_year, selected_month, last_day_num),
        LeaveApplication.end_date >= date(selected_year, selected_month, 1),
        LeaveApplication.status == 'Approved'
    ).all()

    # Collect leave days
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
        leave_days=leave_days
    )






@profile.route('/download_excel_emp', methods=['GET'])
@login_required
def download_excel_emp():
    # ✅ Get selected month & year (default to current if not provided)
    today = date.today()
    selected_month = request.args.get('month', today.month, type=int)
    selected_year = request.args.get('year', today.year, type=int)
    print(f"got the selected month: {selected_month}")
    print(f"got the selected year: {selected_year}")
    # Get user info
    emp = Signup.query.filter_by(email=current_user.email).first()
    if not emp:
        flash("User not found!", "danger")
        return redirect(url_for('profile.punch'))

    emp_type = emp.emp_type
    circle = emp.circle
    emp_code = emp.emp_id
    emp_name = emp.first_name

    # 📌 Get number of days in selected month
    num_days = calendar.monthrange(selected_year, selected_month)[1]

    # Create Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet("Attendance")
        writer.sheets["Attendance"] = worksheet

        # Styles
        border_fmt = workbook.add_format({'border': 1})
        header_fmt = workbook.add_format({
            'border': 1, 'bold': True, 'align': 'center',
            'valign': 'vcenter', 'bg_color': '#D9E1F2'
        })
        absent_fmt = workbook.add_format({'border': 1, 'bg_color': '#FFD966'})
        bold_fmt = workbook.add_format({'bold': True})

        # 📌 Write emp_type and circle at the top
        worksheet.write(0, 0, "emp_type", bold_fmt)
        worksheet.write(0, 1, emp_type)
        worksheet.write(0, 3, "CIRCLE", bold_fmt)
        worksheet.write(0, 4, circle)

        row = 2
        worksheet.write(row, 0, "Emp ID:", bold_fmt)
        worksheet.write(row, 1, emp_code)
        worksheet.write(row, 3, "Emp Name:", bold_fmt)
        worksheet.write(row, 4, emp_name)
        row += 1

        # 📌 Get punch records for selected month
        first_day = date(selected_year, selected_month, 1)
        last_day = date(selected_year, selected_month, num_days)

        punch_records = Punch.query.filter(
            Punch.admin_id == current_user.id,
            Punch.punch_date.between(first_day, last_day)
        ).all()

        punch_map = {p.punch_date.day: p for p in punch_records}

        in_times, out_times, totals = [], [], []
        for d in range(1, num_days + 1):
            punch = punch_map.get(d)
            if punch and punch.punch_in and punch.punch_out:
                in_times.append(punch.punch_in.strftime("%H:%M"))
                out_times.append(punch.punch_out.strftime("%H:%M"))

                if punch.today_work:
                    total_minutes = punch.today_work.hour * 60 + punch.today_work.minute
                else:
                    delta = datetime.combine(date.min, punch.punch_out) - datetime.combine(date.min, punch.punch_in)
                    total_minutes = delta.seconds // 60

                hours = total_minutes // 60
                minutes = total_minutes % 60
                if hours > 0 and minutes > 0:
                    totals.append(f"{hours} hrs {minutes} min")
                elif hours > 0:
                    totals.append(f"{hours} hrs")
                elif minutes > 0:
                    totals.append(f"{minutes} min")
                else:
                    totals.append("")
            else:
                in_times.append("")
                out_times.append("")
                totals.append("")

        # Headers
        days = []
        for d in range(1, num_days + 1):
            weekday = calendar.day_abbr[date(selected_year, selected_month, d).weekday()][0]
            days.append(f"{d} {weekday}")

        worksheet.write(row, 0, "Days", header_fmt)
        for col, val in enumerate(days, start=1):
            worksheet.write(row, col, val, header_fmt)
        row += 1

        # InTime
        worksheet.write(row, 0, "InTime", header_fmt)
        for col, val in enumerate(in_times, start=1):
            fmt = absent_fmt if val == "" else border_fmt
            worksheet.write(row, col, val, fmt)
        row += 1

        # OutTime
        worksheet.write(row, 0, "OutTime", header_fmt)
        for col, val in enumerate(out_times, start=1):
            fmt = absent_fmt if val == "" else border_fmt
            worksheet.write(row, col, val, fmt)
        row += 1

        # Total
        worksheet.write(row, 0, "Total", header_fmt)
        for col, val in enumerate(totals, start=1):
            fmt = absent_fmt if val == "" else border_fmt
            worksheet.write(row, col, val, fmt)

        worksheet.set_column(0, num_days, 12)

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        download_name=f'Attendance_{circle}_{emp_type}_{selected_month}_{selected_year}.xlsx',
        as_attachment=True
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


@profile.route('/manage-locations', methods=['GET', 'POST'])
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
            deducted_days=deducted_days,
            extra_days=extra_leave,        )
        db.session.add(leave_application)
        db.session.commit()

        # Email notification
        manager_contact = None  # ✅ Initialize before use

    # Try match with user_email first
        if current_user.email:
            manager_contact = ManagerContact.query.filter_by(
                circle_name=employee.circle,
                user_type=employee.emp_type,
                user_email=current_user.email
            ).first()

        # Fallback if no match found
        if not manager_contact:
            manager_contact = ManagerContact.query.filter_by(
                circle_name=employee.circle,
                user_type=employee.emp_type
            ).first()

        department_email = 'hr@saffotech.com'
        cc_emails = []

        if manager_contact:
            cc_emails.extend(filter(None, [manager_contact.l2_email, manager_contact.l3_email]))

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




 




